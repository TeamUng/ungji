from __future__ import annotations

from copy import deepcopy

import pytest

from app.core.enums import GradeGroup, MessageType, Segment, Touchpoint, UseCase
from app.services.decision_policy import (
    classify_message_event,
    make_helper_decision,
    make_motivator_decision,
    route_agent,
    should_check_latest_input,
)


def test_init_event_is_app_controlled_not_guarded():
    event = classify_message_event(MessageType.INIT, "")

    assert event.source == "app_event"
    assert not event.should_append_human_message
    assert not event.should_check_input_guard


def test_text_event_is_free_form_and_guarded():
    event = classify_message_event(MessageType.TEXT, " help me ")

    assert event.source == "student_text"
    assert event.content == "help me"
    assert event.should_append_human_message
    assert event.should_check_input_guard


def test_choice_event_is_context_not_free_form_text():
    event = classify_message_event(MessageType.CHOICE, "no_concept")

    assert event.source == "student_choice"
    assert event.should_append_human_message
    assert not event.should_check_input_guard


def test_state_message_type_controls_input_guard(make_chat_state, case1_student):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
    )
    state["current_message_type"] = MessageType.CHOICE

    assert not should_check_latest_input(state, "no_concept")

    state["current_message_type"] = MessageType.TEXT
    assert should_check_latest_input(state, "student typed text")


def test_explicit_event_guard_flag_prevents_guarding_old_history(
    make_chat_state, case1_student
):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
    )
    state["current_message_type"] = MessageType.TEXT
    state["current_message_requires_input_guard"] = False

    assert not should_check_latest_input(state, "old previous student text")


def test_route_policy_keeps_tp4_with_helper(make_chat_state, case1_student):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )

    assert route_agent(state) == "helper"


def test_route_policy_rejects_talk_tp4(make_chat_state, case1_student):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.TALK,
        touchpoint=Touchpoint.TP4,
    )

    with pytest.raises(ValueError):
        route_agent(state)


def test_motivator_policy_suggests_review_when_tasks_done(
    make_chat_state, case2_student
):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.TALK,
        touchpoint=Touchpoint.TP2,
        completed_tasks=[case2_student["today_tasks"][0]],
    )

    decision = make_motivator_decision(state)

    assert decision["intent"] == "suggest_review"


def test_motivator_policy_prioritizes_current_remaining_task(
    make_chat_state, case2_student
):
    student = deepcopy(case2_student)
    first_task = student["today_tasks"][0]
    next_task = {
        **first_task,
        "subject": "국어",
        "unit": "주장과 근거 파악하기",
        "problem_ids": ["upper_korean_argument_001"],
        "problem_id": "upper_korean_argument_001",
        "ai_predicted_score": 76,
    }
    student["today_tasks"] = [first_task, next_task]
    state = make_chat_state(
        student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.TALK,
        touchpoint=Touchpoint.TP2,
        completed_tasks=[first_task],
        current_task=next_task,
    )

    decision = make_motivator_decision(state)

    assert decision["intent"] == "recommend_next_task"
    assert decision["target_task"] == next_task
    assert decision["candidate_tasks"][0] == next_task


def test_helper_policy_first_known_problem_collects_cause(make_chat_state, case1_student):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )

    decision = make_helper_decision(
        state,
        {"problem_id": "p1"},
        last_content="p1",
        turn_count=0,
    )

    assert decision["intent"] == "collect_stuck_cause"
    assert decision["required_tool"] == "send_causes"
