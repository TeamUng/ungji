from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from dataclasses import field
from typing import Any

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


@dataclass
class LLMTokenUsageRun:
    label: str
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def prompt_tokens(self) -> int:
        return sum(int(record.get("prompt_tokens", 0) or 0) for record in self.records)

    @property
    def completion_tokens(self) -> int:
        return sum(int(record.get("completion_tokens", 0) or 0) for record in self.records)

    @property
    def total_tokens(self) -> int:
        return sum(int(record.get("total_tokens", 0) or 0) for record in self.records)

    @property
    def measured_calls(self) -> int:
        return sum(1 for record in self.records if record.get("usage_source") != "unavailable")

    def summary(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "llm_calls": len(self.records),
            "measured_llm_calls": self.measured_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


_ACTIVE_TOKEN_USAGE_RUN: ContextVar[LLMTokenUsageRun | None] = ContextVar(
    "active_llm_token_usage_run",
    default=None,
)


MOTIVATOR_ROUTE = LLMRoute("motivator", MOTIVATOR_PROVIDER, MOTIVATOR_MODEL)
HELPER_ROUTE = LLMRoute("helper", HELPER_PROVIDER, HELPER_MODEL)
JUDGE_ROUTE = LLMRoute("judge", JUDGE_PROVIDER, JUDGE_MODEL)
COMMON_FALLBACK_ROUTE = LLMRoute(
    "common_fallback",
    COMMON_FALLBACK_PROVIDER,
    COMMON_FALLBACK_MODEL,
)


@contextmanager
def collect_llm_token_usage(label: str):
    run, token = start_llm_token_usage_run(label)
    try:
        yield run
    finally:
        stop_llm_token_usage_run(token)


def start_llm_token_usage_run(label: str) -> tuple[LLMTokenUsageRun, Token]:
    run = LLMTokenUsageRun(label=label)
    token = _ACTIVE_TOKEN_USAGE_RUN.set(run)
    return run, token


def stop_llm_token_usage_run(token: Token) -> None:
    _ACTIVE_TOKEN_USAGE_RUN.reset(token)


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
            response = await self.primary.ainvoke(messages, **kwargs)
            _record_llm_token_usage(
                response,
                requested_route=self.primary_route,
                actual_route=self.primary_route,
                used_fallback=False,
                method_name="ainvoke",
            )
            return response
        except Exception as primary_exc:
            self._log_primary_failure(primary_exc)
            if self.fallback is None:
                raise self._no_fallback_error(primary_exc) from primary_exc

            try:
                response = await self.fallback.ainvoke(messages, **kwargs)
                _record_llm_token_usage(
                    response,
                    requested_route=self.primary_route,
                    actual_route=self.fallback_route,
                    used_fallback=True,
                    method_name="ainvoke",
                )
                return response
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
            response = getattr(self.primary, method_name)(messages, **kwargs)
            _record_llm_token_usage(
                response,
                requested_route=self.primary_route,
                actual_route=self.primary_route,
                used_fallback=False,
                method_name=method_name,
            )
            return response
        except Exception as primary_exc:
            self._log_primary_failure(primary_exc)
            if self.fallback is None:
                raise self._no_fallback_error(primary_exc) from primary_exc

            try:
                response = getattr(self.fallback, method_name)(messages, **kwargs)
                _record_llm_token_usage(
                    response,
                    requested_route=self.primary_route,
                    actual_route=self.fallback_route,
                    used_fallback=True,
                    method_name=method_name,
                )
                return response
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


def _record_llm_token_usage(
    response,
    *,
    requested_route: LLMRoute,
    actual_route: LLMRoute,
    used_fallback: bool,
    method_name: str,
) -> None:
    usage = _extract_token_usage(response)
    record = {
        "llm_role": requested_route.role,
        "provider": actual_route.provider,
        "model": actual_route.model,
        "method": method_name,
        "used_fallback": used_fallback,
        **usage,
    }

    active_run = _ACTIVE_TOKEN_USAGE_RUN.get()
    if active_run is not None:
        active_run.records.append(record)
        record["usage_run_label"] = active_run.label

    logger.info("LLM token usage recorded", extra=record)


def _extract_token_usage(response) -> dict[str, int | str]:
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    if usage_metadata:
        prompt_tokens = _token_int(
            usage_metadata.get("input_tokens")
            or usage_metadata.get("prompt_tokens")
        )
        completion_tokens = _token_int(
            usage_metadata.get("output_tokens")
            or usage_metadata.get("completion_tokens")
        )
        total_tokens = _token_int(usage_metadata.get("total_tokens"))
        return _usage_dict(
            prompt_tokens,
            completion_tokens,
            total_tokens,
            source="usage_metadata",
        )

    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = (
        response_metadata.get("token_usage")
        or response_metadata.get("usage")
        or response_metadata
    )
    if token_usage:
        prompt_tokens = _token_int(
            token_usage.get("prompt_tokens")
            or token_usage.get("input_tokens")
        )
        completion_tokens = _token_int(
            token_usage.get("completion_tokens")
            or token_usage.get("output_tokens")
        )
        total_tokens = _token_int(token_usage.get("total_tokens"))
        if prompt_tokens or completion_tokens or total_tokens:
            return _usage_dict(
                prompt_tokens,
                completion_tokens,
                total_tokens,
                source="response_metadata",
            )

    return _usage_dict(0, 0, 0, source="unavailable")


def _usage_dict(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    *,
    source: str,
) -> dict[str, int | str]:
    if not total_tokens and (prompt_tokens or completion_tokens):
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "usage_source": source,
    }


def _token_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
