from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.data.loader import StudentRecord
from app.services.graph import graph
from app.services.prompts.agents import HELPER_ROLE, MOTIVATOR_ROLE


def _invoke(student: StudentRecord, use_case: UseCase, touchpoint: Touchpoint) -> dict:
    """그래프를 invoke하고 최종 state를 반환한다."""
    config = {"configurable": {"thread_id": f"test-{student['student_id']}-{touchpoint}"}}
    initial = {
        "thread_id": f"test-{student['student_id']}-{touchpoint}",
        "student_id": student["student_id"],
        "use_case": use_case,
        "current_touchpoint": touchpoint,
        "response": None,
    }
    with patch("app.services.nodes.classify.load_student", return_value=student):
        return graph.invoke(initial, config=config)


# ─── 케이스 1 라우팅 ──────────────────────────────────────────────────────────

def test_case1_talk_tp1_routes_to_tp1(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.TALK, Touchpoint.TP1)
    assert result["response"] is not None
    types = [m.type for m in result["response"].messages]
    assert "text" in types


def test_case1_learning_tp4_routes_to_tp4(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP4)
    assert result["response"] is not None


# ─── 케이스 2 라우팅 ──────────────────────────────────────────────────────────

def test_case2_talk_tp1_routes_to_tp1(case2_student, mock_llm):
    result = _invoke(case2_student, UseCase.TALK, Touchpoint.TP1)
    assert result["response"] is not None
    types = [m.type for m in result["response"].messages]
    assert "text" in types


def test_case2_learning_tp4_routes_to_tp4(case2_student, mock_llm):
    result = _invoke(case2_student, UseCase.LEARNING, Touchpoint.TP4)
    assert result["response"] is not None


# ─── 보조 터치포인트 라우팅 ───────────────────────────────────────────────────

def test_tp2_routing(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.TALK, Touchpoint.TP2)
    assert result["response"] is not None


def test_tp3_routing(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.TALK, Touchpoint.TP3)
    assert result["response"] is not None


def test_tp5_routing(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.TALK, Touchpoint.TP5)
    assert result["response"] is not None


def test_chat_with_non_tp4_routes_to_motivator(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.CHAT, Touchpoint.TP1)

    assert result["response"] is not None
    system_content = mock_llm.calls[0]["messages"][0].content
    assert MOTIVATOR_ROLE in system_content


def test_chat_with_tp4_routes_to_helper(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.CHAT, Touchpoint.TP4)

    assert result["response"] is not None
    system_content = mock_llm.calls[0]["messages"][0].content
    assert HELPER_ROLE in system_content


# ─── 잘못된 입력 예외 처리 ────────────────────────────────────────────────────

def test_invalid_touchpoint_learning_with_tp1_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP1)


def test_invalid_touchpoint_talk_with_tp4_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.TALK, Touchpoint.TP4)


# ─── 세션 지속성 — classify는 첫 턴에만 실행 ─────────────────────────────────

def test_classify_runs_only_on_first_turn(case1_student, mock_llm):
    """같은 thread_id로 2번 호출하면 classify(load_student)는 1번만 실행된다."""
    thread_id = f"session-test-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        "thread_id": thread_id,
        "student_id": case1_student["student_id"],
        "use_case": UseCase.TALK,
        "current_touchpoint": Touchpoint.TP1,
        "response": None,
    }

    with patch("app.services.nodes.classify.load_student", return_value=case1_student) as mock_load:
        # 턴 1
        graph.invoke(initial, config=config)
        assert mock_load.call_count == 1

        # 턴 2 — 같은 thread_id, chat_history에 사용자 입력 추가
        turn2 = {
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="too_long")],
        }
        graph.invoke(turn2, config=config)
        # classify(load_student)는 여전히 1번만 호출됐어야 한다
        assert mock_load.call_count == 1


def test_chat_history_preserved_on_second_turn(case1_student, mock_llm):
    """턴 2에서 chat_history가 classify에 의해 초기화되지 않는다."""
    thread_id = f"session-history-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        "thread_id": thread_id,
        "student_id": case1_student["student_id"],
        "use_case": UseCase.TALK,
        "current_touchpoint": Touchpoint.TP1,
        "response": None,
    }

    with patch("app.services.nodes.classify.load_student", return_value=case1_student):
        graph.invoke(initial, config=config)

        turn2 = {
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="too_long")],
        }
        result = graph.invoke(turn2, config=config)

    # chat_history가 보존되어 있어야 한다
    history = result["chat_history"]
    contents = [m.content for m in history]
    assert "too_long" in contents


def test_first_turn_chat_history_survives_classify_for_tp4_problem_id(case2_student, mock_llm):
    thread_id = f"session-first-history-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    initial = {
        "thread_id": thread_id,
        "student_id": case2_student["student_id"],
        "use_case": UseCase.LEARNING,
        "current_touchpoint": Touchpoint.TP4,
        "chat_history": [HumanMessage(content="math_ratio_saltwater_001")],
        "response": None,
    }

    with patch("app.services.nodes.classify.load_student", return_value=case2_student):
        result = graph.invoke(initial, config=config)

    assert result["current_problem"]["problem_id"] == "math_ratio_saltwater_001"
    contents = [message.content for message in result["chat_history"]]
    assert "math_ratio_saltwater_001" in contents
