from __future__ import annotations

from collections.abc import Callable, Sequence
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.core.logging import get_logger
from app.guardrails.models import GuardrailContext, OutputCheckResult
from app.schemas.chat import ChatState

logger = get_logger(__name__)

_TOUCHPOINT_MAP = {
    Touchpoint.TP1: "home_screen",
    Touchpoint.TP2: "after_task",
    Touchpoint.TP3: "exit",
    Touchpoint.TP4: "during_study",
    Touchpoint.TP5: "after_all_tasks",
}


def guarded_invoke(
    runnable,
    messages: Sequence[Any],
    state: ChatState,
    *,
    agent_name: str,
    render_output: Callable[[Any], str],
    max_repairs: int = 1,
) -> Any:
    """Invoke an agent LLM and centrally retry once when output guardrails warn."""
    started = perf_counter()
    response = runnable.invoke(list(messages))
    logger.info(
        "coach llm call completed",
        extra={
            "student_id": state["student_id"],
            "thread_id": state["thread_id"],
            "agent_name": agent_name,
            "touchpoint": state["current_touchpoint"].value,
            "attempt": 0,
            "duration_ms": _elapsed_ms(started),
        },
    )

    for attempt in range(max_repairs + 1):
        output_text = render_output(response)
        guard_result = check_agent_output(
            output_text,
            state,
            agent_name=agent_name,
        )
        if guard_result.passed:
            return response
        if attempt >= max_repairs:
            logger.warning(
                "Agent output guardrail still failed after repairs",
                extra={
                    "student_id": state["student_id"],
                    "thread_id": state["thread_id"],
                    "agent_name": agent_name,
                    "touchpoint": state["current_touchpoint"].value,
                    "attempts": attempt,
                    "reasons": guard_result.reasons,
                },
            )
            return response

        reasons = guard_result.reasons or ["Output quality guard failed."]
        logger.warning(
            "Agent output blocked by guardrail; requesting regeneration",
            extra={
                "student_id": state["student_id"],
                "thread_id": state["thread_id"],
                "agent_name": agent_name,
                "touchpoint": state["current_touchpoint"].value,
                "attempt": attempt + 1,
                "reasons": reasons,
            },
        )
        repair_started = perf_counter()
        response = runnable.invoke([
            *messages,
            HumanMessage(content=_build_repair_message(reasons, output_text)),
        ])
        logger.info(
            "coach llm repair call completed",
            extra={
                "student_id": state["student_id"],
                "thread_id": state["thread_id"],
                "agent_name": agent_name,
                "touchpoint": state["current_touchpoint"].value,
                "attempt": attempt + 1,
                "duration_ms": _elapsed_ms(repair_started),
            },
        )

    return response


def check_agent_output(
    output_text: str,
    state: ChatState,
    *,
    agent_name: str,
) -> OutputCheckResult:
    from app.guardrails import build_pipeline

    context = _context_from_state(state, agent_name=agent_name)
    started = perf_counter()
    result = build_pipeline(context).check_output_sync(output_text, context)
    logger.info(
        "agent output guard completed",
        extra={
            "student_id": state["student_id"],
            "thread_id": state["thread_id"],
            "agent_name": agent_name,
            "touchpoint": state["current_touchpoint"].value,
            "passed": result.passed,
            "duration_ms": _elapsed_ms(started),
        },
    )
    return result


def check_agent_input_sync(
    input_text: str,
    state: ChatState,
    *,
    agent_name: str,
) -> str | None:
    """Return a blocked message when the latest student input is unsafe."""
    from app.guardrails import build_pipeline

    context = _context_from_state(state, agent_name=agent_name)
    started = perf_counter()
    result = build_pipeline(context).check_input_sync(input_text, context)
    logger.info(
        "agent input guard completed",
        extra={
            "student_id": state["student_id"],
            "thread_id": state["thread_id"],
            "agent_name": agent_name,
            "touchpoint": state["current_touchpoint"].value,
            "passed": result.passed,
            "duration_ms": _elapsed_ms(started),
        },
    )
    if result.passed:
        return None

    logger.info(
        "Agent input blocked by guardrail",
        extra={
            "student_id": state["student_id"],
            "thread_id": state["thread_id"],
            "agent_name": agent_name,
            "touchpoint": state["current_touchpoint"].value,
            "reasons": [guard.reason for guard in result.guard_results if guard.reason],
        },
    )
    return result.blocked_message


def _context_from_state(
    state: ChatState,
    *,
    agent_name: str,
) -> GuardrailContext:
    touchpoint = state["current_touchpoint"]
    grade_group = state["grade_group"]
    segment = state["segment"]
    use_case = state["use_case"]

    return GuardrailContext(
        touchpoint=_TOUCHPOINT_MAP.get(touchpoint, "during_study"),
        use_case=_guardrail_use_case(use_case),
        grade_group=_enum_value(grade_group),
        segment=_enum_value(segment),
        session_id=state.get("thread_id"),
        agent_name=agent_name,
    )


def _guardrail_use_case(use_case: UseCase | str | None) -> str | None:
    value = _enum_value(use_case)
    if value in {UseCase.TALK.value, UseCase.LEARNING.value}:
        return value
    return None


def _enum_value(value: Any) -> str:
    if isinstance(value, (GradeGroup, Segment, Touchpoint, UseCase)):
        return value.value
    return str(value)


def _build_repair_message(
    reasons: list[str],
    output_text: str,
) -> str:
    reasons_text = "\n".join(f"- {reason}" for reason in reasons)
    return (
        "방금 응답은 출력 품질 guardrail에서 차단되었습니다.\n"
        "아래 이유를 반영해서 같은 상황에 대한 응답을 다시 작성하세요.\n\n"
        f"차단 이유:\n{reasons_text}\n\n"
        "아이에게 그대로 보여줄 최종 응답만 출력하세요. "
        "내부 설명, 메타데이터, 선택 이유, 실제 출력, 응답 예정, 도구 코드, JSON, 선생님용 메모를 쓰지 마세요. "
        "새 문제, 새 예시, 새 미션, 새 퀴즈, 교과서 페이지, 새 과제를 만들지 마세요.\n\n"
        f"차단된 원문:\n{output_text}"
    )


def _elapsed_ms(started: float) -> int:
    return round((perf_counter() - started) * 1000)
