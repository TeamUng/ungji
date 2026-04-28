from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


def tp2(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]

    completed_count = len(completed_tasks)
    total_count = len(today_tasks)
    remaining_tasks = [t for t in today_tasks if t not in completed_tasks]

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "당신은 스마트올 AI 학습 코치입니다. 학생이 방금 과제를 완료했습니다.\n"
        "다음을 해주세요:\n"
        "1. 학생의 노력을 진심으로 인정하고 격려하세요. 구체적으로 칭찬하세요.\n"
        "2. 남은 과제가 있으면 다음으로 할 과제를 하나 구체적으로 추천하세요.\n"
        "3. 모든 과제를 완료했다면 북클럽(독서 코너)으로 넘어가도록 안내하세요: "
        "'오늘 모든 학습을 마쳤어! 이제 북클럽에서 짧은 이야기 하나 읽어볼까?'\n"
        "4. 응답은 2~4문장으로 간결하게 작성하세요."
    )

    completed_subjects = [t["subject"] for t in completed_tasks]
    remaining_lines = [
        f"- {t['subject']}: {t['unit']} (난이도: {t['difficulty']})"
        for t in remaining_tasks
    ]

    if remaining_tasks:
        situation = (
            f"완료한 과제: {', '.join(completed_subjects)} ({completed_count}/{total_count}개 완료)\n"
            f"남은 과제:\n" + "\n".join(remaining_lines)
        )
    else:
        situation = f"모든 과제 완료! ({total_count}/{total_count}개)"

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"{situation}\n\n"
        "방금 과제를 완료했습니다. 격려하고 다음 행동을 안내해주세요."
    )

    logger.info(
        "TP2 node invoked",
        extra={
            "student_id": state["student_id"],
            "completed_count": completed_count,
            "total_count": total_count,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    logger.info("TP2 node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])
