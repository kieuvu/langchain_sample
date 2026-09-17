from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config.settings import Settings, load_settings


def create_qwen_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.qwen_model_name,
        base_url=settings.qwen_base_url,
        api_key=settings.qwen_api_key or "dummy",
    )


def create_chat_model(settings: Settings | None = None) -> BaseChatModel:
    if settings is None:
        settings = load_settings()
    return create_qwen_model(settings)
