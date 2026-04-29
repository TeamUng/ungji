from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.data.loader import load_student
from app.schemas.chat import Task
from app.services.nodes.motivator import motivator


def _last_prompt(mock_llm) -> str:
    return mock_llm.calls[0]["messages"][-1].content


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

    prompt_text = _last_prompt(mock_llm)
    assert "오늘 할 단원 1개를 모두 끝냈어" in prompt_text
    assert "Book Club" in prompt_text


def test_tp2_recommends_only_remaining_units(make_chat_state, mock_llm):
    student = load_student("lower-low-lazy")
    completed: list[Task] = [student["today_tasks"][0]]
    state = make_chat_state(
        student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP2,
        completed_tasks=completed,
    )
    motivator(state)

    prompt_text = _last_prompt(mock_llm)

    assert completed[0]["unit"] in prompt_text
    assert "아직 남은 단원은 3개" in prompt_text
    for task in student["today_tasks"][1:]:
        assert task["unit"] in prompt_text
    assert "새 문제" in prompt_text
    assert "예시" in prompt_text
    assert "하나만 추천" in prompt_text
