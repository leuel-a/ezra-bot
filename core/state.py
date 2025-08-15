from typing import Annotated, List, Optional, Union
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, BaseMessage


class AgentState(TypedDict):
    """Defines the state for our agent."""
    issue_url: Optional[str]
    comments_url: Optional[str]
    event_action: Optional[str]
    messages: Annotated[List[Union[AnyMessage, BaseMessage]], add_messages]
