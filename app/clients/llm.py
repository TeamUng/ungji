from langchain_openai import ChatOpenAI

from app.core.config import configure_langsmith_tracing, settings

configure_langsmith_tracing()


class LLMCallError(RuntimeError):
    """Raised when the shared LLM client cannot complete a request."""


_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/TeamUng/ungji",
    "X-Title": "ungji",
}


def _build_openrouter_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model,
        temperature=settings.LLM_TEMPERATURE,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=1,
        default_headers=_OPENROUTER_HEADERS,
    )


# motivator: TP1·2·3·5 동기 코칭 노드용
motivator_llm = _build_openrouter_llm(settings.MOTIVATOR_MODEL)

# helper: TP4 문제 막힘 진단/코칭 노드용
helper_llm = _build_openrouter_llm(settings.HELPER_MODEL)

# Guardrail judge compatibility alias. The product-facing nodes use the split
# motivator/helper models, while guardrail evaluation keeps the existing llm name.
llm = helper_llm
