"""
Central business decision policy for the chat graph.

This module is the place to inspect or change:
- how incoming frontend events are interpreted,
- which graph agent handles each use case/touchpoint,
- what intent motivator/helper should follow before the LLM writes text.

Node modules should stay focused on guardrails, prompt assembly, LLM calls,
and response parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.enums import MessageType, Touchpoint, UseCase
from app.schemas.chat import ChatState, Task

AgentRoute = Literal["classify", "motivator", "helper"]
MessageSource = Literal["app_event", "student_text", "student_choice"]


@dataclass(frozen=True)
class MessageEventPolicy:
    """How one incoming chat event should be interpreted by the graph."""

    message_type: MessageType
    content: str
    source: MessageSource
    should_append_human_message: bool
    should_check_input_guard: bool


def classify_message_event(
    message_type: MessageType,
    content: str,
) -> MessageEventPolicy:
    """Make frontend event semantics explicit at the API boundary."""
    clean_content = content.strip()

    if message_type == MessageType.TEXT:
        return MessageEventPolicy(
            message_type=message_type,
            content=clean_content,
            source="student_text",
            should_append_human_message=bool(clean_content),
            should_check_input_guard=bool(clean_content),
        )

    if message_type == MessageType.CHOICE:
        return MessageEventPolicy(
            message_type=message_type,
            content=clean_content,
            source="student_choice",
            should_append_human_message=bool(clean_content),
            should_check_input_guard=False,
        )

    return MessageEventPolicy(
        message_type=message_type,
        content=clean_content,
        source="app_event",
        should_append_human_message=bool(clean_content),
        should_check_input_guard=False,
    )


def should_check_latest_input(state: ChatState, latest_content: str) -> bool:
    """Return whether the latest HumanMessage should be treated as free-form input."""
    if not latest_content.strip():
        return False

    requires_guard = state.get("current_message_requires_input_guard")
    if requires_guard is not None:
        return bool(requires_guard)

    message_type = state.get("current_message_type")
    if message_type is None:
        return True
    if isinstance(message_type, str):
        message_type = MessageType(message_type)

    return message_type == MessageType.TEXT


def route_agent(state: ChatState) -> AgentRoute:
    """Choose the business agent for an already-classified state."""
    use_case = _use_case(state["use_case"])
    touchpoint = _touchpoint(state["current_touchpoint"])

    if use_case == UseCase.LEARNING:
        if touchpoint != Touchpoint.TP4:
            raise ValueError(
                f"use_case=learning only allows tp4. Received: {touchpoint}"
            )
        return "helper"

    if use_case == UseCase.CHAT:
        if touchpoint == Touchpoint.TP4:
            return "helper"
        return "motivator"

    if touchpoint == Touchpoint.TP4:
        raise ValueError("use_case=talk does not allow tp4.")
    if touchpoint in (Touchpoint.TP1, Touchpoint.TP2, Touchpoint.TP3, Touchpoint.TP5):
        return "motivator"

    raise ValueError(f"Unsupported touchpoint: {touchpoint}")


def entry_route(state: ChatState) -> AgentRoute:
    """Classify first on new sessions, then route to the selected agent."""
    if state.get("student_profile") is None:
        return "classify"
    return route_agent(state)


def task_key(task: Task | dict) -> tuple[str, str]:
    return str(task.get("subject", "")), str(task.get("unit", ""))


def remaining_tasks(
    today_tasks: list[Task] | list[dict],
    completed_tasks: list[Task] | list[dict],
) -> list:
    completed_keys = {task_key(task) for task in completed_tasks}
    return [task for task in today_tasks if task_key(task) not in completed_keys]


def make_motivator_decision(state: ChatState) -> dict:
    """Decide the motivator intent before asking the LLM to write student text."""
    touchpoint = _touchpoint(state.get("current_touchpoint", Touchpoint.TP1))
    today_tasks = state.get("today_tasks", [])
    completed_tasks = state.get("completed_tasks", [])
    remaining = remaining_tasks(today_tasks, completed_tasks)
    current_task = state.get("current_task")

    if touchpoint == Touchpoint.TP3:
        return {
            "intent": "retain_current_task",
            "target_task": current_task,
            "candidate_tasks": [current_task] if current_task else [],
            "student_goal": "이탈 이벤트에 공감하되 현재 단원 안의 아주 작은 행동 하나로 이어가게 한다.",
            "forbidden": ["나가기 방법 안내", "새 학습 제안", "문제 풀이 힌트로 바로 진입"],
        }

    if remaining:
        return {
            "intent": "recommend_next_task",
            "target_task": remaining[0] if len(remaining) == 1 else None,
            "candidate_tasks": remaining,
            "student_goal": "남은 오늘의 학습 중 하나를 부담 없게 이어서 시작하게 한다.",
            "forbidden": ["완료된 단원 추천", "새 단원 생성", "나가기 버튼 제안"],
        }

    has_wrong_answers = state.get("has_wrong_answers", False)
    wrong_done_today = state.get("wrong_content_done_today", False)
    if has_wrong_answers and not wrong_done_today:
        return {
            "intent": "suggest_review",
            "target_task": None,
            "candidate_tasks": [],
            "student_goal": "남은 오답/복습 콘텐츠를 아주 부담 없게 이어가게 한다.",
            "forbidden": ["새 단원 추천", "새 문제 생성", "별도 활동 제안", "나가기 버튼 제안"],
        }

    return {
        "intent": "wrap_up_today",
        "target_task": None,
        "candidate_tasks": [],
        "student_goal": "오늘의 학습 완료를 인정하고 부드럽게 마무리한다.",
        "forbidden": ["새 단원 추천", "새 문제 생성", "별도 활동 제안", "나가기 버튼 제안"],
    }


def make_helper_decision(
    state: ChatState,
    problem: dict,
    last_content: str,
    turn_count: int,
) -> dict:
    """Decide the TP4 helper mode before asking the LLM to write student text."""
    if not problem:
        return {
            "intent": "ask_for_problem",
            "required_tool": "send_text",
            "student_goal": "코칭을 시작하기 전에 학생이 현재 풀고 있는 문제를 선택하거나 열도록 안내한다.",
            "target_problem": None,
            "forbidden": [
                "문제를 새로 만들기",
                "확인된 문제 없이 막힌 이유 선택지 제시하기",
                "정답이나 해설 알려주기",
            ],
        }

    if turn_count == 0:
        return {
            "intent": "collect_stuck_cause",
            "required_tool": "send_causes",
            "max_choices": 3,
            "student_goal": "힌트를 주기 전에 학생이 어디에서 막혔는지 고를 수 있게 돕는다.",
            "target_problem": problem,
            "forbidden": [
                "정답 알려주기",
                "전체 풀이 설명하기",
                "선택지를 3개보다 많이 제시하기",
            ],
        }

    return {
        "intent": "coach_next_step",
        "required_tool": "send_text",
        "student_goal": "학생의 최근 말에 이어서 아주 작은 다음 단계나 질문 하나를 제시한다.",
        "target_problem": problem,
        "latest_student_message": last_content,
        "forbidden": [
            "정답 알려주기",
            "전체 풀이 설명하기",
            "새 문제 만들기",
        ],
    }


def _use_case(value: UseCase | str) -> UseCase:
    if isinstance(value, UseCase):
        return value
    return UseCase(value)


def _touchpoint(value: Touchpoint | str) -> Touchpoint:
    if isinstance(value, Touchpoint):
        return value
    return Touchpoint(value)
