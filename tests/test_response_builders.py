from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment, Touchpoint
from app.schemas.chat import ChoiceItem
from app.services.nodes.common import (
    build_placeholder_messages,
    get_response_policy,
    make_chat_response,
    make_choices,
    make_hint_card,
    make_image_card,
    make_text,
)


def test_response_builders_create_schema_messages():
    text = make_text("  같이 해볼까요?  ")
    choices = make_choices(
        [
            ("start_small", "작게 시작하기"),
            ChoiceItem(id="show_hint", label="힌트 보기"),
        ]
    )
    image_card = make_image_card("/assets/mock/story-scene.svg", "그림을 보고 생각해요")
    hint_card = make_hint_card(["조건을 찾기", "비교할 두 수 고르기"])
    response = make_chat_response(
        "thread-1",
        [text, choices, image_card, hint_card],
    )

    assert text.type == "text"
    assert text.content == "같이 해볼까요?"
    assert choices.type == "choices"
    assert [item.id for item in choices.items] == ["start_small", "show_hint"]
    assert image_card.type == "image_card"
    assert hint_card.steps[1].step == 2
    assert response.thread_id == "thread-1"
    assert len(response.messages) == 4


def test_choices_require_stable_snake_case_ids():
    with pytest.raises(ValueError, match="stable snake_case"):
        make_choices([("Start-Now", "바로 시작하기")])


def test_response_policy_selects_segment_touchpoint_shape():
    policy = get_response_policy(
        Segment.LOW_DILIGENT,
        GradeGroup.UPPER,
        Touchpoint.TP4,
    )

    assert policy.message_types == ("text", "choices", "hint_card")
    assert policy.max_choice_count == 4
    assert "단계별" in policy.goal


def test_placeholder_messages_do_not_expose_internal_segment_names():
    for segment in Segment:
        for touchpoint in Touchpoint:
            messages = build_placeholder_messages(
                segment,
                GradeGroup.MIDDLE,
                touchpoint,
            )
            student_facing_text = _collect_student_facing_text(messages)

            for internal_segment_label in [item.value for item in Segment]:
                assert internal_segment_label not in student_facing_text


def test_case_1_placeholder_uses_low_barrier_choices():
    messages = build_placeholder_messages(
        Segment.LOW_LAZY,
        GradeGroup.LOWER,
        Touchpoint.TP4,
    )

    assert [message.type for message in messages] == ["text", "choices"]
    assert messages[1].items[0].id == "too_long"
    assert len(messages[1].items) == 4
    assert "어려운 곳 하나만" in messages[0].content


def test_case_2_placeholder_uses_diagnostic_math_choices():
    messages = build_placeholder_messages(
        Segment.LOW_DILIGENT,
        GradeGroup.UPPER,
        Touchpoint.TP4,
    )

    assert [message.type for message in messages] == ["text", "choices"]
    assert [item.id for item in messages[1].items] == [
        "confused_concept",
        "find_compare_numbers",
        "build_expression",
        "check_calculation",
    ]
    assert "비율 뜻이 헷갈려요" in messages[1].items[0].label


def _collect_student_facing_text(messages):
    chunks = []
    for message in messages:
        if message.type == "text":
            chunks.append(message.content)
        elif message.type == "choices":
            chunks.extend(item.label for item in message.items)
        elif message.type == "image_card":
            chunks.append(message.caption)
        elif message.type == "hint_card":
            chunks.extend(step.content for step in message.steps)
    return "\n".join(chunks)
