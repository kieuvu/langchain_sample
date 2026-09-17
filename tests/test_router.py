from langchain_core.messages import AIMessage, HumanMessage

from agent.chat.router import MAX_TOOL_CALL_TURNS, route_chat_output
from agent.chat.state import ChatState


def test_route_chat_output_to_tools():
    state: ChatState = {
        "messages": [
            HumanMessage(content="What's the weather?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_weather",
                        "args": {"location": "Hanoi"},
                        "id": "call-1",
                    }
                ],
            ),
        ]
    }
    assert route_chat_output(state) == "call_tool"


def test_route_chat_output_to_end_on_final_answer():
    state: ChatState = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Hello! How can I help you today?"),
        ]
    }
    assert route_chat_output(state) == "finish"


def test_route_chat_output_prevents_infinite_loops():
    # Exceed MAX_TOOL_CALL_TURNS
    messages = []
    for i in range(MAX_TOOL_CALL_TURNS + 2):
        messages.append(
            AIMessage(
                content="",
                tool_calls=[{"name": "tool", "args": {}, "id": f"call-{i}"}],
            )
        )
    state: ChatState = {"messages": messages}
    assert route_chat_output(state) == "finish"


def test_route_chat_output_empty_messages():
    state: ChatState = {"messages": []}
    assert route_chat_output(state) == "finish"
