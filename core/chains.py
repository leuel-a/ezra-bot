import json
import logging
from typing import List

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from core.state import AgentState
from core.tools import get_data_from_github, post_issue_comment_on_github
from core.prompt_templates import ISSUE_DESCRIPTION_TEMPLATE

tools = [get_data_from_github, post_issue_comment_on_github]
llm = init_chat_model(model="gemini-2.5-flash", model_provider="google_genai")
llm_with_tools = llm.bind_tools(tools)


def _extract_issue_from_messages(messages) -> dict:
    """
    Extracts issue data from a list of message objects.

    :param messages (list): A list of message objects to process. Each message should have
        an attribute `content`, which may contain JSON-formatted text.

    :returns:  A dictionary representing an issue payload if a valid issue is found
    :rtype: dict | None
    """
    for msg in reversed(messages or []):
        content = getattr(msg, "content", None)
        if not content or not isinstance(content, str):
            continue
        try:
            data = json.loads(content)
        except Exception:
            continue
        if isinstance(data, dict) and ("title" in data or "body" in data) and ("html_url" in data or "url" in data):
            return data

    return {}


def _llm_validate_issue_body(body: str | None, issue_url: str) -> dict:
    """Validates the structure and content of a GitHub issue body against a predefined template.

    :param body: The content of the GitHub issue body to validate
    :ptype: str

    :rtype: dict
    """
    if not body:
        return {"valid": False, "reasons": ["Issue description cannot be empty. Please follow the contribution guidelines to create an issue here."]}

    system_message = (
        "You are a strict validator for GitHub issue descriptions. "
        "You will receive a target 'Template' and a 'Body'. "
        "If the user asks to check the description of an issue,"
        f"use the provided {issue_url} to request the issue data from GitHub and extract the description for validation. "
        "Return ONLY a compact JSON object with keys: "
        '\'{{ "valid": boolean, "reasons": [string, ...] }}\'. '
        "valid is true only if the Body clearly follows the structure and intent of the Template "
        "(has all required sections with non-empty, meaningful content). "
        "Do not include any extra keys or commentary."
    )

    user_message = f"""
        Template:
            {ISSUE_DESCRIPTION_TEMPLATE}

        Body:
            {body or ""}

        Respond with strict JSON only.
    """

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_message),
        HumanMessagePromptTemplate.from_template(user_message),
    ])

    messages = prompt_template.format_messages()
    result = llm_with_tools.invoke(messages)

    content = getattr(result, "content", "") or ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "valid" in parsed and "reasons" in parsed:
            return parsed
    except Exception:
        pass

    required_sections = ["## Summary", "## Steps to Reproduce", "## Expected Behavior", "## Actual Behavior", "## Environment"]
    missing = [sec for sec in required_sections if sec not in (body or "")]

    return {"valid": not missing, "reasons": [f"Missing section: {m}" for m in missing]}


## NODES
def react_to_github_event(state: AgentState):
    """Node to handle the GitHub event action"""
    logging.info("(LANGGRAPH_NODE) React to GitHub Event")

    system_message = (
        "You are a specialized agent designed to interact with the GitHub API. "
        "Your core function is to fetch data from a given URL using your available tools. "
        "You will be provided with a specific GitHub URL and must use the appropriate tool "
        "to retrieve the content from that URL and present it to the user. "
        "Your response should be based solely on the data you fetch."
    )
    human_message = HumanMessagePromptTemplate.from_template(
        "Please get the issue details from the following GitHub URL: {url}"
    )

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_message),
        human_message,
    ])
    messages = prompt_template.format_messages(url=state.get("issue_url"))
    ai_message = llm_with_tools.invoke(messages)

    return { "messages": [ai_message] }


def validate_issue_description(state: AgentState):
    """
    Extracts the fetched issue from prior tool output
    Uses the LLM to validate the issue body against a sample template
    """
    logging.info("(LANGGRAPH_NODE) Validate Issue Description")

    if state.get("should_continue") is False:
        return {}
    
    issue = _extract_issue_from_messages(state.get("messages", []))

    if not issue:
        logging.warning("Issue could not be parsed")
        return {}

    issue_body = issue.get("body") or ""
    reasons: List[str] = []

    try:
        validation = _llm_validate_issue_body(issue_body, getattr(state, "issue_url", ""))
        reasons.extend(validation.get("reasons", []))

        is_valid = bool(
            validation.get("valid")
            or validation.get("is_valid")
            or validation.get("ok")
            or False
        )
    except Exception as e:
        logging.exception("Failed to validate issue body: %s", e)
        validation = {"valid": False, "reasons": [f"Failed to validate issue body: {e}"]}
        is_valid = False


    return { "valid_description_on_issue": is_valid, "validation_error_reasons": reasons }


def respond_to_user_query(state: AgentState):
    """
    Responds to the quest query
    """
    logging.info("(LANGGRAPH_NODE) Respond to User Query")

    if state.get("should_continue") is False:
        return {}

    valid_description_on_issue = state.get("valid_description_on_issue")
    validation_error_reasons = state.get("reasons")
    messages = state.get("messages")

    issue = _extract_issue_from_messages(messages)
    issue_body = issue.get("body", "")

    if valid_description_on_issue:
        system_message = (
            "You are a helpful engineering assistant replying in a GitHub Issue thread. "
            "The user’s issue description is valid. "
            "Respond only to the user’s current question in the conversation without adding anything unrelated. "
            "If the user is simply checking validity, respond with: 'The issue description is valid.'\n\n"
            f"Issue description:\n{(issue_body or '').strip()}"
        )
    else:
        reasons_text = "\n".join(f"- {reason}" for reason in validation_error_reasons) if validation_error_reasons else "No specific reasons provided."
        system_message = (
            "You are a helpful engineering assistant replying in a GitHub Issue thread. "
            "The user’s issue description is not valid. "
            f"The following issues were found:\n{reasons_text}\n\n"
            "First, respond to the user’s current question in the conversation. "
            "After that, provide the following template and instruct the user to use it to improve the description:\n\n"
            f"{ISSUE_DESCRIPTION_TEMPLATE}\n\n"
            f"Issue description:\n{(issue_body or '').strip()}"
        )

    user_message = (
        f"Create a new comment using {state.get('comments_url')} with the body as the response you generated."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_message),
        HumanMessagePromptTemplate.from_template(user_message),
    ])
    messages = prompt_template.format_messages()
    ai_message = llm_with_tools.invoke(messages)

    return { "messages": [ai_message], "should_continue": False }


