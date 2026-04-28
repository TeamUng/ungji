from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from app.core.enums import GradeGroup, Segment, Touchpoint
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


@dataclass(frozen=True)
class ResponsePolicy:
    """Student-facing response shape selected before final wording is generated."""

    segment: Segment
    grade_group: GradeGroup
    touchpoint: Touchpoint
    goal: str
    message_types: tuple[str, ...]
    max_choice_count: int


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


def get_response_policy(
    segment: Segment,
    grade_group: GradeGroup,
    touchpoint: Touchpoint,
) -> ResponsePolicy:
    policy = _POLICY_MAP[(segment, touchpoint)]

    logger.debug(
        "Selected response policy",
        extra={
            "segment": segment.value,
            "grade_group": grade_group.value,
            "touchpoint": touchpoint.value,
        },
    )

    return ResponsePolicy(
        segment=segment,
        grade_group=grade_group,
        touchpoint=touchpoint,
        goal=policy.goal,
        message_types=policy.message_types,
        max_choice_count=_choice_count_for_grade(grade_group, policy.max_choice_count),
    )


def build_placeholder_messages(
    segment: Segment,
    grade_group: GradeGroup,
    touchpoint: Touchpoint,
) -> list[ResponseMessage]:
    policy = get_response_policy(segment, grade_group, touchpoint)
    text, choices = _PLACEHOLDER_COPY[(segment, touchpoint)]

    selected_choices = choices[: policy.max_choice_count]
    messages: list[ResponseMessage] = [make_text(text), make_choices(selected_choices)]

    logger.debug(
        "Built placeholder response messages",
        extra={
            "message_count": len(messages),
            "segment": segment.value,
            "grade_group": grade_group.value,
            "touchpoint": touchpoint.value,
        },
    )

    return messages


@dataclass(frozen=True)
class _PolicyTemplate:
    goal: str
    message_types: tuple[str, ...]
    max_choice_count: int


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


def _choice_count_for_grade(grade_group: GradeGroup, default_count: int) -> int:
    return default_count


def _policy(
    goal: str,
    message_types: Iterable[str],
    max_choice_count: int = 3,
) -> _PolicyTemplate:
    return _PolicyTemplate(
        goal=goal,
        message_types=tuple(message_types),
        max_choice_count=max_choice_count,
    )


_POLICY_MAP: dict[tuple[Segment, Touchpoint], _PolicyTemplate] = {
    (Segment.HIGH_DILIGENT, Touchpoint.TP1): _policy(
        "잘 이어온 흐름을 인정하고 심화 학습으로 연결한다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP1): _policy(
        "짧고 명확한 도전으로 학습 시작점을 낮춘다.",
        ("text", "choices"),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP1): _policy(
        "실패감을 줄이고 개념 보정 학습으로 안내한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP1): _policy(
        "초소형 목표로 시작 장벽을 낮춘다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP2): _policy(
        "완료 성취를 인정하고 다음 심화 활동을 제안한다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP2): _policy(
        "완료 경험을 짧은 루틴으로 이어가게 한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP2): _policy(
        "노력을 인정하고 다음 한 단계를 부담 없이 제안한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP2): _policy(
        "완료 자체를 크게 강화하고 작은 다음 행동만 남긴다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP3): _policy(
        "남은 학습의 의미를 짧게 알려 지속을 돕는다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP3): _policy(
        "딱 하나의 도전으로 이탈을 줄인다.",
        ("text", "choices"),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP3): _policy(
        "힘든 지점을 인정하고 단계를 낮춰 다시 시작하게 한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP3): _policy(
        "남은 양을 최소화해 한 번 더 붙잡는다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP4): _policy(
        "핵심 단서를 확인한 뒤 심화 사고로 확장한다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP4): _policy(
        "핵심 조건만 빠르게 잡고 도전 흐름을 유지한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP4): _policy(
        "막힘 원인을 진단하고 단계별 힌트로 이해를 돕는다.",
        ("text", "choices", "hint_card"),
        max_choice_count=4,
    ),
    (Segment.LOW_LAZY, Touchpoint.TP4): _policy(
        "쉬운 원인 선택지와 짧은 설명으로 한 문제만 유도한다.",
        ("text", "choices", "image_card"),
        max_choice_count=4,
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP5): _policy(
        "오늘의 성취를 요약하고 다음 심화를 예고한다.",
        ("text", "choices"),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP5): _policy(
        "짧게 끝낸 성취를 다음 루틴으로 연결한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP5): _policy(
        "노력을 인정하고 오답 복습을 부드럽게 안내한다.",
        ("text", "choices"),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP5): _policy(
        "학습 종료 부담을 낮추고 다음 시작을 가볍게 만든다.",
        ("text", "choices"),
    ),
}

