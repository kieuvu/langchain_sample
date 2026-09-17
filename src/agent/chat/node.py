from datetime import datetime

from langchain_core.messages import BaseMessage

from agent.chat.prompt import chat_prompt
from agent.chat.state import ChatState


def make_chat_node(model_with_tools):
    async def chat_node(state: ChatState) -> dict[str, list[BaseMessage]]:
        date = datetime.now().astimezone().isoformat(timespec="seconds")
        messages = chat_prompt.format_messages(date=date, messages=state["messages"])
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return chat_node
