from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


def tp3(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    current_task = state.get("current_task")

    completed_count = len(completed_tasks)
    total_count = len(today_tasks)
    all_done = completed_count >= total_count

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "당신은 스마트올 AI 학습 코치입니다. 학생이 앱을 나가려 하고 있습니다.\n"
        "다음 원칙으로 대응하세요:\n"
        "1. 모든 과제를 완료한 경우: 수고했다고 격려하고 편하게 보내주세요.\n"
        "2. 과제가 남은 경우: 학생의 마음을 이해하면서 부드럽게 붙잡으세요. "
        "강요하지 말고, 아주 작은 것 하나만 더 하자고 제안하세요.\n"
        "   - 지금 하던 과제가 너무 어려우면 더 쉬운 과제를 추천하세요.\n"
        "   - 피곤하거나 쉬고 싶으면 '잠깐 게임 코너에서 쉬고 오는 건 어때?'처럼 "
        "앱 안에서 쉬도록 유도할 수 있어요.\n"
        "3. 대화를 자연스럽게 이어가며 학생의 상태를 파악하세요.\n"
        "4. 응답은 2~3문장으로 간결하게 작성하세요."
    )

    remaining_tasks = [t for t in today_tasks if t not in completed_tasks]
    remaining_lines = [
        f"- {t['subject']}: {t['unit']} (난이도: {t['difficulty']})"
        for t in remaining_tasks
    ]

    current_line = ""
    if current_task:
        current_line = f"\n현재 진행 중인 과제: {current_task['subject']} - {current_task['unit']}"

    if all_done:
        situation = "모든 과제를 완료했습니다."
    else:
        situation = (
            f"진행 상황: {completed_count}/{total_count}개 완료\n"
            f"남은 과제:\n" + "\n".join(remaining_lines)
        )

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)"
        f"{current_line}\n"
        f"{situation}\n\n"
        "학생이 앱을 나가려 합니다. 상황에 맞게 대응해주세요."
    )

    logger.info(
        "TP3 node invoked",
        extra={
            "student_id": state["student_id"],
            "completed_count": completed_count,
            "total_count": total_count,
            "all_done": all_done,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    logger.info("TP3 node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])
