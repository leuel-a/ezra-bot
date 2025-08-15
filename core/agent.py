from langgraph.graph import StateGraph, START
from langgraph.prebuilt import tools_condition

from core import chains
from core.state import AgentState
from core.tools import tool_node


graph_builder = StateGraph(AgentState)

graph_builder.add_node("determine_github_event", chains.determine_github_event)
graph_builder.add_node("validate_issue_description", chains.validate_issue_description)
graph_builder.add_node("tools", tool_node)


graph_builder.add_edge(START, "determine_github_event")
graph_builder.add_conditional_edges(
    "determine_github_event",
    tools_condition,
)

graph_builder.add_conditional_edges(
    "validate_issue_description",
    tools_condition
)

graph_builder.add_edge("tools", "validate_issue_description")
graph_builder.add_edge("validate_issue_description", "determine_github_event")

graph = graph_builder.compile()
