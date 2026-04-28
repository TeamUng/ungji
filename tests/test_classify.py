from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.enums import GradeGroup, Segment
from app.data.loader import StudentRecord
from app.schemas.chat import ChatState
from app.services.nodes.classify import classify, get_grade_group, get_segment


# ─── get_segment ─────────────────────────────────────────────────────────────

def test_case1_segment(case1_student: StudentRecord) -> None:
    segment = get_segment(case1_student["profile"], case1_student["learning_pattern"])
    assert segment == Segment.LOW_LAZY


def test_case2_segment(case2_student: StudentRecord) -> None:
    segment = get_segment(case2_student["profile"], case2_student["learning_pattern"])
    assert segment == Segment.LOW_DILIGENT


def test_high_diligent_segment(high_diligent_student: StudentRecord) -> None:
    segment = get_segment(high_diligent_student["profile"], high_diligent_student["learning_pattern"])
    assert segment == Segment.HIGH_DILIGENT


def test_high_lazy_segment(high_lazy_student: StudentRecord) -> None:
    segment = get_segment(high_lazy_student["profile"], high_lazy_student["learning_pattern"])
    assert segment == Segment.HIGH_LAZY


def test_none_wrong_content_rate_does_not_penalize_diligence(high_diligent_student: StudentRecord) -> None:
    # wrong_content_rate=None → 오답 자체가 없으므로 성실도 2차 조건 자동 통과
    assert high_diligent_student["learning_pattern"]["wrong_content_rate"] is None
    segment = get_segment(high_diligent_student["profile"], high_diligent_student["learning_pattern"])
    assert segment == Segment.HIGH_DILIGENT


# ─── get_grade_group ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("grade,expected", [
    (1, GradeGroup.LOWER),
    (2, GradeGroup.LOWER),
    (3, GradeGroup.MIDDLE),
    (4, GradeGroup.MIDDLE),
    (5, GradeGroup.UPPER),
    (6, GradeGroup.UPPER),
])
def test_grade_boundaries(grade: int, expected: GradeGroup) -> None:
    assert get_grade_group(grade) == expected


def test_case1_grade_group(case1_student: StudentRecord) -> None:
    grade_group = get_grade_group(case1_student["profile"]["grade"])
    assert grade_group == GradeGroup.LOWER


def test_case2_grade_group(case2_student: StudentRecord) -> None:
    grade_group = get_grade_group(case2_student["profile"]["grade"])
    assert grade_group == GradeGroup.UPPER


# ─── classify 노드 (load_student mock) ───────────────────────────────────────

def _minimal_state(student_id: str) -> ChatState:
    from app.core.enums import Segment, GradeGroup, UseCase, Touchpoint

    return {  # type: ignore[return-value]
        "thread_id": f"thread-{student_id}",
        "student_id": student_id,
        "student_profile": None,  # type: ignore[dict-item]
        "learning_history": None,  # type: ignore[dict-item]
        "learning_pattern": None,  # type: ignore[dict-item]
        "wrong_answer_pattern": None,  # type: ignore[dict-item]
        "today_tasks": [],
        "completed_tasks": [],
        "current_task": None,
        "has_wrong_answers": False,
        "wrong_content_done_today": False,
        "today_score": 0,
        "use_case": UseCase.TALK,
        "grade_group": GradeGroup.LOWER,
        "segment": Segment.LOW_LAZY,
        "chat_history": [],
        "current_touchpoint": Touchpoint.TP1,
    }


def test_classify_node_case1(case1_student: StudentRecord) -> None:
    state = _minimal_state(case1_student["student_id"])
    with patch("app.services.nodes.classify.load_student", return_value=case1_student):
        result = classify(state)

    assert result["segment"] == Segment.LOW_LAZY
    assert result["grade_group"] == GradeGroup.LOWER
    assert result["student_profile"] == case1_student["profile"]


def test_classify_node_case2(case2_student: StudentRecord) -> None:
    state = _minimal_state(case2_student["student_id"])
    with patch("app.services.nodes.classify.load_student", return_value=case2_student):
        result = classify(state)

    assert result["segment"] == Segment.LOW_DILIGENT
    assert result["grade_group"] == GradeGroup.UPPER
    assert result["student_profile"] == case2_student["profile"]


def test_classify_node_initializes_completed_tasks_empty(case1_student: StudentRecord) -> None:
    state = _minimal_state(case1_student["student_id"])
    with patch("app.services.nodes.classify.load_student", return_value=case1_student):
        result = classify(state)

    assert result["completed_tasks"] == []
    assert "chat_history" not in result


def test_classify_node_has_wrong_answers(case1_student: StudentRecord) -> None:
    # case1 학생은 wrong_content_total=2 → has_wrong_answers=True
    state = _minimal_state(case1_student["student_id"])
    with patch("app.services.nodes.classify.load_student", return_value=case1_student):
        result = classify(state)

    assert result["has_wrong_answers"] is True
    assert result["wrong_content_done_today"] is False


def test_classify_node_no_wrong_answers(high_diligent_student: StudentRecord) -> None:
    # 오답 없는 학생(wrong_content_total=0) → has_wrong_answers=False
    state = _minimal_state(high_diligent_student["student_id"])
    with patch("app.services.nodes.classify.load_student", return_value=high_diligent_student):
        result = classify(state)

    assert result["has_wrong_answers"] is False
