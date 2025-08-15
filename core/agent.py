from typing import Union, Any, Literal
from langgraph.graph import StateGraph, START
from langchain_core.messages import AnyMessage

from core import chains
from core.state import AgentState
from core.tools import tool_node
from pydantic import BaseModel


def custom_tools_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["tools", "__end__"]:
    if isinstance(state, list):
        ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
        ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")

    if hasattr(ai_message, "tool_calls") and len(getattr(ai_message, "tool_calls", [])) > 0:
        return "tools"
    return "__end__"

graph_builder = StateGraph(AgentState)

graph_builder.add_node("tools", tool_node)
graph_builder.add_node("react_to_github_event", chains.react_to_github_event)
graph_builder.add_node("validate_issue_description", chains.validate_issue_description)
graph_builder.add_node("respond_to_user_query", chains.respond_to_user_query)


graph_builder.add_edge(START, "react_to_github_event")
graph_builder.add_conditional_edges(
        "react_to_github_event",
        custom_tools_condition,
    )

graph_builder.add_edge("tools", "validate_issue_description")
graph_builder.add_edge("validate_issue_description", "respond_to_user_query")
graph_builder.add_conditional_edges(
        "respond_to_user_query",
        custom_tools_condition,
    )

graph = graph_builder.compile()
