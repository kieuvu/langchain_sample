from typing import Literal

from langchain_core.messages import AIMessage

from agent.chat.state import ChatState

MAX_TOOL_CALL_TURNS = 10


async def route_chat_output(state: ChatState) -> Literal["call_tool", "finish"]:
    messages = state.get("messages", [])
    if not messages:
        return "finish"

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        tool_turns = sum(
            1 for m in messages if isinstance(m, AIMessage) and m.tool_calls
        )
        if tool_turns > MAX_TOOL_CALL_TURNS:
            return "finish"
        return "call_tool"

    return "finish"


async def route_condition(
    state: ChatState,
) -> Literal["weather", "general"]:
    return state["route"]
