from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


def tp1(state: ChatState) -> ChatResponse:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    pattern = state["learning_pattern"]

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "당신은 스마트올 AI 학습 코치입니다. 학생이 홈 화면에 접속했습니다.\n"
        "다음을 해주세요:\n"
        "1. 학생에게 친근하게 인사하세요. 학생이 먼저 대화를 걸어오면 자연스럽게 응하되, "
        "결국 학습으로 부드럽게 안내하세요.\n"
        "2. 오늘의 4가지 과제 중 이 학생에게 가장 적합한 과제 하나를 구체적으로 추천하세요. "
        "난이도, AI 예상 점수, 선호 과목, 학습 패턴(건너뜀/찍기 등)을 종합적으로 고려하세요.\n"
        "3. 추천 이유를 학생의 눈높이에 맞게 짧게 설명하세요.\n"
        "4. 응답은 2~4문장으로 간결하게 작성하세요."
    )

    task_lines = []
    for i, task in enumerate(today_tasks, 1):
        score_info = f" / AI 예상점수 {task['ai_predicted_score']}점" if task.get("ai_predicted_score") else ""
        task_lines.append(
            f"{i}. {task['subject']} - {task['unit']} "
            f"(난이도: {task['difficulty']}{score_info})"
        )

    habits = []
    if pattern.get("skipping_habit"):
        habits.append("건너뛰는 습관 있음")
    if pattern.get("guessing_habit"):
        habits.append("찍는 습관 있음")
    if pattern.get("careless_habit"):
        habits.append("대충 푸는 습관 있음")
    habit_line = f"\n학습 습관: {', '.join(habits)}" if habits else ""

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"최근 평균 점수: {profile['recent_avg_score']}점\n"
        f"선호 과목: {profile['preferred_subject']}, 잘하는 과목: {profile['strong_subject']}"
        f"{habit_line}\n\n"
        f"오늘의 과제:\n" + "\n".join(task_lines) + "\n\n"
        "학생이 홈화면에 진입했습니다. 인사하고 오늘 첫 번째 과제를 추천해주세요."
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

    messages = [make_text(response.content)]

    logger.info(
        "TP1 node completed",
        extra={"student_id": state["student_id"]},
    )

    return make_chat_response(state["thread_id"], messages)
