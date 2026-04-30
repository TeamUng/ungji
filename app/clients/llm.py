from __future__ import annotations

from dataclasses import dataclass

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import configure_langsmith_tracing, settings
from app.core.logging import get_logger

configure_langsmith_tracing()

logger = get_logger(__name__)


class LLMCallError(RuntimeError):
    """Raised when both the primary LLM and common fallback fail."""


# Runtime model routing is intentionally code-visible here. Do not move these
# model names to environment variables; API keys and base URLs remain in config.
MOTIVATOR_PROVIDER = "openrouter"
MOTIVATOR_MODEL = "google/gemini-2.5-flash"

HELPER_PROVIDER = "openrouter"
HELPER_MODEL = "openai/gpt-5.4-mini"

JUDGE_PROVIDER = HELPER_PROVIDER
JUDGE_MODEL = HELPER_MODEL

COMMON_FALLBACK_PROVIDER = "upstage"
COMMON_FALLBACK_MODEL = "solar-pro2"

LLM_TEMPERATURE = 0.7
LLM_TIMEOUT_SECONDS = 60

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/TeamUng/ungji",
    "X-Title": "ungji",
}


@dataclass(frozen=True)
class LLMRoute:
    role: str
    provider: str
    model: str


MOTIVATOR_ROUTE = LLMRoute("motivator", MOTIVATOR_PROVIDER, MOTIVATOR_MODEL)
HELPER_ROUTE = LLMRoute("helper", HELPER_PROVIDER, HELPER_MODEL)
JUDGE_ROUTE = LLMRoute("judge", JUDGE_PROVIDER, JUDGE_MODEL)
COMMON_FALLBACK_ROUTE = LLMRoute(
    "common_fallback",
    COMMON_FALLBACK_PROVIDER,
    COMMON_FALLBACK_MODEL,
)


