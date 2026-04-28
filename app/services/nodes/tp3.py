from __future__ import annotations

from app.core.enums import Segment
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_choices, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)

_TP3_CHOICES: dict[Segment, tuple[tuple[str, str], ...]] = {
    Segment.HIGH_DILIGENT: (
        ("finish_current", "지금 문제 마무리하기"),
        ("check_condition", "조건 하나만 확인하기"),
        ("pause_after_this", "이 문제 후 쉬기"),
    ),
    Segment.HIGH_LAZY: (
        ("finish_one", "딱 1문제만 끝내기"),
        ("quick_hint", "힌트만 보고 풀기"),
        ("pause_after_this", "이 문제 후 쉬기"),
    ),
    Segment.LOW_DILIGENT: (
        ("one_small_step", "한 단계만 같이 보기"),
        ("show_hint", "힌트 보기"),
        ("pause_after_this", "이 문제 후 쉬기"),
    ),
    Segment.LOW_LAZY: (
        ("one_tiny_step", "아주 작은 단계만 하기"),
        ("easy_hint", "쉬운 힌트 보기"),
        ("pause_after_this", "이 문제 후 쉬기"),
    ),
}


def tp3(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm
    from langchain_core.messages import HumanMessage, SystemMessage

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    current_task = state["current_task"]

    system_prompt = f"{get_persona(grade_group)}\n\n{get_coaching_strategy(segment)}"

    task_info = ""
    if current_task:
        task_info = (
            f"지금 하던 학습: {current_task['subject']} - {current_task['unit']} "
            f"({current_task['problem_count']}문제)"
        )

    user_message = (
        f"학생 이름: {profile['name']}\n"
        f"학년: {profile['grade']}학년\n"
        f"{task_info}\n\n"
        "학생이 학습을 중간에 나가려고 합니다. "
        "'이 문제만 끝내고 가자'는 방향으로 남은 양을 최소화해서 짧게 설득해주세요."
    )

    logger.info(
        "TP3 node invoked",
        extra={
            "student_id": state["student_id"],
            "segment": segment.value,
            "current_task": current_task,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    messages = [make_text(response.content), make_choices(_TP3_CHOICES[segment])]

    logger.info(
        "TP3 node completed",
        extra={"student_id": state["student_id"], "message_count": len(messages)},
    )

    return make_chat_response(state["thread_id"], messages)
