from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.schemas.chat import Task
from app.services.nodes.tp2 import tp2


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP2,
    )
    response = tp2(state)

    types = [m.type for m in response.messages]
    assert "text" in types


def test_progress_info_in_user_message(case2_student, make_chat_state, mock_llm):
    completed: list[Task] = [case2_student["today_tasks"][0]]
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP2,
        completed_tasks=completed,
    )
    tp2(state)

    user_content = mock_llm.calls[0]["messages"][1].content
    assert "1/1" in user_content or "1" in user_content
