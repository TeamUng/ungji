from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.enums import Touchpoint, UseCase
from app.core.logging import get_logger
from app.schemas.chat import ChatState
from app.services.nodes.classify import classify
from app.services.nodes.common import make_chat_response
from app.services.nodes.tp1 import tp1
from app.services.nodes.tp2 import tp2
from app.services.nodes.tp3 import tp3
from app.services.nodes.tp4 import tp4
from app.services.nodes.tp5 import tp5

logger = get_logger(__name__)

# ─── LangGraph 노드 래퍼 ──────────────────────────────────────────────────────
# TP 노드들은 ChatResponse 또는 dict를 반환하므로,
# LangGraph state update dict 형식으로 통일한다.

def _tp1_node(state: ChatState) -> dict:
    return {"response": tp1(state)}


def _tp2_node(state: ChatState) -> dict:
    return {"response": tp2(state)}


def _tp3_node(state: ChatState) -> dict:
    return {"response": tp3(state)}


def _tp4_node(state: ChatState) -> dict:
    result = tp4(state)
    messages = result["tp4_response"]
    return {"response": make_chat_response(state["thread_id"], messages)}


def _tp5_node(state: ChatState) -> dict:
    return {"response": tp5(state)}


# ─── 라우팅 함수 ──────────────────────────────────────────────────────────────

def _route(state: ChatState) -> str:
    use_case = state["use_case"]
    touchpoint = state["current_touchpoint"]

    if use_case == UseCase.LEARNING:
        if touchpoint != Touchpoint.TP4:
            raise ValueError(
                f"use_case=learning은 tp4만 허용됩니다. 받은 값: {touchpoint}"
            )
        return "tp4"

    talk_routes = {
        Touchpoint.TP1: "tp1",
        Touchpoint.TP2: "tp2",
        Touchpoint.TP3: "tp3",
        Touchpoint.TP5: "tp5",
    }

    if touchpoint not in talk_routes:
        raise ValueError(
            f"use_case=talk에서 지원하지 않는 touchpoint: {touchpoint}"
        )

    return talk_routes[touchpoint]


# ─── 그래프 조립 ──────────────────────────────────────────────────────────────

_builder = StateGraph(ChatState)

_builder.add_node("classify", classify)
_builder.add_node("tp1", _tp1_node)
_builder.add_node("tp2", _tp2_node)
_builder.add_node("tp3", _tp3_node)
_builder.add_node("tp4", _tp4_node)
_builder.add_node("tp5", _tp5_node)

_builder.add_edge(START, "classify")
_builder.add_conditional_edges("classify", _route)

for _tp_node in ("tp1", "tp2", "tp3", "tp4", "tp5"):
    _builder.add_edge(_tp_node, END)

memory = InMemorySaver()
graph = _builder.compile(checkpointer=memory)
