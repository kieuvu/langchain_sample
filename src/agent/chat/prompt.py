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

chat_prompt = ChatPromptTemplate.from_messages(
    [("system", CHAT_SYSTEM_PROMPT), MessagesPlaceholder(variable_name="messages")]
)
