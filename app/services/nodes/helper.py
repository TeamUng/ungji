from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
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
_HELPER_META_MARKERS = (
    "선택 이유",
    "추천 이유",
    "ESSENTIAL",
    "send_text",
    "JSON",
    "이유:",
    "내부",
)


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
    turn_count = int(state.get("tp4_turn_count") or 0)

    system_prompt = build_system_prompt(grade_group, segment, HELPER_ROLE) + (
        "\n\nTP4 코칭 규칙:\n"
        "- 전체 대화 흐름을 보고 이어서 답한다.\n"
        "- 아이의 최신 메시지를 고정된 백엔드 분류값처럼 다루지 않는다.\n"
        "- 원인 선택지는 아이가 막힌 이유를 말로 설명하기 어려울 때만 쓰는 발판이다.\n"
        "- 아이가 선택지를 고르거나, 다른 이유를 말하거나, 마음을 바꾸거나, 풀이를 시도하면 그 말에서 자연스럽게 이어간다.\n"
        "- 한 번에 작은 질문이나 힌트 하나로 단계적으로 돕고, 최종 정답, 계산 결과, 공식 전체로 바로 뛰어가지 않는다.\n"
        "- 도구를 사용할 때는 실제 tool call만 사용하고, 본문에 send_text(...), JSON, 선택 이유, 내부 설명을 쓰지 않는다.\n"
        "- 상황에 맞게 send_causes, send_text, send_hint_card, send_image_card 중 하나를 사용한다."
    )
    if problem:
        system_prompt += (
            "\n\n코치 참고용 정답/해설입니다. 아이에게 그대로 말하지 말고 힌트 방향을 잡는 데만 사용하세요:\n"
            f"정답: {problem.get('answer', '')}\n"
            f"해설: {problem.get('explanation', '')}"
        )

    if turn_count == 0:
        phase_request = (
            "나는 아직 어디서 막혔는지 말하지 않았어. "
            "문제 ID만 눌렀으니 바로 풀어주지 말고, 내가 막힌 이유를 고를 수 있게 짧은 선택지를 보여줘."
        )
    else:
        phase_request = (
            "내가 방금 말한 막힌 지점에서 이어서 한 단계만 도와줘. "
            "정답이나 계산 결과를 한 번에 말하지 말고, 다음에 볼 것 하나만 물어봐줘."
        )

    call_name = _student_call_name(str(profile.get("name", "")))
    user_message = (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야.\n"
        f"나를 부를 때는 반드시 '{call_name}'라고 불러줘.\n"
        "지금 이 문제를 보다가 막혀서 도움을 받고 싶어.\n\n"
        f"{_problem_context(problem, state)}\n\n"
        f"최근 대화:\n{history}\n\n"
        f"{phase_request}"
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
    response = bound_llm.invoke(messages)
    if _needs_helper_repair(response, turn_count):
        logger.warning(
            "helper response repaired before delivery",
            extra={"student_id": state["student_id"], "tp4_turn_count": turn_count},
        )
        response = bound_llm.invoke([
            *messages,
            HumanMessage(content=_helper_repair_prompt(response, turn_count, call_name)),
        ])

    return _parse_helper_response(response)


def _student_call_name(name: str) -> str:
    if not name:
        return "친구야"
    last = name[-1]
    code = ord(last) - 0xAC00
    if 0 <= code <= 11171 and code % 28:
        return f"{name}아"
    return f"{name}야"


def _needs_helper_repair(response, turn_count: int) -> bool:
    content = str(getattr(response, "content", "") or "")
    if any(marker in content for marker in _HELPER_META_MARKERS):
        return True
    tool_names = [tool_call.get("name") for tool_call in getattr(response, "tool_calls", [])]
    return turn_count > 0 and "send_causes" in tool_names


def _helper_repair_prompt(response, turn_count: int, call_name: str) -> str:
    content = str(getattr(response, "content", "") or "")
    tool_names = ", ".join(tool_call.get("name", "") for tool_call in getattr(response, "tool_calls", []))
    if turn_count > 0:
        phase_rule = "아이는 이미 막힌 이유를 말했어. 원인 선택지를 다시 주지 말고 작은 힌트나 질문 하나로 이어가."
    else:
        phase_rule = "아이는 아직 막힌 이유를 말하지 않았어. 바로 풀지 말고 원인 선택지를 짧게 줘."
    return (
        "방금 응답은 아이에게 그대로 보낼 수 없어. "
        "메타 설명, 도구 코드, 내부 이유, 반복 선택지, 정답 직접 제공을 제거하고 다시 작성해.\n"
        f"학생을 부를 때는 반드시 '{call_name}'라고 불러.\n"
        f"{phase_rule}\n"
        "실제 tool call을 사용해. 본문에 send_text(...) 같은 코드를 쓰지 마.\n"
        f"이전 응답 content: {content}\n"
        f"이전 tool calls: {tool_names}"
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
        content = getattr(response, "content", "") or "좋아, 한 단계만 같이 생각해보자."
        messages.append(make_text(content))

    return messages
