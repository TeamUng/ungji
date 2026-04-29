from __future__ import annotations

import importlib
import os
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.clients import llm_config


@dataclass
class FakeLLMResponse:
    content: str
    tool_calls: list = field(default_factory=list)


class FakeChatBase:
    instances: list["FakeChatBase"] = []
    fail_with: Exception | None = None
    response_content = "ok"

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list[dict[str, Any]] = []
        self.bound_tools: list[list[Any]] = []
        self.__class__.instances.append(self)

    def bind_tools(self, tools):
        self.bound_tools.append(list(tools))
        return self

    def invoke(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self.__class__.fail_with:
            raise self.__class__.fail_with
        return FakeLLMResponse(content=self.__class__.response_content)

    async def ainvoke(self, messages, **kwargs):
        return self.invoke(messages, **kwargs)

    def stream(self, messages, **kwargs):
        yield self.invoke(messages, **kwargs)


class FakeChatUpstage(FakeChatBase):
    instances = []
    fail_with = None
    response_content = "upstage response"


class FakeChatOpenAI(FakeChatBase):
    instances = []
    fail_with = None
    response_content = "openai response"


class FakeChatGoogle(FakeChatBase):
    instances = []
    fail_with = None
    response_content = "google response"


def _install_fake_provider_modules(monkeypatch):
    upstage_module = types.ModuleType("langchain_upstage")
    upstage_module.ChatUpstage = FakeChatUpstage
    openai_module = types.ModuleType("langchain_openai")
    openai_module.ChatOpenAI = FakeChatOpenAI
    google_module = types.ModuleType("langchain_google_genai")
    google_module.ChatGoogleGenerativeAI = FakeChatGoogle

    monkeypatch.setitem(sys.modules, "langchain_upstage", upstage_module)
    monkeypatch.setitem(sys.modules, "langchain_openai", openai_module)
    monkeypatch.setitem(sys.modules, "langchain_google_genai", google_module)


def _reset_fakes():
    for fake in (FakeChatUpstage, FakeChatOpenAI, FakeChatGoogle):
        fake.instances = []
        fake.fail_with = None


def _import_llm(monkeypatch, *, fallback_provider="", fallback_model=""):
    _reset_fakes()
    _install_fake_provider_modules(monkeypatch)
    monkeypatch.setattr(
        llm_config,
        "PRIMARY_LLM",
        llm_config.LLMModelConfig(provider="upstage", model="solar-pro2"),
    )
    monkeypatch.setattr(
        llm_config,
        "FALLBACK_LLM",
        (
            llm_config.LLMModelConfig(provider=fallback_provider, model=fallback_model)
            if fallback_provider and fallback_model
            else None
        ),
    )
    monkeypatch.setattr(llm_config, "LLM_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(llm_config, "UPSTAGE_BASE_URL", "https://api.upstage.ai/v1/solar")
    monkeypatch.setattr(llm_config, "OPENAI_BASE_URL", None)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "upstage-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "google-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "")
    sys.modules.pop("app.clients.llm", None)
    return importlib.import_module("app.clients.llm")


def test_primary_provider_is_used_when_available(monkeypatch):
    llm_module = _import_llm(monkeypatch, fallback_provider="openai", fallback_model="gpt-test")

    response = llm_module.llm.invoke(["hello"])

    assert response.content == "upstage response"
    assert len(FakeChatUpstage.instances) == 1
    assert FakeChatUpstage.instances[0].kwargs == {
        "api_key": "upstage-key",
        "model": "solar-pro2",
        "timeout": 30.0,
        "base_url": "https://api.upstage.ai/v1/solar",
    }
    assert FakeChatOpenAI.instances == []


def test_fallback_provider_is_used_for_service_failures(monkeypatch):
    llm_module = _import_llm(monkeypatch, fallback_provider="openai", fallback_model="gpt-test")
    FakeChatUpstage.fail_with = httpx.ConnectError("upstage unavailable")

    response = llm_module.llm.invoke(["hello"])

    assert response.content == "openai response"
    assert len(FakeChatOpenAI.instances) == 1
    assert FakeChatOpenAI.instances[0].kwargs == {
        "api_key": "openai-key",
        "model": "gpt-test",
        "timeout": 30.0,
    }


def test_gemini_alias_builds_google_provider(monkeypatch):
    llm_module = _import_llm(monkeypatch, fallback_provider="gemini", fallback_model="gemini-test")
    FakeChatUpstage.fail_with = httpx.ConnectError("upstage unavailable")

    response = llm_module.llm.invoke(["hello"])

    assert response.content == "google response"
    assert FakeChatGoogle.instances[0].kwargs == {
        "api_key": "google-key",
        "model": "gemini-test",
        "request_timeout": 30.0,
    }


def test_bind_tools_is_applied_to_fallback_provider(monkeypatch):
    llm_module = _import_llm(monkeypatch, fallback_provider="openai", fallback_model="gpt-test")
    FakeChatUpstage.fail_with = httpx.ConnectError("upstage unavailable")

    llm_module.llm.bind_tools(["send_text"]).invoke(["hello"])

    assert FakeChatOpenAI.instances[0].bound_tools == [["send_text"]]


def test_configuration_errors_do_not_fallback(monkeypatch):
    llm_module = _import_llm(monkeypatch, fallback_provider="openai", fallback_model="gpt-test")
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "")

    with pytest.raises(llm_module.LLMCallError):
        llm_module.create_llm().invoke(["hello"])

    assert FakeChatOpenAI.instances == []


