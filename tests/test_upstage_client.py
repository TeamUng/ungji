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
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    sys.modules.pop("app.clients.upstage", None)

    upstage = importlib.import_module("app.clients.upstage")

    assert upstage.llm is FakeChatUpstage.instances[0]
    assert upstage.llm.kwargs == {
        "api_key": "test-upstage-key",
        "model": "solar-pro2",
        "timeout": 30,
    }


def test_upstage_client_enables_langsmith_tracing_when_key_exists(monkeypatch):
    fake_module = types.ModuleType("langchain_upstage")
    fake_module.ChatUpstage = FakeChatUpstage
    FakeChatUpstage.instances = []

    monkeypatch.setitem(sys.modules, "langchain_upstage", fake_module)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "test-upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.delenv("UNGJI_DISABLE_LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    sys.modules.pop("app.clients.upstage", None)

    importlib.import_module("app.clients.upstage")

    assert FakeChatUpstage.instances
    assert os.environ["LANGCHAIN_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGSMITH_API_KEY"] == "test-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_upstage_client_respects_test_tracing_disable_flag(monkeypatch):
    fake_module = types.ModuleType("langchain_upstage")
    fake_module.ChatUpstage = FakeChatUpstage
    FakeChatUpstage.instances = []

    monkeypatch.setitem(sys.modules, "langchain_upstage", fake_module)
    monkeypatch.setattr(settings, "UPSTAGE_API_KEY", "test-upstage-key")
    monkeypatch.setattr(settings, "LANGSMITH_API_KEY", "test-langsmith-key")
    monkeypatch.setattr(settings, "LANGSMITH_PROJECT", "test-project")
    monkeypatch.setenv("UNGJI_DISABLE_LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    sys.modules.pop("app.clients.upstage", None)

    importlib.import_module("app.clients.upstage")

    assert FakeChatUpstage.instances
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"
    assert os.environ["LANGSMITH_TRACING"] == "false"
