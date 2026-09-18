import asyncio
import json

import httpx
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool

from api import create_app
from services.chat import ChatService


@tool
async def fake_weather(location: str) -> str:
    """Return a fake weather report for a location."""
    return f"Sunny in {location}"


class FakeChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        assert kwargs["method"] == "json_schema"
        assert schema["properties"]["route"]

        async def route(messages):
            users = [
                message for message in messages if isinstance(message, HumanMessage)
            ]
            choice = "weather" if "weather" in users[-1].content.lower() else "general"
            return {"route": choice}

        return RunnableLambda(route)

    @staticmethod
    def reply(messages):
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content="Weather: sunny.")
        users = [message for message in messages if isinstance(message, HumanMessage)]
        if "weather" in users[-1].content.lower():
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fake_weather",
                        "args": {"location": "Hanoi"},
                        "id": "call-weather",
                    }
                ],
            )
        return AIMessage(content=f"Turn {len(users)}: {users[-1].content}")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self.reply(messages))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self.reply(messages)
        if reply.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": "fake_weather",
                            "args": '{"location":"Hanoi"}',
                            "id": "call-weather",
                            "index": 0,
                        }
                    ],
                )
            )
        else:
            for word in reply.content.split(" "):
                yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))


class FailingChatModel(FakeChatModel):
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("fake model failed")

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("fake model failed")
        yield  # Keep this an async generator, as required by the chat model API.


class SlowChatModel(FakeChatModel):
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        await asyncio.sleep(0.01)
        return await super()._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )


class ThinkingChatModel(FakeChatModel):
    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        for text in ("Let me ", "check."):
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="", additional_kwargs={"reasoning_content": text}
                )
            )
        async for chunk in super()._astream(
            messages, stop=stop, run_manager=run_manager, **kwargs
        ):
            yield chunk


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    service = ChatService(model=FakeChatModel(), tools=[fake_weather])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test"
    ) as client:
        yield client


async def create_session(client):
    response = await client.post("/v1/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]


def parse_events(body):
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1][6:])))
    return events


@pytest.mark.anyio
async def test_session_lifecycle_and_multi_turn(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    page = await client.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert '<html lang="en">' in page.text
    css = await client.get("/static/style.css")
    assert css.status_code == 200
    js = await client.get("/static/app.js")
    assert js.status_code == 200
    session_id = await create_session(client)
    url = f"/v1/sessions/{session_id}"

    first = await client.post(f"{url}/messages", json={"message": "  Hello  "})
    second = await client.post(f"{url}/messages", json={"message": "Again"})
    assert first.json() == {"session_id": session_id, "answer": "Turn 1: Hello"}
    assert second.json() == {"session_id": session_id, "answer": "Turn 2: Again"}


@pytest.mark.anyio
async def test_sessions_are_isolated_and_inputs_are_validated(client):
    first = await create_session(client)
    second = await create_session(client)
    for session_id in (first, second):
        response = await client.post(
            f"/v1/sessions/{session_id}/messages", json={"message": "Hello"}
        )
        assert response.json()["answer"] == "Turn 1: Hello"
    assert (
        await client.post("/v1/sessions/missing/messages", json={"message": "Hi"})
    ).status_code == 404
    assert (
        await client.post(f"/v1/sessions/{first}/messages", json={"message": "  "})
    ).status_code == 422


@pytest.mark.anyio
async def test_stream_reports_tool_progress_tokens_and_final_answer(client):
    session_id = await create_session(client)
    url = f"/v1/sessions/{session_id}"
    response = await client.post(
        f"{url}/messages/stream", json={"message": "Weather in Hanoi?"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_events(response.text)
    names = [name for name, _ in events]
    assert names[:2] == ["progress", "progress"]
    assert [data["step"] for name, data in events if name == "progress"] == [
        "router_agent",
        "weather_agent",
        "weather_agent",
    ]
    assert names.index("tool_start") < names.index("tool_end") < names.index("token")
    assert names[-1] == "done"
    assert "token" in names
    assert next(data for name, data in events if name == "tool_start") == {
        "name": "fake_weather",
        "input": {"location": "Hanoi"},
    }
    assert next(data for name, data in events if name == "tool_end") == {
        "name": "fake_weather",
        "output": "Sunny in Hanoi",
    }
    assert events[-1][1] == {"answer": "Weather: sunny. "}


@pytest.mark.anyio
async def test_general_stream_shows_steps_and_tokens_without_tools(client):
    session_id = await create_session(client)
    response = await client.post(
        f"/v1/sessions/{session_id}/messages/stream", json={"message": "Hello"}
    )
    events = parse_events(response.text)
    assert [data["step"] for name, data in events if name == "progress"] == [
        "router_agent",
        "general_agent",
    ]
    assert "tool_start" not in [name for name, _ in events]
    assert "token" in [name for name, _ in events]
    assert events[-1] == ("done", {"answer": "Turn 1: Hello "})


@pytest.mark.anyio
async def test_stream_rejects_unknown_session_and_blank_message(client):
    assert (
        await client.post(
            "/v1/sessions/missing/messages/stream", json={"message": "Hello"}
        )
    ).status_code == 404
    session_id = await create_session(client)
    assert (
        await client.post(
            f"/v1/sessions/{session_id}/messages/stream", json={"message": " "}
        )
    ).status_code == 422


@pytest.mark.anyio
async def test_model_failure_returns_json_error_or_sse_error():
    service = ChatService(model=FailingChatModel(), tools=[fake_weather])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test"
    ) as client:
        session_id = await create_session(client)
        url = f"/v1/sessions/{session_id}/messages"
        response = await client.post(url, json={"message": "Hello"})
        assert response.status_code == 502
        assert response.json()["detail"] == "Could not process the message."

        response = await client.post(f"{url}/stream", json={"message": "Hello"})
        assert response.status_code == 200
        events = parse_events(response.text)
        assert [name for name, _ in events] == ["progress", "progress", "error"]
        assert events[-1] == (
            "error",
            {"message": "Could not process the message."},
        )


@pytest.mark.anyio
async def test_requests_in_one_session_are_serialized():
    service = ChatService(model=SlowChatModel(), tools=[fake_weather])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test"
    ) as client:
        session_id = await create_session(client)
        url = f"/v1/sessions/{session_id}/messages"
        first, second = await asyncio.gather(
            client.post(url, json={"message": "One"}),
            client.post(url, json={"message": "Two"}),
        )
        assert {first.json()["answer"], second.json()["answer"]} == {
            "Turn 1: One",
            "Turn 2: Two",
        }
