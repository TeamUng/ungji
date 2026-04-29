from __future__ import annotations

from langchain_core.messages import SystemMessage

from app.core.enums import Touchpoint
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.agents import MOTIVATOR_ROLE, build_system_prompt

logger = get_logger(__name__)

_HISTORY_WINDOW = 20


def motivator(state: ChatState) -> ChatResponse:
    """Handle TP1, TP2, TP3, TP5, and non-TP4 free chat turns."""
    from app.clients.upstage import llm

    grade_group = state["grade_group"]
    segment = state["segment"]
    touchpoint = state["current_touchpoint"]
    chat_history = state.get("chat_history", [])

    system_prompt = build_system_prompt(grade_group, segment, MOTIVATOR_ROLE)
    situation = _get_situation(state)
    recent = chat_history[-_HISTORY_WINDOW:] if len(chat_history) > _HISTORY_WINDOW else chat_history

    messages = [SystemMessage(content=system_prompt)]
    messages += list(recent)
    if situation:
        messages.append(SystemMessage(content=f"[현재 상황]\n{situation}"))

    logger.info(
        "motivator node invoked",
        extra={
            "student_id": state["student_id"],
            "touchpoint": touchpoint.value if touchpoint else "chat",
            "segment": segment.value,
        },
    )

    response = llm.invoke(messages)

    logger.info("motivator node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])


def _get_situation(state: ChatState) -> str:
    touchpoint = state.get("current_touchpoint")

    if touchpoint == Touchpoint.TP1:
        return _situation_tp1(state)
    if touchpoint == Touchpoint.TP2:
        return _situation_tp2(state)
    if touchpoint == Touchpoint.TP3:
        return _situation_tp3(state)
    if touchpoint == Touchpoint.TP5:
        return _situation_tp5(state)
    return ""


def _situation_tp1(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    pattern = state["learning_pattern"]

    task_lines = []
    for index, task in enumerate(today_tasks, 1):
        score_info = (
            f", AI 예상점수 {task['ai_predicted_score']}점"
            if task.get("ai_predicted_score")
            else ""
        )
        task_lines.append(
            f"{index}. {task['subject']} - {task['unit']} "
            f"(난이도 {task['difficulty']}, {task['problem_count']}문제, "
            f"{task['estimated_time']}분{score_info})"
        )

    habits = [
        label
        for label, enabled in {
            "건너뛰는 습관": pattern.get("skipping_habit"),
            "찍는 습관": pattern.get("guessing_habit"),
            "대충 푸는 습관": pattern.get("careless_habit"),
        }.items()
        if enabled
    ]

    habit_line = f"학습 습관: {', '.join(habits)}\n" if habits else ""
    tasks = "\n".join(task_lines) if task_lines else "오늘 홈화면에 표시할 단원이 없습니다."

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)이 홈화면에 진입했습니다.\n"
        f"최근 평균 점수: {profile['recent_avg_score']}점 / "
        f"선호 과목: {profile['preferred_subject']} / 강한 과목: {profile['strong_subject']}\n"
        f"{habit_line}"
        "학생 홈화면에는 아래 4개 단원 카드가 보입니다.\n"
        f"{tasks}\n\n"
        "이 4개 중 지금 시작하기 가장 좋은 단원 하나를 골라 추천하세요. "
        "학생에게 4개 전체를 다시 선택지처럼 나열하지 말고, 추천 단원 하나와 이유를 짧게 말하세요. "
        "단원 내용을 가르치거나 새 문제를 내지 마세요."
    )


def _situation_tp2(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = [task for task in today_tasks if task not in completed_tasks]

    completed_str = ", ".join(task["subject"] for task in completed_tasks) or "없음"
    remaining_lines = [
        f"- {task['subject']}: {task['unit']} (난이도 {task['difficulty']})"
        for task in remaining
    ]

    if remaining:
        situation = (
            f"완료: {completed_str} ({len(completed_tasks)}/{len(today_tasks)}개)\n"
            f"남은 과제:\n" + "\n".join(remaining_lines) + "\n\n"
            "방금 과제를 완료한 학생을 격려하고, 다음으로 할 과제 하나를 추천하세요. "
            "여러 선택지를 주지 말고 하나를 분명히 찍어주세요. "
            "단원 내용을 설명하거나 새 과제를 만들지 마세요."
        )
    else:
        situation = (
            f"모든 과제 완료! ({len(today_tasks)}/{len(today_tasks)}개)\n\n"
            "모든 과제를 마친 학생에게 짧게 칭찬하고 북클럽 코너로 안내하세요. "
            "새 학습 과제나 복습 문제를 만들지 마세요."
        )

    return f"학생: {profile['name']} ({profile['grade']}학년)\n{situation}"


def _situation_tp3(state: ChatState) -> str:
    profile = state["student_profile"]
    current_task = state.get("current_task")
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining_count = max(len(today_tasks) - len(completed_tasks), 0)

    task_info = ""
    if current_task:
        task_info = f"현재 과제: {current_task['subject']} - {current_task['unit']}\n"

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)이 학습 중에 이탈하려 합니다.\n"
        f"{task_info}"
        f"남은 과제: {remaining_count}개\n\n"
        "강요하지 말고 공감하며, 쉽고 돌아오기 좋은 작은 행동 하나를 제안하세요. "
        "응답은 2~3문장으로 작성하세요. "
        "여러 선택지를 주지 말고, 지금 할 수 있는 아주 작은 행동 하나를 추천하세요. "
        "수업 내용을 설명하거나 새 문제를 내지 마세요."
    )


def _situation_tp5(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    wrong_summary = _build_wrong_answer_summary(state)
    completed_str = ", ".join(task["subject"] for task in completed_tasks) or "없음"

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)이 오늘 학습을 끝내려 합니다.\n"
        f"완료한 과제: {completed_str} ({len(completed_tasks)}/{len(today_tasks)}개)\n"
        f"오답 현황: {wrong_summary}\n"
        f"오늘 평균 점수: {state['today_score']}점\n\n"
        "오늘 학습을 진심으로 마무리해주세요. "
        "TP1처럼 새 단원을 시작시키지 마세요. "
        "오답이 남아 있다면 부드럽게 다음에 이어서 복습하자고 말하고, 없으면 짧게 칭찬하세요. "
        "새 문제나 새 과제를 만들지 마세요."
    )


def _build_wrong_answer_summary(state: ChatState) -> str:
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]
    wrong_total = pattern.get("wrong_content_total", 0)
    wrong_done = pattern.get("wrong_content_done", 0)

    if not has_wrong:
        return "오늘 틀린 문제가 없어요."
    if wrong_done_today:
        return f"오늘 오답 {wrong_total}개를 다 복습했어요."
    remaining = max(wrong_total - wrong_done, 0)
    return f"오답 {wrong_total}개 중 {remaining}개가 남아 있어요."
