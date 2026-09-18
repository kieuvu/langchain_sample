from typing import Annotated, TypedDict, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    route: Literal["weather", "general"]
