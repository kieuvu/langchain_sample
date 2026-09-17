from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.chat.node import make_chat_node
from agent.chat.router import route_chat_output
from agent.chat.state import ChatState


def build_graph(model, tools: list[BaseTool], checkpointer: BaseCheckpointSaver):
    model_with_tools = model.bind_tools(tools)
    builder = StateGraph(ChatState)
    builder.add_node("chat", make_chat_node(model_with_tools))
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "chat")
    builder.add_conditional_edges(
        "chat",
        route_chat_output,
        {"call_tool": "tools", "finish": END},
    )
    builder.add_edge("tools", "chat")

    return builder.compile(checkpointer=checkpointer)
