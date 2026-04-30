from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.services.nodes.motivator import motivator


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP3,
    )
    response = motivator(state)

    types = [message.type for message in response.messages]
    assert "text" in types


def test_current_task_and_remaining_count_in_situation(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP3,
    )
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    current_task = case1_student["today_tasks"][0]
    assert current_task["subject"] in prompt_text
    assert current_task["unit"] in prompt_text
    assert "아직 남은 단원 수는 1개" in prompt_text


def test_remaining_problem_count_in_situation(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP3,
    )
    state["current_task_remaining_count"] = 2
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    assert "현재 단원에서 남은 문제 수는 2문제" in prompt_text
