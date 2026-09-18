import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.chat.graph import build_graph
from agent.chat.model import create_chat_model
from exception.session_not_found import SessionNotFound


class ChatService:
    def __init__(self, model: Any = None, tools: list | None = None):
        if model is None:
            model = create_chat_model()
        if tools is None:
            from agent.chat.tools.weather import get_weather

            tools = [get_weather]
        self.graph = build_graph(model, tools, InMemorySaver())
        self.sessions: dict[str, asyncio.Lock] = {}

    def create_session(self) -> str:
        session_id = str(uuid4())
        self.sessions[session_id] = asyncio.Lock()
        return session_id

    def require_session(self, session_id: str) -> asyncio.Lock:
        lock = self.sessions.get(session_id)
        if lock is None:
            raise SessionNotFound(session_id)
        return lock

    @staticmethod
    def config(session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    async def send(self, session_id: str, message: str) -> str:
        async with self.require_session(session_id):
            result = await self.graph.ainvoke(
                {"messages": [HumanMessage(content=message)]}, self.config(session_id)
            )
            return result["messages"][-1].content

    async def stream(
        self, session_id: str, message: str
    ) -> AsyncIterator[tuple[str, dict]]:
        async with self.require_session(session_id):
            async for part in self.graph.astream(
                {"messages": [HumanMessage(content=message)]},
                self.config(session_id),
                stream_mode=["messages", "updates", "tasks"],
                version="v2",
            ):
                if part["type"] == "tasks":
                    task = part["data"]
                    if "input" in task and task["name"] in (
                        "router_agent",
                        "weather_agent",
                        "general_agent",
                    ):
                        yield "progress", {"step": task["name"]}
                elif part["type"] == "messages":
                    chunk, metadata = part["data"]
                    node = metadata.get("langgraph_node")
                    if isinstance(chunk, AIMessageChunk) and node in (
                        "router_agent",
                        "weather_agent",
                        "general_agent",
                    ):
                        if node != "router_agent" and chunk.content:
                            yield "token", {"text": chunk.content}
                elif part["type"] == "updates":
                    for node_name, update in part["data"].items():
                        if not isinstance(update, dict):
                            continue
                        for item in update.get("messages", []):
                            if node_name == "weather_agent" and isinstance(
                                item, AIMessage
                            ):
                                for call in item.tool_calls:
                                    yield (
                                        "tool_start",
                                        {
                                            "name": call["name"],
                                            "input": call["args"],
                                        },
                                    )
                            elif node_name == "weather_tools" and isinstance(
                                item, ToolMessage
                            ):
                                yield (
                                    "tool_end",
                                    {
                                        "name": item.name,
                                        "output": item.content,
                                    },
                                )
            state = await self.graph.aget_state(self.config(session_id))
            yield "done", {"answer": state.values["messages"][-1].content}
