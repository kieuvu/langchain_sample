import pytest
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


@pytest.mark.anyio
async def test_make_router_node_routes_with_structured_output():
    from unittest.mock import AsyncMock

    from agent.chat.graph import Route
    from agent.chat.node import make_router_node

    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = Route(route="weather")

    router = make_router_node(mock_model)
    command = await router({"messages": [HumanMessage(content="Weather in Danang?")]})
    assert command.goto == "weather"

    mock_model.ainvoke.return_value = Route(route="general")
    command = await router({"messages": [HumanMessage(content="Hello")]})
    assert command.goto == "general"


@pytest.mark.anyio
async def test_make_router_node_routes_with_dict():
    from unittest.mock import AsyncMock

    from agent.chat.node import make_router_node

    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = {"route": "weather"}

    router = make_router_node(mock_model)
    command = await router({"messages": [HumanMessage(content="Weather?")]})
    assert command.goto == "weather"


@pytest.mark.anyio
async def test_make_router_node_fallback_on_output_parser_exception():
    from unittest.mock import AsyncMock

    from langchain_core.exceptions import OutputParserException

    from agent.chat.node import make_router_node

    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = OutputParserException("Failed")

    router = make_router_node(mock_model)
    command = await router({"messages": [HumanMessage(content="What's the weather?")]})
    assert command.goto == "weather"

    command = await router({"messages": [HumanMessage(content="Hi there!")]})
    assert command.goto == "general"