class CommonFallbackChatModel:
    """Chat-model wrapper that retries one shared fallback model after primary failure."""

    def __init__(
        self,
        *,
        primary: Runnable,
        fallback: Runnable | None,
        primary_route: LLMRoute,
        fallback_route: LLMRoute,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_route = primary_route
        self.fallback_route = fallback_route

    def invoke(self, messages, **kwargs):
        return self._invoke_with_fallback("invoke", messages, **kwargs)

    async def ainvoke(self, messages, **kwargs):
        try:
            return await self.primary.ainvoke(messages, **kwargs)
        except Exception as primary_exc:
            self._log_primary_failure(primary_exc)
            if self.fallback is None:
                raise self._no_fallback_error(primary_exc) from primary_exc

            try:
                return await self.fallback.ainvoke(messages, **kwargs)
            except Exception as fallback_exc:
                self._log_fallback_failure(fallback_exc)
                raise self._fallback_error(primary_exc, fallback_exc) from fallback_exc

    def stream(self, messages, **kwargs):
        try:
            yield from self.primary.stream(messages, **kwargs)
            return
        except Exception as primary_exc:
            self._log_primary_failure(primary_exc)
            if self.fallback is None:
                raise self._no_fallback_error(primary_exc) from primary_exc

        try:
            yield from self.fallback.stream(messages, **kwargs)
        except Exception as fallback_exc:
            self._log_fallback_failure(fallback_exc)
            raise LLMCallError(
                f"{self.primary_route.role} LLM failed on primary and common fallback"
            ) from fallback_exc

    def bind_tools(self, tools):
        return CommonFallbackChatModel(
            primary=_bind_tools(self.primary, tools, self.primary_route),
            fallback=(
                _bind_tools(self.fallback, tools, self.fallback_route)
                if self.fallback is not None
                else None
            ),
            primary_route=self.primary_route,
            fallback_route=self.fallback_route,
        )

    def _invoke_with_fallback(self, method_name: str, messages, **kwargs):
        try:
            return getattr(self.primary, method_name)(messages, **kwargs)
        except Exception as primary_exc:
            self._log_primary_failure(primary_exc)
            if self.fallback is None:
                raise self._no_fallback_error(primary_exc) from primary_exc

            try:
                return getattr(self.fallback, method_name)(messages, **kwargs)
            except Exception as fallback_exc:
                self._log_fallback_failure(fallback_exc)
                raise self._fallback_error(primary_exc, fallback_exc) from fallback_exc

    def _log_primary_failure(self, exc: Exception) -> None:
        logger.warning(
            (
                "Primary LLM call failed; trying common fallback"
                if self.fallback is not None
                else "Primary LLM call failed; common fallback unavailable"
            ),
            extra={
                "llm_role": self.primary_route.role,
                "primary_provider": self.primary_route.provider,
                "primary_model": self.primary_route.model,
                "fallback_provider": self.fallback_route.provider,
                "fallback_model": self.fallback_route.model,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )

    def _log_fallback_failure(self, exc: Exception) -> None:
        logger.exception(
            "Common fallback LLM call failed",
            extra={
                "llm_role": self.primary_route.role,
                "fallback_provider": self.fallback_route.provider,
                "fallback_model": self.fallback_route.model,
                "error_type": type(exc).__name__,
            },
        )

    def _no_fallback_error(self, primary_exc: Exception) -> LLMCallError:
        return LLMCallError(
            f"{self.primary_route.role} LLM failed and common fallback is unavailable: "
            f"{type(primary_exc).__name__}: {primary_exc}"
        )

    def _fallback_error(self, primary_exc: Exception, fallback_exc: Exception) -> LLMCallError:
        return LLMCallError(
            f"{self.primary_route.role} LLM failed on primary "
            f"({type(primary_exc).__name__}: {primary_exc}) and common fallback "
            f"({type(fallback_exc).__name__}: {fallback_exc})"
        )


def _bind_tools(model: Runnable, tools, route: LLMRoute) -> Runnable:
    bind_tools = getattr(model, "bind_tools", None)
    if not callable(bind_tools):
        logger.warning(
            "LLM route does not support tool binding; using unbound model",
            extra={"llm_role": route.role, "provider": route.provider, "model": route.model},
        )
        return model

    try:
        return bind_tools(tools)
    except Exception:
        logger.warning(
            "LLM tool binding failed; using unbound model",
            extra={"llm_role": route.role, "provider": route.provider, "model": route.model},
            exc_info=True,
        )
        return model


def _build_chat_model(route: LLMRoute) -> Runnable:
    if route.provider == "openrouter":
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=route.model,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=1,
            default_headers=_OPENROUTER_HEADERS,
        )

    if route.provider == "upstage":
        from langchain_upstage import ChatUpstage

        return ChatUpstage(
            api_key=settings.UPSTAGE_API_KEY,
            model=route.model,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
        )

    raise ValueError(f"Unsupported LLM provider: {route.provider}")


def _build_common_fallback() -> Runnable | None:
    if COMMON_FALLBACK_ROUTE.provider == "upstage" and not settings.UPSTAGE_API_KEY:
        logger.warning(
            "Common fallback LLM disabled because UPSTAGE_API_KEY is not configured",
            extra={
                "fallback_provider": COMMON_FALLBACK_ROUTE.provider,
                "fallback_model": COMMON_FALLBACK_ROUTE.model,
            },
        )
        return None
    return _build_chat_model(COMMON_FALLBACK_ROUTE)


def _with_common_fallback(route: LLMRoute, fallback: Runnable | None) -> CommonFallbackChatModel:
    return CommonFallbackChatModel(
        primary=_build_chat_model(route),
        fallback=fallback,
        primary_route=route,
        fallback_route=COMMON_FALLBACK_ROUTE,
    )


_common_fallback_llm = _build_common_fallback()

# Motivator: TP1, TP2, TP3, TP5, and non-TP4 chat turns.
motivator_llm = _with_common_fallback(MOTIVATOR_ROUTE, _common_fallback_llm)

# Helper: TP4 stuck/help diagnosis and coaching.
helper_llm = _with_common_fallback(HELPER_ROUTE, _common_fallback_llm)

judge_llm = _with_common_fallback(JUDGE_ROUTE, _common_fallback_llm)

# Guardrail judge compatibility alias. Guardrail code imports `llm`.
llm = judge_llm
