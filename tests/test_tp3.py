from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.services.nodes.tp3 import tp3


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP3,
    )
    response = tp3(state)

    types = [m.type for m in response.messages]
    assert "text" in types


def test_current_task_in_user_message(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP3,
    )
    tp3(state)

    user_content = mock_llm.calls[0]["messages"][1].content
    # current_task is the first today_task: 국어 - 짧은 글 읽기
    assert "국어" in user_content
    assert "짧은 글 읽기" in user_content
