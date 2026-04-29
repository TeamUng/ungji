import os
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    LOGTAIL_SOURCE_TOKEN: str = ""
    LOGTAIL_HOST: str = ""
    DISCORD_WEBHOOK_URL: str = ""
    UPSTAGE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "ungji"
    UNGJI_DISABLE_LANGSMITH_TRACING: bool = False
    GOOGLE_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""


settings = Settings()


def configure_langsmith_tracing() -> None:
    """Enable LangSmith tracing before LangChain/LangGraph cache env lookups."""
    if not settings.LANGSMITH_API_KEY or settings.UNGJI_DISABLE_LANGSMITH_TRACING:
        return

    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"

    langsmith_utils = sys.modules.get("langsmith.utils")
    if langsmith_utils is not None:
        cache_clear = getattr(getattr(langsmith_utils, "get_env_var", None), "cache_clear", None)
        if callable(cache_clear):
            cache_clear()


configure_langsmith_tracing()