def test_langsmith_tracing_env_is_configured(monkeypatch):
    _reset_fakes()
    _install_fake_provider_modules(monkeypatch)
    monkeypatch.setattr(
        llm_config,
        "PRIMARY_LLM",
        llm_config.LLMModelConfig(provider="upstage", model="solar-pro2"),
    )
    monkeypatch.setattr(llm_config, "FALLBACK_LLM", None)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.delenv("UNGJI_DISABLE_LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    sys.modules.pop("app.clients.llm", None)

    importlib.import_module("app.clients.llm")

    assert os.environ["LANGCHAIN_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGSMITH_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_langsmith_tracing_respects_disable_flag(monkeypatch):
    _reset_fakes()
    _install_fake_provider_modules(monkeypatch)
    monkeypatch.setattr(
        llm_config,
        "PRIMARY_LLM",
        llm_config.LLMModelConfig(provider="upstage", model="solar-pro2"),
    )
    monkeypatch.setattr(llm_config, "FALLBACK_LLM", None)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.setenv("UNGJI_DISABLE_LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    sys.modules.pop("app.clients.llm", None)

    importlib.import_module("app.clients.llm")

    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert "LANGCHAIN_API_KEY" not in os.environ
    assert "LANGSMITH_API_KEY" not in os.environ


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_content", "expected"),
    [
        (
            '```json\n{"tone": {"passed": true, "reason": null}}\n```',
            {"tone": {"passed": True, "reason": None}},
        ),
        (
            '검사 결과입니다.\n{"tone": {"passed": true, "reason": null}}\n다음 응답을 사용하세요.',
            {"tone": {"passed": True, "reason": None}},
        ),
        (
            '{"tone": {"passed": false, "reason": "too {harsh}"}}',
            {"tone": {"passed": False, "reason": "too {harsh}"}},
        ),
    ],
)
async def test_llm_judge_parses_common_json_wrappers(raw_content, expected):
    from app.guardrails.strategies.llm_judge import LLMJudge

    class FakeFallbackLLM:
        def __init__(self):
            self.calls = []

        async def ainvoke(self, messages, **kwargs):
            self.calls.append({"messages": messages, "kwargs": kwargs})
            return FakeLLMResponse(content=raw_content)

    fake_llm = FakeFallbackLLM()

    verdict = await LLMJudge(chat_model=fake_llm).evaluate("judge system", "candidate")

    assert verdict == expected
    assert fake_llm.calls[0]["kwargs"] == {"temperature": 0}
