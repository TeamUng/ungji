from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import Touchpoint, UseCase
from app.core.logging import get_logger
from app.guardrails.agent_output import check_agent_input_sync, guarded_invoke
from app.schemas.chat import ChatResponse, ChatState, Task
from app.services.decision_policy import (
    make_motivator_decision as _make_motivator_decision,
    remaining_tasks,
    should_check_latest_input,
)
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.agents import MOTIVATOR_ROLE, build_system_prompt

logger = get_logger(__name__)

_HISTORY_WINDOW = 20


def _task_lines(tasks: list[Task] | list[dict]) -> str:
    if not tasks:
        return "없어."

    lines: list[str] = []
    for index, task in enumerate(tasks, 1):
        score_info = (
            f", 예상 점수 {task['ai_predicted_score']}점"
            if task.get("ai_predicted_score") is not None
            else ""
        )
        lines.append(
            f"{index}. {task.get('subject', '')} - {task.get('unit', '')} "
            f"(난이도 {task.get('difficulty', '')}, {task.get('problem_count', '')}문제, "
            f"{task.get('estimated_time', '')}분{score_info})"
        )
    return "\n".join(lines)


def _decision_lines(decision: dict) -> str:
    target_task = decision.get("target_task")
    candidate_tasks = [task for task in decision.get("candidate_tasks", []) if task]
    target_line = _task_lines([target_task]) if target_task else "없어."
    candidate_line = _task_lines(candidate_tasks)
    forbidden = ", ".join(decision.get("forbidden", [])) or "없어."

    return (
        "시스템이 먼저 확정한 motivator decision:\n"
        f"- intent: {decision['intent']}\n"
        f"- student_goal: {decision['student_goal']}\n"
        f"- target_task:\n{target_line}\n"
        f"- candidate_tasks:\n{candidate_line}\n"
        f"- forbidden: {forbidden}\n\n"
        "위 decision의 범위를 벗어나지 말고, 아이에게 그대로 보일 최종 문장만 작성해줘. "
        "target_task가 있으면 반드시 target_task 단원 하나만 추천해줘. "
        "forbidden에 적힌 행동은 제안하지 말고, "
        "intent, target_task, candidate_tasks, forbidden 같은 내부 필드명은 절대 말하지 마."
    )


def _latest_student_message(chat_history) -> str:
    for message in reversed(chat_history):
        if message.__class__.__name__ == "HumanMessage":
            content = getattr(message, "content", "")
            if content:
                return str(content)
    return ""


def _student_call_name(name: str) -> str:
    if not name:
        return "친구야"
    last = name[-1]
    code = ord(last) - 0xAC00
    if 0 <= code <= 11171 and code % 28:
        return f"{name}아"
    return f"{name}야"


def _request_context_lines(state: ChatState) -> str:
    context = state.get("request_context")
    if context is None:
        return ""

    lines: list[str] = []
    flow_event = _context_value(context, "flow_event")
    answer_result = _context_value(context, "answer_result")
    today_tasks_completed = _context_value(context, "today_tasks_completed")

    if flow_event:
        lines.append(f"프론트 이벤트: {flow_event}")
    if answer_result:
        lines.append(f"직전 채점 결과: {answer_result}")
    if today_tasks_completed is not None:
        lines.append(f"오늘 학습목록 완료 여부: {today_tasks_completed}")

    if not lines:
        return ""

    return "시연 화면 상태:\n" + "\n".join(f"- {line}" for line in lines) + "\n\n"


def _context_value(context, field: str, default=None):
    if context is None:
        return default
    if isinstance(context, dict):
        return context.get(field, default)
    return getattr(context, field, default)


