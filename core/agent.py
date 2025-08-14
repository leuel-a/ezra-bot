import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.chains import on_issue_created, on_issue_edited


def route_event(state: AgentState) -> Literal["on_issue_created", "on_issue_edited"]:
    """Router to direct the graph flow based on the event type."""
    logging.info(f"(ROUTER) Event type is '{state['event_type']}'---")
    event_type = state["event_type"]

    if event_type == "created":
        return "on_issue_created"
    return "on_issue_edited"


def should_apply_action(state: AgentState) -> Literal["apply_action", "__end__"]:
    """Conditional edge to determine if an action needs to be applied."""
    logging.info("(CONDITION): should_apply_action?...")

    if state.get("action"):
        logging.info("(CONDITION_RESULT): Yes, applying action...")
        return "apply_action"

    logging.info("(CONDITION_RESULT): No, ending...")
    return "__end__" 


graph_builder = StateGraph(AgentState)

# ADD AGENT NODES
graph_builder.add_node("on_issue_created", on_issue_created)
graph_builder.add_node("on_issue_edited", on_issue_edited)

graph_builder.add_conditional_edges(
    "on_issue_created",
    should_apply_action,
    {"apply_action": "apply_action", END: END},
)
graph_builder.add_conditional_edges(
    "on_issue_edited",
    should_apply_action,
    {"apply_action": "apply_action", END: END},
)

graph_builder.add_edge("apply_action", END)
agent = graph_builder.compile()

