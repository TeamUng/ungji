from __future__ import annotations

import importlib
import os
import sys
import types

from app.core.config import settings


class FakeChatUpstage:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.instances.append(self)


def test_upstage_client_initializes_chat_upstage_with_settings(monkeypatch):
    fake_module = types.ModuleType("langchain_upstage")
    fake_module.ChatUpstage = FakeChatUpstage
    FakeChatUpstage.instances = []

    monkeypatch.setitem(sys.modules, "langchain_upstage", fake_module)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "test-upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    sys.modules.pop("app.clients.upstage", None)

    upstage = importlib.import_module("app.clients.upstage")

    assert upstage.llm is FakeChatUpstage.instances[0]
    assert upstage.llm.kwargs == {
        "api_key": "test-upstage-key",
        "model": "solar-pro",
    }


def test_upstage_client_enables_langsmith_tracing_when_key_exists(monkeypatch):
    fake_module = types.ModuleType("langchain_upstage")
    fake_module.ChatUpstage = FakeChatUpstage
    FakeChatUpstage.instances = []

    monkeypatch.setitem(sys.modules, "langchain_upstage", fake_module)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "test-upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    sys.modules.pop("app.clients.upstage", None)

    importlib.import_module("app.clients.upstage")

    assert FakeChatUpstage.instances
    assert os.environ["LANGCHAIN_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
