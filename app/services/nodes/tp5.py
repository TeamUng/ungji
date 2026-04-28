from __future__ import annotations

from app.core.enums import Segment
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_choices, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)

_TP5_CHOICES: dict[Segment, tuple[tuple[str, str], ...]] = {
    Segment.HIGH_DILIGENT: (
        ("preview_deeper", "다음 심화 미리 보기"),
        ("review_today", "오늘 핵심 정리하기"),
        ("finish_today", "학습 끝내기"),
    ),
    Segment.HIGH_LAZY: (
        ("set_short_goal", "다음 목표 짧게 정하기"),
        ("review_today", "오늘 한 것 확인하기"),
        ("finish_today", "학습 끝내기"),
    ),
    Segment.LOW_DILIGENT: (
        ("review_wrong", "오답 다시 보기"),
        ("review_today", "오늘 배운 것 정리하기"),
        ("finish_today", "학습 끝내기"),
    ),
    Segment.LOW_LAZY: (
        ("one_next_goal", "다음에 할 1개 정하기"),
        ("quick_review", "오늘 한 것 보기"),
        ("finish_today", "학습 끝내기"),
    ),
}


def _build_wrong_answer_summary(state: ChatState) -> str:
    if not state["has_wrong_answers"]:
        return "오늘 틀린 문제가 없어요!"

    total = state["learning_pattern"]["wrong_content_total"]
    done = state["learning_pattern"]["wrong_content_done"]

    if state["wrong_content_done_today"]:
        return f"오답 {total}개를 다 복습했어요!"

    remaining = total - done
    return f"오답 {total}개 중 {remaining}개가 남아있어요."


def tp5(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm
    from langchain_core.messages import HumanMessage, SystemMessage

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]

    system_prompt = f"{get_persona(grade_group)}\n\n{get_coaching_strategy(segment)}"

    wrong_summary = _build_wrong_answer_summary(state)

    user_message = (
        f"학생 이름: {profile['name']}\n"
        f"학년: {profile['grade']}학년\n"
        f"오늘 학습 결과: {wrong_summary}\n\n"
        "오늘 학습을 마무리하는 메시지를 전해주세요."
    )

    logger.info(
        "TP5 node invoked",
        extra={
            "student_id": state["student_id"],
            "segment": segment.value,
            "has_wrong_answers": state["has_wrong_answers"],
            "wrong_content_done_today": state["wrong_content_done_today"],
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    messages = [make_text(response.content), make_choices(_TP5_CHOICES[segment])]

    logger.info(
        "TP5 node completed",
        extra={"student_id": state["student_id"], "message_count": len(messages)},
    )

    return make_chat_response(state["thread_id"], messages)
