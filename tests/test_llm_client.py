from __future__ import annotations

import importlib
import os
import sys
import types

from app.core.config import settings


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


def test_llm_client_initializes_motivator_and_helper_with_settings(monkeypatch):
    _setup_fake_openai(monkeypatch)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setattr(settings, "OPENROUTER_BASE_URL", "https://example.test/api/v1")
    monkeypatch.setattr(settings, "MOTIVATOR_MODEL", "openai/gpt-test-motivator")
    monkeypatch.setattr(settings, "HELPER_MODEL", "google/gemini-test-helper")
    monkeypatch.setattr(settings, "LLM_TEMPERATURE", 0.5)
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 42)
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    sys.modules.pop("app.clients.llm", None)

    llm_module = importlib.import_module("app.clients.llm")

    assert len(FakeChatOpenAI.instances) == 2
    assert llm_module.motivator_llm is FakeChatOpenAI.instances[0]
    assert llm_module.helper_llm is FakeChatOpenAI.instances[1]

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
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    sys.modules.pop("app.clients.llm", None)

    importlib.import_module("app.clients.llm")

    assert FakeChatOpenAI.instances
    assert os.environ["LANGCHAIN_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
