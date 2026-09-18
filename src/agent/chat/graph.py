from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.chat.node import Route, make_chat_node, make_router_node
from agent.chat.router import route_chat_output, route_condition
from agent.chat.state import ChatState


def build_graph(
    model, weather_tools: list[BaseTool], checkpointer: BaseCheckpointSaver
):
    model_with_weather_tools = model.bind_tools(weather_tools)
    model_with_routes = model.with_structured_output(
        Route.model_json_schema(), method="json_schema"
    )

    weather_agent = make_chat_node(model_with_weather_tools)
    general_agent = make_chat_node(model)

    builder = StateGraph(ChatState)
    builder.add_node("router_agent", make_router_node(model_with_routes))
    builder.add_node("weather_agent", weather_agent)
    builder.add_node("general_agent", general_agent)
    
    builder.add_node("weather_tools", ToolNode(weather_tools))

    builder.add_edge(START, "router_agent")
    builder.add_edge("weather_tools", "weather_agent")
    builder.add_edge("general_agent", END)

    builder.add_conditional_edges(
        "router_agent",
        route_condition,
        {
            "weather": "weather_agent",
            "general": "general_agent",
        },
    )
    builder.add_conditional_edges(
        "weather_agent",
        route_chat_output,
        {
            "call_tool": "weather_tools",
            "finish": END,
        },
    )

    return builder.compile(checkpointer=checkpointer)
