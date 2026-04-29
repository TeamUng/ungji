from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.enums import Touchpoint, UseCase
from app.core.logging import get_logger
from app.schemas.chat import ChatState
from app.services.nodes.classify import classify
from app.services.nodes.common import make_chat_response
from app.services.nodes.helper import helper
from app.services.nodes.motivator import motivator

logger = get_logger(__name__)

# ─── LangGraph 노드 래퍼 ──────────────────────────────────────────────────────

def _motivator_node(state: ChatState) -> dict:
    return {"response": motivator(state)}


def _helper_node(state: ChatState) -> dict:
    result = helper(state)
    messages = result["helper_response"]
    extra = {"response": make_chat_response(state["thread_id"], messages)}
    if "current_problem" in result:
        extra["current_problem"] = result["current_problem"]
    return extra


# ─── 라우팅 함수 ──────────────────────────────────────────────────────────────

def _route(state: ChatState) -> str:
    use_case = state["use_case"]
    touchpoint = state["current_touchpoint"]

    if use_case == UseCase.LEARNING:
        if touchpoint != Touchpoint.TP4:
            raise ValueError(
                f"use_case=learning은 tp4만 허용됩니다. 받은 값: {touchpoint}"
            )
        return "helper"

    if use_case == UseCase.CHAT:
        if touchpoint == Touchpoint.TP4:
            return "helper"
        return "motivator"

    if touchpoint == Touchpoint.TP4:
        raise ValueError(
            f"use_case=talk에서 tp4는 허용되지 않습니다."
        )
    if touchpoint in (Touchpoint.TP1, Touchpoint.TP2, Touchpoint.TP3, Touchpoint.TP5):
        return "motivator"

    raise ValueError(f"지원하지 않는 touchpoint: {touchpoint}")


# ─── 진입 라우팅 ─────────────────────────────────────────────────────────────

def _entry_route(state: ChatState) -> str:
    """첫 턴(student_profile 없음)이면 classify, 이후 턴이면 바로 노드로."""
    if state.get("student_profile") is None:
        return "classify"
    return _route(state)


# ─── 그래프 조립 ──────────────────────────────────────────────────────────────

_builder = StateGraph(ChatState)

_builder.add_node("classify", classify)
_builder.add_node("motivator", _motivator_node)
_builder.add_node("helper", _helper_node)

_builder.add_conditional_edges(START, _entry_route)
_builder.add_conditional_edges("classify", _route)

memory = InMemorySaver()
graph = _builder.compile(checkpointer=memory)
