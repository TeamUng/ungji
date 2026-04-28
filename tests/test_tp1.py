from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.services.nodes.tp1 import tp1


def test_case1_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    response = tp1(state)

    types = [m.type for m in response.messages]
    assert "text" in types


def test_case1_system_prompt_uses_lower_persona(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    tp1(state)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert "이모" in system_content or "삼촌" in system_content


def test_case2_response_shape(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP1,
    )
    response = tp1(state)

    types = [m.type for m in response.messages]
    assert "text" in types


def test_case2_system_prompt_uses_upper_persona(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP1,
    )
    tp1(state)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert "코치" in system_content


def test_task_info_in_user_message(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    tp1(state)

    user_content = mock_llm.calls[0]["messages"][1].content
    assert "민준" in user_content
    assert "짧은 글 읽기" in user_content
