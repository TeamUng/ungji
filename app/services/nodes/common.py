from __future__ import annotations

import re
from typing import Sequence

from app.core.logging import get_logger
from app.schemas.chat import (
    ChatResponse,
    ChoiceItem,
    ChoicesMessage,
    HintCardMessage,
    HintStep,
    ImageCardMessage,
    ResponseMessage,
    TextMessage,
)

logger = get_logger(__name__)

CHOICE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def make_text(content: str) -> TextMessage:
    content = _require_non_empty(content, "content")
    return TextMessage(content=content)


def make_choices(items: Sequence[tuple[str, str] | ChoiceItem]) -> ChoicesMessage:
    if not items:
        raise ValueError("choices must contain at least one item")

    choice_items = [
        item if isinstance(item, ChoiceItem) else _make_choice_item(*item)
        for item in items
    ]
    return ChoicesMessage(items=choice_items)


def make_image_card(image_url: str, caption: str) -> ImageCardMessage:
    image_url = _require_non_empty(image_url, "image_url")
    caption = _require_non_empty(caption, "caption")
    return ImageCardMessage(image_url=image_url, caption=caption)


def make_hint_card(steps: Sequence[str | HintStep]) -> HintCardMessage:
    if not steps:
        raise ValueError("hint steps must contain at least one item")

    hint_steps = [
        step if isinstance(step, HintStep) else HintStep(step=index, content=step)
        for index, step in enumerate(steps, start=1)
    ]
    return HintCardMessage(steps=hint_steps)


def make_chat_response(
    thread_id: str,
    messages: Sequence[ResponseMessage],
) -> ChatResponse:
    thread_id = _require_non_empty(thread_id, "thread_id")
    if not messages:
        raise ValueError("messages must contain at least one item")

    return ChatResponse(thread_id=thread_id, messages=list(messages))


def _make_choice_item(choice_id: str, label: str) -> ChoiceItem:
    choice_id = _require_non_empty(choice_id, "choice id")
    label = _require_non_empty(label, "choice label")

    if not CHOICE_ID_PATTERN.fullmatch(choice_id):
        raise ValueError(f"choice id must be stable snake_case: {choice_id}")

    return ChoiceItem(id=choice_id, label=label)


def _require_non_empty(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value