_PLACEHOLDER_COPY: dict[tuple[Segment, Touchpoint], tuple[str, tuple[tuple[str, str], ...]]] = {
    (Segment.HIGH_DILIGENT, Touchpoint.TP1): (
        "오늘도 잘 이어가고 있어요. 한 단계 더 생각해보는 학습으로 시작해볼까요?",
        (
            ("deep_challenge", "오늘의 심화 문제 도전하기"),
            ("real_life_problem", "실생활 적용 문제 풀기"),
            ("check_weak_unit", "내가 약한 단원 확인하기"),
        ),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP1): (
        "길게 하지 않아도 괜찮아요. 먼저 5분만 가볍게 시작해볼까요?",
        (
            ("five_min_challenge", "5분만 도전 문제 풀기"),
            ("pick_today_task", "오늘 할 것 골라주기"),
            ("continue_yesterday", "어제 하던 학습 이어하기"),
        ),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP1): (
        "괜찮아요. 오늘은 헷갈린 부분을 작게 나눠서 같이 볼게요.",
        (
            ("easy_explanation", "쉬운 설명으로 다시 배우기"),
            ("step_by_step", "한 문제를 단계별로 같이 풀기"),
            ("find_stuck_point", "어디서 막혔는지 확인하기"),
        ),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP1): (
        "좋아! 딱 하나만 아주 가볍게 시작해보자.",
        (
            ("one_min_reading", "1분만 짧은 글 읽어보기"),
            ("one_easy_problem", "아주 쉬운 문제 1개만 풀기"),
            ("picture_first", "그림 보고 먼저 보기"),
        ),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP2): (
        "좋아요. 방금 흐름이 아주 안정적이었어요. 다음은 조금 더 생각해볼 수 있어요.",
        (
            ("try_deeper", "심화 문제로 이어가기"),
            ("review_key", "핵심만 빠르게 확인하기"),
            ("finish_today", "오늘 학습 정리하기"),
        ),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP2): (
        "좋아요. 하나 끝냈으니 흐름이 생겼어요. 아주 짧게 하나만 더 이어갈까요?",
        (
            ("one_more_challenge", "도전 문제 1개만 더 풀기"),
            ("short_review", "핵심만 1분 복습하기"),
            ("finish_today", "오늘은 여기까지 하기"),
        ),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP2): (
        "끝까지 해낸 게 좋아요. 다음도 작게 나누면 충분히 따라갈 수 있어요.",
        (
            ("next_small_step", "다음 단계 같이 보기"),
            ("review_mistake", "헷갈린 부분 다시 보기"),
            ("finish_today", "오늘 학습 정리하기"),
        ),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP2): (
        "좋아! 하나 끝낸 것만으로도 오늘 시작은 성공이야.",
        (
            ("one_more_easy", "쉬운 문제 1개만 더 하기"),
            ("quick_praise", "오늘 한 것 확인하기"),
            ("finish_today", "오늘은 여기까지 하기"),
        ),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP3): (
        "거의 흐름을 잡았어요. 마무리 한 번만 하면 오늘 학습이 더 단단해져요.",
        (
            ("finish_current", "지금 문제 마무리하기"),
            ("check_condition", "조건 하나만 확인하기"),
            ("pause_after_this", "이 문제 후 쉬기"),
        ),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP3): (
        "지금 나가도 되지만, 딱 하나만 끝내면 훨씬 깔끔해요.",
        (
            ("finish_one", "딱 1문제만 끝내기"),
            ("quick_hint", "힌트만 보고 풀기"),
            ("pause_after_this", "이 문제 후 쉬기"),
        ),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP3): (
        "어려우면 잠깐 멈춰도 괜찮아요. 대신 한 단계만 같이 확인해볼까요?",
        (
            ("one_small_step", "한 단계만 같이 보기"),
            ("show_hint", "힌트 보기"),
            ("pause_after_this", "이 문제 후 쉬기"),
        ),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP3): (
        "좋아, 많이 하지 말고 딱 여기까지만 해보자.",
        (
            ("one_tiny_step", "아주 작은 단계만 하기"),
            ("easy_hint", "쉬운 힌트 보기"),
            ("pause_after_this", "이 문제 후 쉬기"),
        ),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP4): (
        "좋아요. 지금은 답보다 조건을 더 정확히 보는 게 중요해요.",
        (
            ("check_condition", "조건 다시 확인하기"),
            ("compare_choices", "선택지 차이 비교하기"),
            ("try_deeper", "조금 더 어려운 생각 해보기"),
        ),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP4): (
        "핵심만 빠르게 잡아볼게요. 어디부터 확인하면 좋을까요?",
        (
            ("key_condition", "핵심 조건만 보기"),
            ("fast_hint", "빠른 힌트 보기"),
            ("try_one_more", "바로 한 번 풀어보기"),
        ),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP4): (
        "괜찮아요. 어디에서 헷갈렸는지 먼저 나눠서 보면 풀 수 있어요.",
        (
            ("confused_concept", "비율 뜻이 헷갈려요"),
            ("find_compare_numbers", "어떤 수끼리 비교할지 모르겠어요"),
            ("build_expression", "식을 어떻게 세우는지 모르겠어요"),
            ("check_calculation", "계산하다가 틀렸어요"),
        ),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP4): (
        "괜찮아! 어려운 곳 하나만 골라줘. 내가 짧게 도와줄게.",
        (
            ("too_long", "글이 너무 길어"),
            ("dont_get_situation", "무슨 상황인지 모르겠어"),
            ("dont_get_feeling", "주인공 마음을 모르겠어"),
            ("dont_want_now", "그냥 하기 싫어"),
        ),
    ),
    (Segment.HIGH_DILIGENT, Touchpoint.TP5): (
        "오늘 학습 흐름이 좋아요. 다음에는 한 단계 더 깊게 생각해볼 수 있어요.",
        (
            ("preview_deeper", "다음 심화 미리 보기"),
            ("review_today", "오늘 핵심 정리하기"),
            ("finish_today", "학습 끝내기"),
        ),
    ),
    (Segment.HIGH_LAZY, Touchpoint.TP5): (
        "오늘 짧게라도 끝낸 흐름이 중요해요. 다음에도 이렇게 가볍게 시작해봐요.",
        (
            ("set_short_goal", "다음 목표 짧게 정하기"),
            ("review_today", "오늘 한 것 확인하기"),
            ("finish_today", "학습 끝내기"),
        ),
    ),
    (Segment.LOW_DILIGENT, Touchpoint.TP5): (
        "오늘 애쓴 부분이 보여요. 틀린 문제도 작게 나누면 다시 볼 수 있어요.",
        (
            ("review_wrong", "오답 다시 보기"),
            ("review_today", "오늘 배운 것 정리하기"),
            ("finish_today", "학습 끝내기"),
        ),
    ),
    (Segment.LOW_LAZY, Touchpoint.TP5): (
        "오늘 시작한 것만으로도 좋아. 다음에도 아주 작게 시작하면 돼.",
        (
            ("one_next_goal", "다음에 할 1개 정하기"),
            ("quick_review", "오늘 한 것 보기"),
            ("finish_today", "학습 끝내기"),
        ),
    ),
}
