from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.clients import llm_config

logger = get_logger(__name__)


class LLMConfigurationError(RuntimeError):
    """Raised when a configured LLM provider cannot be constructed."""


class LLMCallError(RuntimeError):
    """Raised when all configured LLM providers fail for one call."""


@dataclass(frozen=True)
class LLMProviderConfig:
    role: str
    provider: str
    model: str
    api_key: str
    base_url: str | None
    timeout: float

    @property
    def label(self) -> str:
        return f"{self.role}:{self.provider}/{self.model}"


class FallbackChatModel:
    """LangChain-style chat model wrapper with central provider fallback."""

    def __init__(
        self,
        configs: Iterable[LLMProviderConfig] | None = None,
        *,
        bound_tools: list[Any] | None = None,
        bound_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._configs = tuple(configs or build_provider_configs())
        if not self._configs:
            raise LLMConfigurationError("At least one LLM provider must be configured")
        self._bound_tools = list(bound_tools or [])
        self._bound_kwargs = dict(bound_kwargs or {})
        self._models: dict[tuple[str, str, str | None, float], Any] = {}

    def bind_tools(self, tools: list[Any]) -> "FallbackChatModel":
        return self._clone(bound_tools=list(tools))

    def bind(self, **kwargs: Any) -> "FallbackChatModel":
        return self._clone(bound_kwargs={**self._bound_kwargs, **kwargs})

    def invoke(self, messages: list[Any], **kwargs: Any) -> Any:
        call_kwargs = {**self._bound_kwargs, **kwargs}
        return self._invoke_with_fallback("invoke", messages, call_kwargs)

    async def ainvoke(self, messages: list[Any], **kwargs: Any) -> Any:
        call_kwargs = {**self._bound_kwargs, **kwargs}
        return await self._ainvoke_with_fallback(messages, call_kwargs)

    def stream(self, messages: list[Any], **kwargs: Any):
        call_kwargs = {**self._bound_kwargs, **kwargs}
        last_error: Exception | None = None
        for index, config in enumerate(self._configs):
            try:
                runnable = self._runnable_for(config)
                for chunk in runnable.stream(messages, **call_kwargs):
                    yield chunk
                if index > 0:
                    _log_fallback_success(config, "stream")
                return
            except Exception as exc:
                last_error = exc
                if not _can_try_next(exc, index, self._configs):
                    break
                _log_fallback_attempt(config, exc, "stream")
        raise LLMCallError("LLM stream failed for all configured providers") from last_error

    def _clone(
        self,
        *,
        bound_tools: list[Any] | None = None,
        bound_kwargs: dict[str, Any] | None = None,
    ) -> "FallbackChatModel":
        clone = FallbackChatModel(
            self._configs,
            bound_tools=self._bound_tools if bound_tools is None else bound_tools,
            bound_kwargs=self._bound_kwargs if bound_kwargs is None else bound_kwargs,
        )
        clone._models = self._models
        return clone

    def _invoke_with_fallback(
        self,
        operation: str,
        messages: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        last_error: Exception | None = None
        for index, config in enumerate(self._configs):
            try:
                runnable = self._runnable_for(config)
                result = getattr(runnable, operation)(messages, **kwargs)
                if index > 0:
                    _log_fallback_success(config, operation)
                return result
            except Exception as exc:
                last_error = exc
                if not _can_try_next(exc, index, self._configs):
                    break
                _log_fallback_attempt(config, exc, operation)
        raise LLMCallError(f"LLM {operation} failed for all configured providers") from last_error

    async def _ainvoke_with_fallback(self, messages: list[Any], kwargs: dict[str, Any]) -> Any:
        last_error: Exception | None = None
        for index, config in enumerate(self._configs):
            try:
                runnable = self._runnable_for(config)
                if hasattr(runnable, "ainvoke"):
                    result = await runnable.ainvoke(messages, **kwargs)
                else:
                    result = await asyncio.to_thread(runnable.invoke, messages, **kwargs)
                if index > 0:
                    _log_fallback_success(config, "ainvoke")
                return result
            except Exception as exc:
                last_error = exc
                if not _can_try_next(exc, index, self._configs):
                    break
                _log_fallback_attempt(config, exc, "ainvoke")
        raise LLMCallError("LLM ainvoke failed for all configured providers") from last_error

    def _runnable_for(self, config: LLMProviderConfig) -> Any:
        model = self._model_for(config)
        if self._bound_tools:
            return model.bind_tools(self._bound_tools)
        return model

    def _model_for(self, config: LLMProviderConfig) -> Any:
        key = (config.provider, config.model, config.base_url, config.timeout)
        if key not in self._models:
            self._models[key] = _build_chat_model(config)
        return self._models[key]


def create_llm() -> FallbackChatModel:
    return FallbackChatModel()


def build_provider_configs() -> tuple[LLMProviderConfig, ...]:
    primary = _provider_config(
        role="primary",
        provider=llm_config.PRIMARY_LLM.provider,
        model=llm_config.PRIMARY_LLM.model,
    )

    configs = [primary]
    if llm_config.FALLBACK_LLM is not None:
        fallback = _provider_config(
            role="fallback",
            provider=llm_config.FALLBACK_LLM.provider,
            model=llm_config.FALLBACK_LLM.model,
        )
        if (fallback.provider, fallback.model) != (primary.provider, primary.model):
            configs.append(fallback)
        else:
            logger.warning(
                "LLM fallback matches primary and will be ignored",
                extra={"provider": fallback.provider, "model": fallback.model},
            )
    return tuple(configs)


def _provider_config(role: str, provider: str, model: str) -> LLMProviderConfig:
    normalized_provider = _normalize_provider(provider)
    model = model.strip()
    if not model:
        raise LLMConfigurationError(f"{role} LLM model must be configured")

    return LLMProviderConfig(
        role=role,
        provider=normalized_provider,
        model=model,
        api_key=_api_key_for(normalized_provider),
        base_url=_base_url_for(normalized_provider),
        timeout=float(llm_config.LLM_TIMEOUT_SECONDS),
    )


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    aliases = {"gemini": "google"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"upstage", "openai", "google"}:
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")
    return normalized


def _api_key_for(provider: str) -> str:
    if provider == "upstage":
        return settings.UPSTAGE_API_KEY
    if provider == "openai":
        return settings.OPENAI_API_KEY
    if provider == "google":
        return settings.GOOGLE_API_KEY
    raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")


def _base_url_for(provider: str) -> str | None:
    if provider == "upstage":
        return llm_config.UPSTAGE_BASE_URL
    if provider == "openai":
        return llm_config.OPENAI_BASE_URL
    return None


def _build_chat_model(config: LLMProviderConfig) -> Any:
    if not config.api_key:
        raise LLMConfigurationError(f"{config.label} is missing an API key")

    logger.info(
        "Building LLM provider",
        extra={"provider": config.provider, "model": config.model, "role": config.role},
    )

    if config.provider == "upstage":
        from langchain_upstage import ChatUpstage

        kwargs: dict[str, Any] = {
            "api_key": config.api_key,
            "model": config.model,
            "timeout": config.timeout,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatUpstage(**kwargs)

    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "api_key": config.api_key,
            "model": config.model,
            "timeout": config.timeout,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)

    if config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            api_key=config.api_key,
            model=config.model,
            request_timeout=config.timeout,
        )

    raise LLMConfigurationError(f"Unsupported LLM provider: {config.provider}")


def _can_try_next(
    exc: Exception,
    current_index: int,
    configs: tuple[LLMProviderConfig, ...],
) -> bool:
    return current_index < len(configs) - 1 and _is_fallbackable(exc)


def _is_fallbackable(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, httpx.RequestError)):
        return True

    status_code = _status_code_from(exc)
    if status_code is not None:
        return status_code in {408, 409, 425, 429} or status_code >= 500

    message = str(exc).lower()
    fallback_markers = (
        "timeout",
        "timed out",
        "connection",
        "temporarily unavailable",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "504",
    )
    return any(marker in message for marker in fallback_markers)


def _status_code_from(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status

    return None


def _log_fallback_attempt(config: LLMProviderConfig, exc: Exception, operation: str) -> None:
    logger.warning(
        "LLM provider failed; trying fallback",
        extra={
            "provider": config.provider,
            "model": config.model,
            "role": config.role,
            "operation": operation,
            "error": str(exc),
        },
    )


def _log_fallback_success(config: LLMProviderConfig, operation: str) -> None:
    logger.info(
        "LLM fallback provider succeeded",
        extra={
            "provider": config.provider,
            "model": config.model,
            "role": config.role,
            "operation": operation,
        },
    )


def _configure_langsmith() -> None:
    if settings.LANGSMITH_API_KEY:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


_configure_langsmith()
llm = create_llm()
