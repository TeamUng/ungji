from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.services.nodes.motivator import _build_wrong_answer_summary, motivator


def test_no_wrong_answers_summary(case1_student, make_chat_state):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP5,
    )
    state = {**state, "has_wrong_answers": False}

    summary = _build_wrong_answer_summary(state)

    assert "틀린 문제는 없어" in summary


def test_wrong_answers_all_reviewed_summary(case2_student, make_chat_state):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    state = {**state, "has_wrong_answers": True, "wrong_content_done_today": True}

    summary = _build_wrong_answer_summary(state)

    assert "모두 복습했어" in summary
    assert "3" in summary


def test_wrong_answers_partially_reviewed_summary(case2_student, make_chat_state):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    state = {**state, "has_wrong_answers": True, "wrong_content_done_today": False}

    summary = _build_wrong_answer_summary(state)

    assert "3" in summary
    assert "2" in summary
    assert "아직 남아 있어" in summary


def test_response_shape(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    response = motivator(state)

    types = [message.type for message in response.messages]
    assert "text" in types


def test_wrong_summary_in_situation_partial(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    state = {**state, "wrong_content_done_today": False}
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    assert "아직 남아 있어" in prompt_text


def test_tp5_does_not_prompt_invented_review_exercises(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
        completed_tasks=[case2_student["today_tasks"][0]],
    )
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    banned_examples = ["7-3", "피자", "사과 3개"]

    assert "Book Club" in prompt_text
    assert "새 문제" in prompt_text
    assert "예시" in prompt_text
    assert "교과서 페이지" in prompt_text
    assert "퀴즈" in prompt_text
    for phrase in banned_examples:
        assert phrase not in prompt_text
