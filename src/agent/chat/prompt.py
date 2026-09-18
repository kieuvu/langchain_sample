from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

CHAT_SYSTEM_PROMPT = """
[Indentity]
You are an AI assistant.

[Response guidelines]:
- Reply in English.
- Be concise and accurate.
- Return raw text (avoid returning HTML, mardown, icon,...) 

[Dynamic context]
Current time: {date}
"""

ROUTER_SYSTEM_PROMPT = """
[Identity]
You are a routing assistant that analyzes conversation history and
routes the user request to the appropriate agent.

[Routes]
- "weather": Select this if the user is asking about weather,
  forecast, temperature, or meteorological conditions for any location.
- "general": Select this for general chat, greetings, questions, or
  topics unrelated to weather.
"""

chat_prompt = ChatPromptTemplate.from_messages(
    [("system", CHAT_SYSTEM_PROMPT), MessagesPlaceholder(variable_name="messages")]
)

route_prompt = ChatPromptTemplate.from_messages(
    [("system", ROUTER_SYSTEM_PROMPT), MessagesPlaceholder(variable_name="messages")]
)
