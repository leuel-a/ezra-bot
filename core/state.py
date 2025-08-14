from typing import Annotated, List, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class Issue(TypedDict):
    """Represents the core issue data."""
    body: str
    labels: List[str]


class Comment(TypedDict):
    """Represents a comment on the issue."""
    body: str


class AgentState(TypedDict):
    """Defines the state for our agent."""
    issue: Issue
    comments: Annotated[List[Comment], add_messages] # TODO: may be we might need to parse the comments that come
    event_type: Literal["created", "edited"]
    action: Optional[str]
    action_payload: Optional[dict]
