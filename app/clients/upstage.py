import os

from langchain_upstage import ChatUpstage

from app.core.config import settings

_DISABLE_LANGSMITH_TRACING = "UNGJI_DISABLE_LANGSMITH_TRACING"


def configure_langsmith_tracing() -> None:
    """Enable LangSmith tracing for real LLM runs when a key is configured."""
    if not settings.LANGSMITH_API_KEY:
        return
    if os.environ.get(_DISABLE_LANGSMITH_TRACING, "").lower() == "true":
        return

    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"


configure_langsmith_tracing()

llm = ChatUpstage(
    api_key=settings.UPSTAGE_API_KEY,
    model="solar-pro2",
    timeout=30,
)
