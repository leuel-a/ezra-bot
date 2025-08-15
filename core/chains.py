import re
import json
import logging
from typing import Tuple, Dict, Any, List, Optional

import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from core.state import AgentState
from core.tools import get_data_from_github
from core.utils import get_github_app_access_token, headers_without_authorization

tools = [get_data_from_github]
llm = init_chat_model(model="gemini-2.5-flash", model_provider="google_genai")
llm_with_tools = llm.bind_tools(tools)

ISSUE_DESCRIPTION_TEMPLATE = """\
## Summary
Briefly describe the problem.

## Steps to Reproduce
- Step 1
- Step 2
- ...

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS:
- Python:
- App/Service version:

## Additional Context (optional)
Links, screenshots, logs, or any other useful context.
"""

def determine_github_event(state: AgentState) -> AgentState:
    """Node to handle the GitHub event action"""
    logging.info("(LANGGRAPH_NODE) Determine GitHub Event")

    existing = state.get("messages") or []
    if existing:
        # NOTE: if there are any messages (e.g., after the ToolNode call), continue the conversation
        ai_message = llm_with_tools.invoke(existing)
        return { **state, "messages": [ai_message] }

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
    state["messages"] = messages

    ai_message = llm_with_tools.invoke(messages)
    return { **state, "messages": [*messages, ai_message] }


