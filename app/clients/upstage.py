import os

from langchain_upstage import ChatUpstage

from app.core.config import settings

if settings.LANGSMITH_API_KEY:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

llm = ChatUpstage(
    api_key=settings.UPSTAGE_API_KEY,
    model="solar-pro-2",
)
