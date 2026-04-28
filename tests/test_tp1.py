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
    assert "choices" in types


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
    assert "choices" in types


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


def test_choices_differ_between_cases(case1_student, case2_student, make_chat_state, mock_llm):
    state1 = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    state2 = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP1,
    )

    response1 = tp1(state1)
    response2 = tp1(state2)

    choices1 = next(m for m in response1.messages if m.type == "choices")
    choices2 = next(m for m in response2.messages if m.type == "choices")

    labels1 = {item.label for item in choices1.items}
    labels2 = {item.label for item in choices2.items}
    assert labels1 != labels2