def motivator(state: ChatState) -> ChatResponse:
    """Handle TP1, TP2, TP3, TP5, and non-TP4 free chat turns."""
    from app.clients.llm import motivator_llm as llm

    grade_group = state["grade_group"]
    segment = state["segment"]
    touchpoint = state["current_touchpoint"]
    chat_history = state.get("chat_history", [])
    latest_student_input = _latest_student_message(chat_history).strip()

    if should_check_latest_input(state, latest_student_input):
        blocked_message = check_agent_input_sync(
            latest_student_input,
            state,
            agent_name="motivator",
        )
        if blocked_message:
            logger.info(
                "motivator input guard returned blocked response",
                extra={
                    "student_id": state["student_id"],
                    "thread_id": state["thread_id"],
                    "touchpoint": touchpoint.value if touchpoint else "chat",
                },
            )
            return make_chat_response(state["thread_id"], [make_text(blocked_message)])

    system_prompt = build_system_prompt(grade_group, segment, MOTIVATOR_ROLE)
    situation = _get_situation(state)
    recent = chat_history[-_HISTORY_WINDOW:] if len(chat_history) > _HISTORY_WINDOW else chat_history

    messages = [SystemMessage(content=system_prompt)]
    messages += list(recent)
    if situation:
        messages.append(HumanMessage(content=situation))

    logger.info(
        "motivator node invoked",
        extra={
            "student_id": state["student_id"],
            "touchpoint": touchpoint.value if touchpoint else "chat",
            "segment": segment.value,
        },
    )

    response = guarded_invoke(
        llm,
        messages,
        state,
        agent_name="motivator",
        render_output=lambda raw: str(getattr(raw, "content", "")),
    )
    content = str(getattr(response, "content", ""))

    logger.info("motivator node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(content)])


def _get_situation(state: ChatState) -> str:
    touchpoint = state.get("current_touchpoint")

    if state["use_case"] == UseCase.CHAT:
        return _situation_chat(state)

    if touchpoint == Touchpoint.TP1:
        return _situation_tp1(state)
    if touchpoint == Touchpoint.TP2:
        return _situation_tp2(state)
    if touchpoint == Touchpoint.TP3:
        return _situation_tp3(state)
    if touchpoint == Touchpoint.TP5:
        return _situation_tp5(state)
    return ""


def _situation_chat(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    touchpoint = state.get("current_touchpoint")
    latest = _latest_student_message(state.get("chat_history", []))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = remaining_tasks(today_tasks, completed_tasks)
    active_tasks = remaining if completed_tasks else today_tasks

    if touchpoint == Touchpoint.TP3:
        decision = _make_motivator_decision(state)
        current_task = state.get("current_task")
        task_line = _task_lines([current_task] if current_task else [])
        remaining_problem_count = state.get("current_task_remaining_count")
        problem_count_line = (
            f"현재 단원에서 남은 문제 수는 {remaining_problem_count}문제야.\n"
            if remaining_problem_count
            else ""
        )
        return (
            f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            f"방금 이렇게 말했어: \"{latest}\"\n"
            f"지금 화면의 현재 단원:\n{task_line}\n\n"
            f"{problem_count_line}"
            f"{_decision_lines(decision)}\n\n"
            "내 말에 이어서 바로 대답해줘. "
            "내가 조금 더 해보겠다고 했으니 현재 화면 안에서 할 수 있는 아주 작은 행동 하나만 말해줘."
        )

    if touchpoint == Touchpoint.TP5 and "여기까지" in latest:
        return (
            f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            f"방금 이렇게 말했어: \"{latest}\"\n\n"
            "오늘은 끝내겠다는 뜻이야. 나가기 버튼이나 새 학습을 제안하지 말고 따뜻하게 마무리해줘."
        )

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
        f"방금 이렇게 말했어: \"{latest}\"\n"
        f"내 홈 화면에서 지금 말할 수 있는 단원:\n{_task_lines(active_tasks)}\n\n"
        "내 말에 이어서 바로 대답해줘. "
        "내가 추천한 단원을 해보겠다고 했어. 추천이 필요하면 위 단원 중 하나만 말해줘."
    )


def _situation_tp1(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    pattern = state["learning_pattern"]
    decision = _make_motivator_decision(state)

    habits = [
        label
        for label, enabled in {
            "건너뛰는 습관": pattern.get("skipping_habit"),
            "찍는 습관": pattern.get("guessing_habit"),
            "대충 푸는 습관": pattern.get("careless_habit"),
        }.items()
        if enabled
    ]
    habit_line = f"내 학습 습관 참고: {', '.join(habits)}\n" if habits else ""

    return (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. 지금 앱 홈 화면을 열었어.\n"
        f"내 최근 평균 점수는 {profile['recent_avg_score']}점이고, "
        f"좋아하는 과목은 {profile['preferred_subject']}, 잘하는 과목은 {profile['strong_subject']}야.\n"
        f"{habit_line}"
        f"{_request_context_lines(state)}"
        "오늘 홈 화면에는 4개 단원이 보여:\n"
        f"{_task_lines(today_tasks)}\n\n"
        f"{_decision_lines(decision)}\n\n"
        "이 중에서 지금 바로 시작할 추천 단원 하나만 알려줘."
    )


def _situation_tp2(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = remaining_tasks(today_tasks, completed_tasks)
    decision = _make_motivator_decision(state)

    if remaining:
        return (
            f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            "방금 아래 단원을 끝냈어:\n"
            f"{_task_lines(completed_tasks)}\n\n"
            f"{_request_context_lines(state)}"
            f"아직 남은 단원은 {len(remaining)}개야:\n"
            f"{_task_lines(remaining)}\n\n"
            f"{_decision_lines(decision)}\n\n"
            "다음에 무엇을 하면 좋을지 남은 단원 중 하나만 추천해줘."
        )

    return (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
        f"오늘 할 단원 {len(today_tasks)}개를 모두 끝냈어.\n"
        f"완료한 단원:\n{_task_lines(completed_tasks)}\n\n"
        f"{_request_context_lines(state)}"
        f"오답 상황: {_build_wrong_answer_summary(state)}\n\n"
        f"{_decision_lines(decision)}"
    )


def _situation_tp3(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    current_task = state.get("current_task")
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining_count = len(remaining_tasks(today_tasks, completed_tasks))
    remaining_problem_count = state.get("current_task_remaining_count")
    problem_count_line = (
        f"현재 단원에서 남은 문제 수는 {remaining_problem_count}문제야.\n\n"
        if remaining_problem_count is not None
        else ""
    )
    decision = _make_motivator_decision(state)

    if current_task:
        task_info = (
            f"지금 하고 있는 단원은 {current_task['subject']} - {current_task['unit']}이야 "
            f"(난이도 {current_task['difficulty']})."
        )
        current_units = [current_task]
    else:
        task_info = "지금 하고 있는 단원 정보는 없어."
        current_units = []

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. {task_info}\n"
        f"아직 남은 단원 수는 {remaining_count}개야.\n\n"
        f"{problem_count_line}"
        f"{_request_context_lines(state)}"
        f"{_decision_lines(decision)}\n\n"
        "나가기 버튼을 눌러서 이탈하려는 상황이야. 나가기 방법을 안내하지 말고, 강요하지 말고 공감해줘. "
        "그래도 계속할 수 있게 현재 단원 안에서 할 수 있는 아주 작은 행동 하나만 말해줘."
    )


def _situation_tp5(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = remaining_tasks(today_tasks, completed_tasks)
    wrong_summary = _build_wrong_answer_summary(state)
    decision = _make_motivator_decision(state)

    if remaining:
        next_request = (
            "아직 오늘의 학습 단원이 남아 있어. 나가기 버튼이나 새 학습을 제안하지 말고 "
            "남은 단원 중 하나만 부담 낮게 이어서 하도록 권해줘."
        )
    else:
        next_request = "남은 단원이 없으므로 decision에 따라 오답/복습 유도 또는 마무리만 해줘."

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. 오늘 학습을 마치려 해.\n"
        f"완료한 단원 ({len(completed_tasks)}/{len(today_tasks)}개):\n"
        f"{_task_lines(completed_tasks)}\n\n"
        f"{_request_context_lines(state)}"
        f"남은 단원:\n{_task_lines(remaining)}\n"
        f"오답 상황: {wrong_summary}\n"
        f"오늘 평균 점수: {state['today_score']}점\n\n"
        f"{_decision_lines(decision)}\n\n"
        f"{next_request}"
    )


def _build_wrong_answer_summary(state: ChatState) -> str:
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]
    wrong_total = pattern.get("wrong_content_total", 0)
    wrong_done = pattern.get("wrong_content_done", 0)

    if not has_wrong:
        return "오늘 틀린 문제는 없어."
    if wrong_done_today:
        return f"오늘 오답 {wrong_total}개를 모두 복습했어."
    remaining = max(wrong_total - wrong_done, 0)
    return f"오답 {wrong_total}개 중 {remaining}개가 아직 남아 있어."
