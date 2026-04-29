from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.services.nodes.motivator import motivator
from app.services.prompts.personas import get_persona


def _prompt_text(mock_llm) -> str:
    return "\n".join(message.content for message in mock_llm.calls[0]["messages"])


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    response = motivator(state)

    types = [message.type for message in response.messages]
    assert "text" in types


def test_system_prompt_uses_lower_persona(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    motivator(state)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert get_persona(GradeGroup.LOWER) in system_content


def test_situation_contains_student_and_task_info(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    motivator(state)

    prompt_text = _prompt_text(mock_llm)
    assert case1_student["profile"]["name"] in prompt_text
    assert case1_student["today_tasks"][0]["unit"] in prompt_text


def test_chat_history_is_passed_to_llm(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    state["chat_history"] = [HumanMessage(content="오늘은 국어부터 할래요")]

    motivator(state)

    contents = [message.content for message in mock_llm.calls[0]["messages"]]
    assert "오늘은 국어부터 할래요" in contents


def test_response_does_not_expose_segment_name(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    response = motivator(state)

    content = response.messages[0].content
    assert "LOW_LAZY" not in content
    assert Segment.LOW_LAZY.value not in content
