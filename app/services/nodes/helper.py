from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.core.logging import get_logger
from app.data.loader import load_problem
from app.guardrails.agent_output import check_agent_input_sync, guarded_invoke
from app.schemas.chat import ChatState, ResponseMessage
from app.services.nodes.common import (
    make_choices,
    make_hint_card,
    make_image_card,
    make_text,
)
from app.services.decision_policy import (
    make_helper_decision as _make_helper_decision,
    should_check_latest_input,
)
from app.services.prompts.agents import HELPER_ROLE, build_system_prompt

logger = get_logger(__name__)

TP4_PHASE_AWAITING_PROBLEM = "awaiting_problem"
TP4_PHASE_COACHING = "coaching"


@tool
def send_causes(items: list[dict]) -> str:
    """학생에게 막힌 이유 선택지를 제시합니다.

    Each item must be {"id": "snake_case_english_id", "label": "Korean student-facing label"}.
    Use this only when a child may not be able to name where they are stuck.
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

    app_controlled_problem_selection = False
    result: dict = {}

    if not current_problem:
        loaded_problem = _try_load_problem(last_content)
        if loaded_problem:
            current_problem = loaded_problem
            app_controlled_problem_selection = True
        else:
            current_problem = {}
        result["current_problem"] = current_problem

    if (
        should_check_latest_input(state, last_content)
        and not app_controlled_problem_selection
    ):
        blocked_message = check_agent_input_sync(
            last_content,
            state,
            agent_name="helper",
        )
        if blocked_message:
            logger.info(
                "helper input guard returned blocked response",
                extra={
                    "student_id": state["student_id"],
                    "thread_id": state["thread_id"],
                    "tp4_turn_count": turn_count,
                },
            )
            return {"helper_response": [make_text(blocked_message)]}

    result["tp4_phase"] = TP4_PHASE_COACHING
    result["tp4_turn_count"] = turn_count + 1
    result["helper_response"] = _coach_tp4(state, current_problem, last_content, turn_count, llm)

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


def _helper_decision_lines(decision: dict) -> str:
    target_problem = decision.get("target_problem")
    target_line = _problem_decision_summary(target_problem)
    forbidden = ", ".join(decision.get("forbidden", [])) or "none"
    max_choices = decision.get("max_choices")
    max_choices_line = f"- max_choices: {max_choices}\n" if max_choices else ""

    return (
        "시스템이 먼저 확정한 helper decision:\n"
        f"- intent: {decision['intent']}\n"
        f"- required_tool: {decision['required_tool']}\n"
        f"{max_choices_line}"
        f"- student_goal: {decision['student_goal']}\n"
        f"- target_problem: {target_line}\n"
        f"- forbidden: {forbidden}\n\n"
        "위 decision의 범위를 벗어나지 말고, 아이에게 그대로 보일 최종 응답만 작성해줘. "
        "intent, required_tool, target_problem, student_goal, forbidden 같은 내부 필드명은 절대 말하지 마."
    )


def _problem_decision_summary(problem: dict | None) -> str:
    if not problem:
        return "none"
    return (
        f"{problem.get('problem_id', 'unknown')} | "
        f"{problem.get('subject', 'unknown')} | "
        f"{problem.get('unit', 'unknown')}"
    )


def _coach_tp4(
    state: ChatState,
    problem: dict,
    last_content: str,
    turn_count: int,
    llm,
) -> list[ResponseMessage]:
    """Let the LLM run TP4 as an ongoing coaching conversation."""
    profile = state["student_profile"]
    segment = state["segment"]
    grade_group = state["grade_group"]
    history = _format_recent_history(state.get("chat_history", []))
    decision = _make_helper_decision(state, problem, last_content, turn_count)

    system_prompt = build_system_prompt(grade_group, segment, HELPER_ROLE)
    if problem:
        system_prompt += (
            "\n\n코치 참고용 정답/해설입니다. 아이에게 그대로 말하지 말고 힌트 방향을 잡는 데만 사용하세요:\n"
            f"정답: {problem.get('answer', '')}\n"
            f"해설: {problem.get('explanation', '')}"
        )

    call_name = _student_call_name(str(profile.get("name", "")))
    user_message = (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야.\n"
        f"나를 부를 때는 반드시 '{call_name}'라고 불러줘.\n"
        "지금 이 문제를 보다가 막혀서 도움을 받고 싶어.\n\n"
        f"{_problem_context(problem, state)}\n\n"
        f"최근 대화:\n{history}\n\n"
        f"{_helper_decision_lines(decision)}"
    )

    bound_llm = llm.bind_tools([
        send_causes,
        send_text,
        send_hint_card,
        send_image_card,
    ])
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = _invoke_helper_with_decision(
        bound_llm,
        messages,
        state,
        decision,
    )

    return _parse_helper_response(response, required_tool=decision["required_tool"])


def _student_call_name(name: str) -> str:
    if not name:
        return "친구야"
    last = name[-1]
    code = ord(last) - 0xAC00
    if 0 <= code <= 11171 and code % 28:
        return f"{name}아"
    return f"{name}야"


def _render_helper_output_for_guard(response) -> str:
    parts: list[str] = []
    content = str(getattr(response, "content", "") or "")
    if content:
        parts.append(content)

    for tool_call in getattr(response, "tool_calls", []):
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        parts.append(f"tool:{name} args:{args}")

    return "\n".join(parts)


def _invoke_helper_with_decision(
    bound_llm,
    messages: list,
    state: ChatState,
    decision: dict,
):
    required_tool = decision.get("required_tool")
    response = guarded_invoke(
        bound_llm,
        messages,
        state,
        agent_name="helper",
        render_output=_render_helper_output_for_guard,
    )
    if _required_tool_used(response, required_tool):
        return response

    logger.warning(
        "helper used wrong response tool; requesting repair",
        extra={
            "student_id": state["student_id"],
            "thread_id": state["thread_id"],
            "required_tool": required_tool,
            "actual_tools": _tool_names(response),
        },
    )
    repaired_response = guarded_invoke(
        bound_llm,
        [
            *messages,
            HumanMessage(content=_build_tool_repair_message(decision)),
        ],
        state,
        agent_name="helper",
        render_output=_render_helper_output_for_guard,
    )
    if not _required_tool_used(repaired_response, required_tool):
        logger.warning(
            "helper response tool still invalid after repair",
            extra={
                "student_id": state["student_id"],
                "thread_id": state["thread_id"],
                "required_tool": required_tool,
                "actual_tools": _tool_names(repaired_response),
            },
        )
    return repaired_response


def _required_tool_used(response, required_tool: str | None) -> bool:
    if not required_tool:
        return True
    return required_tool in _tool_names(response)


def _tool_names(response) -> list[str]:
    names: list[str] = []
    for tool_call in getattr(response, "tool_calls", []):
        name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
        if name:
            names.append(str(name))
    return names


def _build_tool_repair_message(decision: dict) -> str:
    required_tool = decision.get("required_tool", "send_text")
    return (
        "방금 helper 응답이 필요한 응답 방식과 달랐어. "
        f"다시 응답하되 반드시 `{required_tool}` tool만 사용해. "
        "다른 tool은 사용하지 말고, 내부 decision 필드명은 아이에게 노출하지 마."
    )


def _problem_context(problem: dict | None, state: ChatState) -> str:
    if problem:
        return (
            "내 화면에 보이는 문제 정보:\n"
            f"과목: {problem.get('subject', '정보 없음')}\n"
            f"단원: {problem.get('unit', '정보 없음')}\n"
            f"문제: {problem.get('question', '(문제 없음)')}"
        )

    current_task = state.get("current_task")
    if current_task:
        return (
            f"내가 지금 보고 있는 단원: {current_task['subject']} - {current_task['unit']} "
            f"(난이도 {current_task['difficulty']})\n"
            "(구체적인 문제 데이터는 아직 없어.)"
        )
    return "(문제 데이터가 아직 없어.)"


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


def _parse_helper_response(response, *, required_tool: str | None = None) -> list[ResponseMessage]:
    messages: list[ResponseMessage] = []

    for tool_call in getattr(response, "tool_calls", []):
        name = tool_call["name"]
        args = tool_call["args"]
        if required_tool and name != required_tool:
            continue

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
        content = getattr(response, "content", "") or "좋아, 한 단계만 같이 생각해보자."
        messages.append(make_text(content))

    return messages
