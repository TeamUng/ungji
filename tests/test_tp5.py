from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.services.nodes.tp5 import _build_wrong_answer_summary, tp5


# ─── _build_wrong_answer_summary unit tests ──────────────────────────────────

def test_no_wrong_answers(case1_student, make_chat_state):
    # Force has_wrong_answers=False by using high_diligent_student (wrong_content_total=0)
    # but we can also override via a custom state
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP5,
    )
    # Manually set no wrong answers
    state = {**state, "has_wrong_answers": False}
    summary = _build_wrong_answer_summary(state)
    assert "오늘 틀린 문제가 없어요" in summary


def test_wrong_answers_all_reviewed(case2_student, make_chat_state):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    # wrong_content_total=3, force done_today=True
    state = {**state, "has_wrong_answers": True, "wrong_content_done_today": True}
    summary = _build_wrong_answer_summary(state)
    assert "다 복습했어요" in summary
    assert "3" in summary


def test_wrong_answers_partially_reviewed(case2_student, make_chat_state):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    # wrong_content_total=3, wrong_content_done=1 → 2 remaining
    state = {**state, "has_wrong_answers": True, "wrong_content_done_today": False}
    summary = _build_wrong_answer_summary(state)
    assert "3" in summary
    assert "2" in summary  # remaining = 3 - 1


# ─── tp5 node integration tests ──────────────────────────────────────────────

def test_response_shape(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    response = tp5(state)

    types = [m.type for m in response.messages]
    assert "text" in types
    assert "choices" in types


def test_wrong_summary_in_user_message_no_wrong(high_diligent_student, make_chat_state, mock_llm):
    state = make_chat_state(
        high_diligent_student,
        segment=Segment.HIGH_DILIGENT,
        grade_group=GradeGroup.MIDDLE,
        touchpoint=Touchpoint.TP5,
    )
    tp5(state)

    user_content = mock_llm.calls[0]["messages"][1].content
    assert "오늘 틀린 문제가 없어요" in user_content


def test_wrong_summary_in_user_message_partial(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    # wrong_content_total=3, wrong_content_done=1, done_today=False
    state = {**state, "wrong_content_done_today": False}
    tp5(state)

    user_content = mock_llm.calls[0]["messages"][1].content
    assert "남아있어요" in user_content