def _coerce_and_normalize_validation(payload: Any) -> Tuple[Dict[str, Any], str]:
    """
    Attempts to coerce the LLM validation output into a dict and normalize keys.
    Returns (normalized_dict, debug_repr_of_original).
    """
    logging.info(f"Coerce and Normalize Validation")

    original_repr = repr(payload)
    data = None

    if isinstance(payload, dict):
        data = payload
    else:
        for attr in ("model_dump", "dict"):
            if hasattr(payload, attr) and callable(getattr(payload, attr)):
                try:
                    data = getattr(payload, attr)()
                    break
                except Exception:
                    pass

    if data is None and isinstance(payload, str):
        try:
            data = json.loads(payload)
        except Exception:
            try:
                match = re.search(r"\{.*\}", payload, flags=re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
            except Exception:
                data = None

    if not isinstance(data, dict):
        data = {}

    normalized = {str(k).strip().strip('"').strip("'"): v for k, v in data.items()}
    return normalized, original_repr


def _extract_issue_from_messages(messages) -> dict | None:
    """
    Extracts issue data from a list of message objects.

    :param messages (list): A list of message objects to process. Each message should have
        an attribute `content`, which may contain JSON-formatted text.

    :returns:  A dictionary representing an issue payload if a valid issue is found
    :rtype: dict | None
    """
    logging.info("Extracting Issue from tool call from previous node")

    for msg in reversed(messages or []):
        content = getattr(msg, "content", None)


        # if the content is not a string or does not exist just move to next message
        if not content or not isinstance(content, str):
            continue

        try:
            data = json.loads(content)

        except Exception:
            continue

        # issue payloads from GitHub normally include at least these fields
        if isinstance(data, dict) and ("title" in data or "body" in data) and ("html_url" in data or "url" in data):
            return data
    return None


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
    except Exception as e:
        pass

    required_sections = ["## Summary", "## Steps to Reproduce", "## Expected Behavior", "## Actual Behavior", "## Environment"]
    missing = [sec for sec in required_sections if sec not in (body or "")]

    return {"valid": not missing, "reasons": [f"Missing section: {m}" for m in missing]}


def _post_issue_comment(comments_url: str, body: str) -> None:
    access_token = get_github_app_access_token()
    headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    payload = {"body": body}

    resp = requests.post(comments_url, json=payload, headers=headers)
    try:
        resp.raise_for_status()
    except Exception as e:
        logging.exception("Failed to create GitHub issue comment: %s", e)
        raise


def _get_issue_comments(comments_url: str) -> List[dict]:
    """Fetch comments for the issue
    :returns: A list of raw comment dicts (as received from GitHub).
    """
    access_token = get_github_app_access_token()
    headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    resp = requests.get(comments_url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    return data if isinstance(data, list) else []


def _is_github_bot_comment(comment: dict) -> bool:
    """Heuristics to identify if a comment appears to be authored by a GitHub app/bot.
    """
    user = (comment or {}).get("user") or {}
    login = (user.get("login") or "").lower()
    user_type = (user.get("type") or "").lower()
    performed_via_app = (comment or {}).get("performed_via_github_app")

    if performed_via_app:
        return True
    if user_type == "bot":
        return True
    if login.endswith("[bot]") or login.endswith("-bot") or "bot" in login:
        return True
    return False


def _asks_if_description_is_valid(text: str) -> bool:
    """
    Simple check to see if the last comment is asking whether the description is valid.
    You can refine this later with better NLU if needed.
    """
    t = (text or "").strip().lower()
    if not t:
        return False
    triggers = [
        "is the description valid",
        "is my description valid",
        "is it valid now",
        "is the issue valid",
        "is the body valid",
        "valid now?",
        "valid now",
        "is this valid",
    ]
    return any(k in t for k in triggers)



def _construct_reply_from_conversation(issue_body: str, comments: List[dict]) -> Optional[str]:
    """ Given the current issue body and the full conversation (comment list),
    construct a reply to the last user comment by calling an LLM via llm.invoke.

    :param issue_body: The body of the issue (string).
    :param comments: List of GitHub comment dicts (each must include 'body' and optionally 'performed_via_github_app').

    :returns: A string with the reply to post, or None to skip posting a reply.
    """
    if not comments:
        return None

    last_comment = comments[-1]
    last_is_user_comment = last_comment.get("performed_via_github_app") is None
    if not last_is_user_comment:
        return None

    messages = []
    for comment in comments:
        comment_body = (comment.get("body") or "").strip()
        if not comment_body:
            continue

        is_user_comment = comment.get("performed_via_github_app") is None
        if is_user_comment:
            messages.append(HumanMessage(content=comment_body))
        else:
            messages.append(AIMessage(content=comment_body))

    if not messages:
        return None

    system_prompt = (
        "You are a helpful engineering assistant replying in a GitHub Issue thread. "
        "Consider the issue description and the conversation so far. "
        "Write a concise, actionable reply,e with concrete next steps. "
        "If clarification is needed, ask at most one brief question. "
        "Keep a polite, professional tone.\n\n"
        f"Issue description:\n{(issue_body or '').strip()}"
    )

    try:
        result = llm_with_tools.invoke([SystemMessage(content=system_prompt), *messages])

        if hasattr(result, "content"):
            reply = str(result.content)
        elif isinstance(result, str):
            reply = result
        else:
            reply = "" 

        reply = reply.strip()
        return reply or None
    except Exception:
        logging.exception("Failed to generate reply via llm.invoke")
        return None


def validate_issue_description(state: AgentState):
    """
    Node that:
    - Extracts the fetched issue from prior tool output
    - Uses the LLM to validate the issue body against a sample template
    - If invalid:
        * Fetches comments
        * If last comment is from a GitHub bot, returns without responding
        * Otherwise, responds to the last user comment based on previous comments
        * If the user asked if the description is valid, re-checks the description and replies accordingly
    """
    logging.info("(LANGGRAPH_NODE) Validate Issue Description")
    issue = _extract_issue_from_messages(state.get("messages", []))

    if not issue:
        logging.warning("Issue could not be parsed, might be empty or not a tool call before")
        return {}

    issue_body = issue.get("body") or ""
    try:
        validation = _llm_validate_issue_body(issue_body, getattr(state, "issue_url", ""))
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


    if is_valid:
        logging.info("Issue Description Validated: OK")
        return {}

    comments_url = state.get("comments_url")
    reasons = validation.get("reasons") or []

    comments: List[dict] = []
    if comments_url:
        try:
            comments = _get_issue_comments(comments_url)
            logging.info("Fetched %d comment(s) for conversation analysis", len(comments))
        except Exception as e:
            logging.exception("Failed to fetch GitHub issue comments: %s", e)
    else:
        logging.warning("comments_url is missing in state; cannot fetch comments or post replies.")

    # if the last message was from a GitHub bot, do nothing and return
    if comments:
        last_comment = comments[-1]
        if _is_github_bot_comment(last_comment):
            logging.info("Last comment is from a GitHub bot; skipping response.")
            return {}

    # respond to the last comment based on the previous comments.
    # special behavior: if the last comment asks whether the description is valid,
    # re-check the description and reply accordingly.
    # !(todo) -> this does not seem right, the LLM should make the descision to respond
    reply_body: Optional[str] = None
    if comments:
        last_comment_body = (comments[-1].get("body") or "").strip()
        if _asks_if_description_is_valid(last_comment_body):
            revalidation = _llm_validate_issue_body(issue_body, getattr(state, "issue_url", ""))

            now_valid = bool(
                revalidation.get("valid")
                or revalidation.get("is_valid")
                or revalidation.get("ok")
                or False
            )
            if now_valid:
                reply_body = (
                    "I'm very happy with the description—thank you for the update! "
                    "We'll now wait for an internal engineer to mark the issue as reproducible."
                )
            else:
                rv_reasons = revalidation.get("reasons") or []
                reply_body = (
                    "Thanks for checking in! The description still doesn’t match the expected format. "
                    "Please update the issue body to follow the template in the contribution guidelines."
                )
                if rv_reasons:
                    reply_body += "\n\nWhy it’s considered invalid:\n"
                    for r in rv_reasons:
                        reply_body += f"- {r}\n"
        else:
            # Hand off to your custom conversation-based reply generator
            reply_body = _construct_reply_from_conversation(issue_body, comments)

    # fallback: if we couldn't construct a reply from comments, post the original validation guidance
    if not reply_body:
        reply_body = (
            "Thanks for opening this issue! 😊 It looks like the description does not match the expected format.\n"
            "Please update the issue body to follow the template in the contribution guideline.\n"
        )
        if reasons:
            reply_body += "\nWhy it’s considered invalid:\n"
            for r in reasons:
                reply_body += f"- {r}\n"

    # post reply if we have a comments_url; otherwise, just return with a message
    if comments_url:
        try:
            _post_issue_comment(comments_url, reply_body)
            logging.info("Posted validation/follow-up comment to: %s", comments_url)
        except Exception as e:
            logging.exception("Failed to create GitHub issue comment.")
    else:
        logging.warning("comments_url is missing in state; no comment posted.")

    return {
        "messages": [
            AIMessage(content="Issue description validated (invalid). Reply logic executed based on conversation.")
        ]
    }
