from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.data.loader import StudentRecord
from app.services.graph import graph


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
    assert "choices" in types


def test_case1_learning_tp4_routes_to_tp4(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP4)
    assert result["response"] is not None


# ─── 케이스 2 라우팅 ──────────────────────────────────────────────────────────

def test_case2_talk_tp1_routes_to_tp1(case2_student, mock_llm):
    result = _invoke(case2_student, UseCase.TALK, Touchpoint.TP1)
    assert result["response"] is not None
    types = [m.type for m in result["response"].messages]
    assert "text" in types
    assert "choices" in types


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


# ─── 잘못된 입력 예외 처리 ────────────────────────────────────────────────────

def test_invalid_touchpoint_learning_with_tp1_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP1)


def test_invalid_touchpoint_talk_with_tp4_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.TALK, Touchpoint.TP4)
