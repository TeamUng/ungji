from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


def general_chat(state: ChatState) -> ChatResponse:
    """자유 대화 노드 — 학생이 자유롭게 메시지를 보낼 때 사용."""
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    chat_history = state.get("chat_history", [])

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "당신은 스마트올 AI 학습 코치입니다. 학생과 자유롭게 대화하세요.\n"
        "학생의 말에 공감하며 자연스럽게 응답하세요.\n"
        "학습 관련 이야기가 나오면 자연스럽게 연결하고, "
        "대화 흐름에서 학습으로 돌아올 기회가 생기면 부드럽게 유도하세요.\n"
        "강요하지 말고, 학생이 편하게 느낄 수 있도록 하세요.\n"
        "응답은 1~3문장으로 간결하게 작성하세요."
    )

    # 최근 대화 히스토리 포함 (최대 10턴)
    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    messages = [SystemMessage(content=system_prompt)] + list(recent_history)

    logger.info(
        "general_chat 노드 호출",
        extra={
            "student_id": state["student_id"],
            "history_length": len(chat_history),
        },
    )

    response = llm.invoke(messages)

    logger.info("general_chat 노드 완료", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])
