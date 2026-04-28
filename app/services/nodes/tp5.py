from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


def _build_wrong_answer_summary(state: ChatState) -> str:
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]
    wrong_total = pattern.get("wrong_content_total", 0)
    wrong_done = pattern.get("wrong_content_done", 0)

    if not has_wrong:
        return "오늘 틀린 문제가 없어요!"
    if wrong_done_today:
        return f"오늘 오답 {wrong_total}개를 다 복습했어요."
    remaining = wrong_total - wrong_done
    return f"오답 {wrong_total}개 중 {remaining}개가 남아있어요."


def tp5(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "당신은 스마트올 AI 학습 코치입니다. 학생의 오늘 학습 세션이 끝났습니다.\n"
        "다음을 해주세요:\n"
        "1. 오늘 학습을 진심으로 격려하세요.\n"
        "2. 오답이 있고 아직 복습하지 않았다면, 다음 학습 전에 복습하도록 부드럽게 권유하세요. "
        "강요하지 말고 선택권을 주세요.\n"
        "3. 오답이 없거나 이미 복습했다면 잘했다고 크게 칭찬하세요.\n"
        "4. 다음 학습도 기대되도록 마무리하세요.\n"
        "5. 응답은 3~5문장으로 작성하세요."
    )

    completed_subjects = [t["subject"] for t in completed_tasks]
    wrong_summary = _build_wrong_answer_summary(state)

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"오늘 완료한 과제: {', '.join(completed_subjects) if completed_subjects else '없음'} "
        f"({len(completed_tasks)}/{len(today_tasks)}개)\n"
        f"오답 현황: {wrong_summary}\n"
        f"오늘 평균 점수: {state['today_score']}점\n\n"
        "오늘 학습을 마무리해주세요."
    )

    logger.info(
        "TP5 node invoked",
        extra={
            "student_id": state["student_id"],
            "has_wrong_answers": has_wrong,
            "wrong_content_done_today": wrong_done_today,
        },
    )

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

    logger.info("TP5 node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])
