from __future__ import annotations

import pytest

from app.schemas.chat import ChoiceItem
from app.services.nodes.common import (
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
