from __future__ import annotations

from app.core.enums import Segment
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_choices, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)

_TP2_CHOICES: dict[Segment, tuple[tuple[str, str], ...]] = {
    Segment.HIGH_DILIGENT: (
        ("try_deeper", "심화 문제로 이어가기"),
        ("review_key", "핵심만 빠르게 확인하기"),
        ("finish_today", "오늘 학습 정리하기"),
    ),
    Segment.HIGH_LAZY: (
        ("one_more_challenge", "도전 문제 1개만 더 풀기"),
        ("short_review", "핵심만 1분 복습하기"),
        ("finish_today", "오늘은 여기까지 하기"),
    ),
    Segment.LOW_DILIGENT: (
        ("next_small_step", "다음 단계 같이 보기"),
        ("review_mistake", "헷갈린 부분 다시 보기"),
        ("finish_today", "오늘 학습 정리하기"),
    ),
    Segment.LOW_LAZY: (
        ("one_more_easy", "쉬운 문제 1개만 더 하기"),
        ("quick_praise", "오늘 한 것 확인하기"),
        ("finish_today", "오늘은 여기까지 하기"),
    ),
}


def tp2(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm
    from langchain_core.messages import HumanMessage, SystemMessage

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    completed = state["completed_tasks"]
    today_tasks = state["today_tasks"]

    system_prompt = f"{get_persona(grade_group)}\n\n{get_coaching_strategy(segment)}"

    completed_count = len(completed)
    total_count = len(today_tasks)
    remaining = total_count - completed_count

    user_message = (
        f"학생 이름: {profile['name']}\n"
        f"학년: {profile['grade']}학년\n"
        f"오늘 학습 진행률: {completed_count}/{total_count} 완료, {remaining}개 남음\n\n"
        "방금 한 단위 학습을 완료했습니다. 완료를 축하하고 다음 학습을 부드럽게 제안해주세요."
    )

    logger.info(
        "TP2 node invoked",
        extra={
            "student_id": state["student_id"],
            "segment": segment.value,
            "completed": completed_count,
            "total": total_count,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    messages = [make_text(response.content), make_choices(_TP2_CHOICES[segment])]

    logger.info(
        "TP2 node completed",
        extra={"student_id": state["student_id"], "message_count": len(messages)},
    )

    return make_chat_response(state["thread_id"], messages)
