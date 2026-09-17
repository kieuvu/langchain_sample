from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qwen_base_url: str
    qwen_model_name: str
    qwen_api_key: str | None = None


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing = [
            ".".join(map(str, error["loc"]))
            for error in exc.errors()
            if error["type"] == "missing"
        ]
        if missing:
            names = ", ".join(name.upper() for name in missing)
            raise RuntimeError(
                f"Missing configuration: {names}. See .env.example."
            ) from exc
        raise RuntimeError(f"Invalid configuration: {exc}") from exc
