from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
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

    assert "없어요" in summary


def test_wrong_answers_all_reviewed_summary(case2_student, make_chat_state):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        touchpoint=Touchpoint.TP5,
    )
    state = {**state, "has_wrong_answers": True, "wrong_content_done_today": True}

    summary = _build_wrong_answer_summary(state)

    assert "다 복습했어요" in summary
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
    assert "남아 있어요" in summary


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
    assert "남아 있어요" in prompt_text


def test_chat_followup_keeps_tp5_situation(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.CHAT,
        touchpoint=Touchpoint.TP5,
    )
    motivator(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    assert "오늘 학습을 끝내려 합니다" in prompt_text
    assert "TP1처럼 새 단원을 시작시키지 마세요" in prompt_text
