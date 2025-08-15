from typing import Annotated, List, Union, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, BaseMessage


class AgentState(TypedDict):
    """Defines the state for our agent."""
    issue_url: str
    comments_url: str
    event_action: str
    should_continue: bool
    valid_description_on_issue: bool
    validation_error_reasons: List[str]
    messages: Annotated[List[Union[AnyMessage, BaseMessage]], add_messages]

