from __future__ import annotations

import importlib
import os
import sys
import types
from dataclasses import dataclass, field

import pytest

from app.core.config import configure_langsmith_tracing, settings


@dataclass
class FakeLLMResponse:
    content: str
    tool_calls: list = field(default_factory=list)


class FakeChatOpenAI:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.instances.append(self)


def _setup_fake_openai(monkeypatch):
    fake_module = types.ModuleType("langchain_openai")
    fake_module.ChatOpenAI = FakeChatOpenAI
    FakeChatOpenAI.instances = []
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)


def test_llm_client_initializes_motivator_helper_and_judge_alias_with_settings(monkeypatch):
    _setup_fake_openai(monkeypatch)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setattr(settings, "OPENROUTER_BASE_URL", "https://example.test/api/v1")
    monkeypatch.setattr(settings, "MOTIVATOR_MODEL", "openai/gpt-test-motivator")
    monkeypatch.setattr(settings, "HELPER_MODEL", "google/gemini-test-helper")
    monkeypatch.setattr(settings, "LLM_TEMPERATURE", 0.5)
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 42)
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "")
    monkeypatch.setattr(settings, "UNGJI_DISABLE_LANGSMITH_TRACING", False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    sys.modules.pop("app.clients.llm", None)

    llm_module = importlib.import_module("app.clients.llm")

    assert len(FakeChatOpenAI.instances) == 2
    assert llm_module.motivator_llm is FakeChatOpenAI.instances[0]
    assert llm_module.helper_llm is FakeChatOpenAI.instances[1]
    assert llm_module.llm is llm_module.helper_llm

    motivator_kwargs = llm_module.motivator_llm.kwargs
    assert motivator_kwargs["api_key"] == "test-or-key"
    assert motivator_kwargs["base_url"] == "https://example.test/api/v1"
    assert motivator_kwargs["model"] == "openai/gpt-test-motivator"
    assert motivator_kwargs["temperature"] == 0.5
    assert motivator_kwargs["timeout"] == 42
    assert motivator_kwargs["max_retries"] == 1
    assert "HTTP-Referer" in motivator_kwargs["default_headers"]

    helper_kwargs = llm_module.helper_llm.kwargs
    assert helper_kwargs["model"] == "google/gemini-test-helper"
    assert helper_kwargs["api_key"] == "test-or-key"


def test_llm_client_enables_langsmith_tracing_when_key_exists(monkeypatch):
    _setup_fake_openai(monkeypatch)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.setattr(settings, "UNGJI_DISABLE_LANGSMITH_TRACING", False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    sys.modules.pop("app.clients.llm", None)

    importlib.import_module("app.clients.llm")

    assert FakeChatOpenAI.instances
    assert os.environ["LANGCHAIN_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGSMITH_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_llm_client_respects_langsmith_disable_flag(monkeypatch):
    _setup_fake_openai(monkeypatch)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.setattr(settings, "UNGJI_DISABLE_LANGSMITH_TRACING", True)
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


def test_langsmith_tracing_clears_cached_env_lookup(monkeypatch):
    from langsmith import utils as langsmith_utils

    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.setattr(settings, "UNGJI_DISABLE_LANGSMITH_TRACING", False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    langsmith_utils.get_env_var.cache_clear()

    assert langsmith_utils.get_env_var("TRACING", default="") == ""

    configure_langsmith_tracing()

    assert langsmith_utils.get_env_var("TRACING", default="") == "true"


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


def test_llm_judge_sync_uses_central_chat_model_invoke():
    from app.guardrails.strategies.llm_judge import LLMJudge

    class FakeFallbackLLM:
        def __init__(self):
            self.calls = []

        def invoke(self, messages, **kwargs):
            self.calls.append({"messages": messages, "kwargs": kwargs})
            return FakeLLMResponse(content='{"tone": {"passed": true, "reason": null}}')

    fake_llm = FakeFallbackLLM()

    verdict = LLMJudge(chat_model=fake_llm).evaluate_sync("judge system", "candidate")

    assert verdict == {"tone": {"passed": True, "reason": None}}
    assert fake_llm.calls[0]["kwargs"] == {"temperature": 0}
