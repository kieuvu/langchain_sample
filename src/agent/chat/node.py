from datetime import datetime
from typing import Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from agent.chat.prompt import chat_prompt, route_prompt
from agent.chat.state import ChatState


class Route(BaseModel):
    route: Literal["weather", "general"]


def make_chat_node(model_with_tools):
    async def chat_node(state: ChatState) -> dict[str, list[BaseMessage]]:
        date = datetime.now().astimezone().isoformat(timespec="seconds")
        messages = chat_prompt.format_messages(date=date, messages=state["messages"])
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return chat_node


def make_router_node(model_with_routes):
    async def router_node(state: ChatState):
        messages = route_prompt.format_messages(messages=state["messages"])

        response = await model_with_routes.ainvoke(messages)

        return {"route": Route.model_validate(response).route}

    return router_node
