import logging
from core.state import AgentState
from langchain.chat_models import init_chat_model
from core.utils import validate_issue_body


model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")




def on_issue_created(state: AgentState) -> AgentState:
    """Node to handle 'issue created' events."""
    print("---NODE: on_issue_created---")
    is_valid = validate_issue_body(state["issue"]["body"])

    if not is_valid:
        print("DECISION: Issue is invalid. Needs label and comment.")
        state["action"] = "ADD_LABEL_AND_COMMENT"
        state["action_payload"] = {
            "label": NEEDS_DESCRIPTION_LABEL,
            "comment": TEMPLATE_COMMENT,
        }
    else:
        print("DECISION: Issue is valid. No action needed.")
        state["action"] = None
        state["action_payload"] = None
    return state

def on_issue_edited(state: AgentState) -> AgentState:
    """Node to handle 'issue edited' events."""
    print("---NODE: on_issue_edited---")
    is_valid = validate_issue_body(state["issue"]["body"])
    has_label = NEEDS_DESCRIPTION_LABEL in state["issue"]["labels"]

    # Case 1: Issue is now valid and has the 'needs description' label.
    if is_valid and has_label:
        print("DECISION: Issue fixed. Remove label and thank user.")
        state["action"] = "REMOVE_LABEL_AND_COMMENT"
        state["action_payload"] = {
            "label": NEEDS_DESCRIPTION_LABEL,
            "comment": THANK_YOU_COMMENT,
        }
    # Case 2: Issue is still invalid, but doesn't have the label yet.
    elif not is_valid and not has_label:
        # Avoid spamming by checking if a reminder was already posted.
        has_reminder = any(TEMPLATE_COMMENT in c["body"] for c in state["comments"])
        if not has_reminder:
            print("DECISION: Issue still invalid. Add label and reminder.")
            state["action"] = "ADD_LABEL_AND_COMMENT"
            state["action_payload"] = {
                "label": NEEDS_DESCRIPTION_LABEL,
                "comment": REMINDER_COMMENT,
            }
        else:
             print("DECISION: Issue still invalid, but reminder already exists. No action.")
             state["action"] = None
             state["action_payload"] = None
    else:
        print("DECISION: No relevant changes. No action needed.")
        state["action"] = None
        state["action_payload"] = None
    return state

def apply_action(state: AgentState) -> AgentState:
    """
    Effector node. This node simulates making API calls to GitHub.
    In a real-world scenario, this is where you'd use a GitHub client.
    """
    print("---NODE: apply_action---")
    action = state.get("action")
    payload = state.get("action_payload")

    if action == "ADD_LABEL_AND_COMMENT":
        print(f"ACTION: Adding label '{payload['label']}'")
        print(f"ACTION: Posting comment:\n---\n{payload['comment']}\n---")
    elif action == "REMOVE_LABEL_AND_COMMENT":
        print(f"ACTION: Removing label '{payload['label']}'")
        print(f"ACTION: Posting comment:\n---\n{payload['comment']}\n---")
    else:
        print("ACTION: No action taken.")
    return state
