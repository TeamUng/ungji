from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import Segment
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_choices, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)

_TP1_CHOICES: dict[Segment, tuple[tuple[str, str], ...]] = {
    Segment.HIGH_DILIGENT: (
        ("deep_challenge", "오늘의 심화 문제 도전하기"),
        ("real_life_problem", "실생활 적용 문제 풀기"),
        ("check_weak_unit", "내가 약한 단원 확인하기"),
    ),
    Segment.HIGH_LAZY: (
        ("five_min_challenge", "5분만 도전 문제 풀기"),
        ("pick_today_task", "오늘 할 것 골라주기"),
        ("continue_yesterday", "어제 하던 학습 이어하기"),
    ),
    Segment.LOW_DILIGENT: (
        ("easy_explanation", "쉬운 설명으로 다시 배우기"),
        ("step_by_step", "한 문제를 단계별로 같이 풀기"),
        ("find_stuck_point", "어디서 막혔는지 확인하기"),
    ),
    Segment.LOW_LAZY: (
        ("one_min_reading", "1분만 짧은 글 읽어보기"),
        ("one_easy_problem", "아주 쉬운 문제 1개만 풀기"),
        ("picture_first", "그림 보고 먼저 보기"),
    ),
}


def tp1(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]

    system_prompt = f"{get_persona(grade_group)}\n\n{get_coaching_strategy(segment)}"

    task_lines = ""
    if today_tasks:
        task = today_tasks[0]
        task_lines = (
            f"오늘 학습: {task['subject']} - {task['unit']} "
            f"(예상 {task['estimated_time']}분, AI 예상점수 {task['ai_predicted_score']}점)"
        )

    user_message = (
        f"학생 이름: {profile['name']}\n"
        f"학년: {profile['grade']}학년\n"
        f"선호 과목: {profile['preferred_subject']}\n"
        f"{task_lines}\n\n"
        "지금 홈화면에 진입했습니다. 학생에게 오늘 학습을 시작하도록 안내해주세요."
    )

    logger.info(
        "TP1 node invoked",
        extra={
            "student_id": state["student_id"],
            "segment": segment.value,
            "grade_group": grade_group.value,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    messages = [make_text(response.content), make_choices(_TP1_CHOICES[segment])]

    logger.info(
        "TP1 node completed",
        extra={"student_id": state["student_id"], "message_count": len(messages)},
    )

    return make_chat_response(state["thread_id"], messages)
