from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.schemas.chat import Task
from app.services.nodes.motivator import motivator


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP2,
    )
    response = motivator(state)

    types = [message.type for message in response.messages]
    assert "text" in types


def test_progress_info_in_situation(case2_student, make_chat_state, mock_llm):
    completed: list[Task] = [case2_student["today_tasks"][0]]
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP2,
        completed_tasks=completed,
    )
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    assert "1/1" in prompt_text
    assert "모든 과제 완료" in prompt_text
