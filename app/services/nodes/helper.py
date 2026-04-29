from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool

from app.core.logging import get_logger
from app.data.loader import load_problem
from app.schemas.chat import ChatState, ResponseMessage
from app.services.nodes.common import (
    make_choices,
    make_hint_card,
    make_image_card,
    make_text,
)
from app.services.prompts.agents import HELPER_ROLE, build_system_prompt

logger = get_logger(__name__)

TP4_PHASE_AWAITING_PROBLEM = "awaiting_problem"
TP4_PHASE_COACHING = "coaching"


@tool
def send_causes(items: list[dict]) -> str:
    """학생에게 막힌 이유 선택지를 제시합니다.

    Each item must be {"id": "snake_case_english_id", "label": "Korean student-facing label"}.
    Use this when a child may not be able to name where they are stuck.
    """
    return str(items)


@tool
def send_text(content: str) -> str:
    """학생에게 코칭 텍스트 메시지를 전송합니다."""
    return content


@tool
def send_hint_card(steps: list[str]) -> str:
    """단계별 힌트 카드를 보여줍니다. Each step should be short and student-friendly."""
    return str(steps)


@tool
def send_image_card(caption: str) -> str:
    """그림/시각 자료 카드를 보여줍니다. Describe what visual aid should be shown."""
    return caption


def helper(state: ChatState) -> dict:
    from app.clients.llm import helper_llm as llm

    current_problem = state.get("current_problem")
    chat_history = state.get("chat_history", [])
    last_content = chat_history[-1].content.strip() if chat_history else ""
    turn_count = int(state.get("tp4_turn_count") or 0)

    logger.info(
        "helper node invoked",
        extra={
            "student_id": state["student_id"],
            "segment": state["segment"].value,
            "grade_group": state["grade_group"].value,
            "tp4_phase": state.get("tp4_phase") or TP4_PHASE_AWAITING_PROBLEM,
            "tp4_turn_count": turn_count,
        },
    )

    result: dict = {
        "tp4_phase": TP4_PHASE_COACHING,
        "tp4_turn_count": turn_count + 1,
    }

    if current_problem is None:
        current_problem = _try_load_problem(last_content) or {}
        result["current_problem"] = current_problem

    result["helper_response"] = _coach_tp4(state, current_problem, llm)

    logger.info(
        "helper node completed",
        extra={
            "student_id": state["student_id"],
            "tp4_phase": result["tp4_phase"],
            "tp4_turn_count": result["tp4_turn_count"],
        },
    )

    return result


def _try_load_problem(problem_id: str) -> dict | None:
    """Load a problem by id. Return None when it cannot be loaded."""
    if not problem_id:
        return None
    try:
        return dict(load_problem(problem_id))
    except (KeyError, ValueError):
        return None


def _coach_tp4(state: ChatState, problem: dict, llm) -> list[ResponseMessage]:
    """Let the LLM run TP4 as an ongoing coaching conversation."""
    profile = state["student_profile"]
    segment = state["segment"]
    grade_group = state["grade_group"]
    history = _format_recent_history(state.get("chat_history", []))

    system_prompt = build_system_prompt(grade_group, segment, HELPER_ROLE) + (
        "\n\nTP4 is an agentic, multi-turn coaching conversation.\n"
        "Use the full conversation history. Do not treat any one student message as a fixed backend category.\n"
        "Choice buttons are only a child-friendly scaffold: use send_causes when the student may not know"
        " how to explain where they are stuck.\n"
        "If the student selects a choice, describes a new reason, changes their mind, or attempts an answer,"
        " continue naturally from that message.\n"
        "Guide step by step with one small next question or hint. Do not jump straight to the final answer.\n"
        "Use any suitable tool: send_causes, send_text, send_hint_card, or send_image_card."
    )

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"세그먼트: {segment.value}\n\n"
        f"{_problem_context(problem, state)}\n\n"
        f"최근 대화:\n{history}\n\n"
        "지금 이 대화의 다음 코칭 응답을 생성해 주세요."
    )

    response = llm.bind_tools([
        send_causes,
        send_text,
        send_hint_card,
        send_image_card,
    ]).invoke([
        SystemMessage(content=system_prompt),
        SystemMessage(content=user_message),
    ])

    return _parse_helper_response(response)


def _problem_context(problem: dict | None, state: ChatState) -> str:
    if problem:
        return (
            "현재 문제:\n"
            f"과목: {problem.get('subject', '정보 없음')}\n"
            f"단원: {problem.get('unit', '정보 없음')}\n"
            f"문제: {problem.get('question', '(문제 없음)')}\n"
            f"정답: {problem.get('answer', '')}\n"
            f"설명: {problem.get('explanation', '')}"
        )

    current_task = state.get("current_task")
    if current_task:
        return (
            f"현재 단원: {current_task['subject']} - {current_task['unit']} "
            f"(난이도 {current_task['difficulty']})\n"
            "(구체적인 문제 데이터 없음)"
        )
    return "(문제 데이터 없음 - 일반적인 학습 막힘 상황)"


def _format_recent_history(messages) -> str:
    if not messages:
        return "(이전 대화 없음)"

    lines: list[str] = []
    for message in messages[-10:]:
        role = "학생"
        if message.__class__.__name__ == "AIMessage":
            role = "코치"
        content = getattr(message, "content", "")
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(이전 대화 없음)"


def _parse_helper_response(response) -> list[ResponseMessage]:
    messages: list[ResponseMessage] = []

    for tool_call in getattr(response, "tool_calls", []):
        name = tool_call["name"]
        args = tool_call["args"]

        if name == "send_causes":
            raw_items = args.get("items", [])
            try:
                choices = [(item["id"], item["label"]) for item in raw_items if "id" in item and "label" in item]
                if choices:
                    messages.append(make_choices(choices))
            except (TypeError, KeyError):
                pass

        elif name == "send_text":
            content = args.get("content", "")
            if content:
                messages.append(make_text(content))

        elif name == "send_hint_card":
            steps = args.get("steps", [])
            if steps:
                messages.append(make_hint_card(steps))

        elif name == "send_image_card":
            caption = args.get("caption", "")
            if caption:
                messages.append(make_image_card("https://placeholder.invalid/img", caption))

    if not messages:
        content = getattr(response, "content", "") or "좋아요, 한 단계씩 같이 생각해 볼까요?"
        messages.append(make_text(content))

    return messages
