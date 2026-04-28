from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.core.logging import get_logger
from app.data.loader import load_problem
from app.schemas.chat import ChatResponse, ChatState, ResponseMessage
from app.services.nodes.common import (
    make_chat_response,
    make_choices,
    make_hint_card,
    make_image_card,
    make_text,
)
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)


# ─── 출력 도구 정의 ───────────────────────────────────────────────────────────

@tool
def send_causes(items: list[dict]) -> str:
    """학생에게 막힌 원인 선택지를 제시합니다.
    각 item은 반드시 {"id": "snake_case_영문_id", "label": "한글 설명"} 형식이어야 합니다.
    3~4개의 구체적인 선택지를 생성하세요."""
    return str(items)


@tool
def send_text(content: str) -> str:
    """학생에게 코칭 텍스트 메시지를 전송합니다."""
    return content


@tool
def send_hint_card(steps: list[str]) -> str:
    """단계별 힌트 카드를 보여줍니다. 각 step은 짧은 한국어 안내 문장입니다."""
    return str(steps)


@tool
def send_image_card(caption: str) -> str:
    """그림/시각 자료 카드를 보여줍니다. caption에 어떤 그림을 보여줄지 설명하세요."""
    return caption


# ─── 메인 노드 ────────────────────────────────────────────────────────────────

def tp4(state: ChatState) -> dict:
    from app.clients.upstage import llm

    segment = state["segment"]
    grade_group = state["grade_group"]

    logger.info(
        "tp4 노드 시작",
        extra={
            "student_id": state["student_id"],
            "segment": segment.value,
            "grade_group": grade_group.value,
        },
    )

    current_problem = state.get("current_problem")
    chat_history = state.get("chat_history", [])
    last_content = chat_history[-1].content.strip() if chat_history else ""

    # Turn 1: 문제 ID로 문제 로드 → 원인 선택지 생성
    if current_problem is None:
        problem_data = _try_load_problem(last_content)
        messages = _generate_causes(state, problem_data, llm)
        result = {"tp4_response": messages, "current_problem": problem_data or {}}
    else:
        # Turn 2: 선택한 원인 + 저장된 문제 데이터로 코칭
        cause_label = last_content
        messages = _build_coaching(state, current_problem, cause_label, llm)
        result = {"tp4_response": messages}

    logger.info(
        "tp4 노드 완료",
        extra={
            "student_id": state["student_id"],
            "turn": 1 if current_problem is None else 2,
        },
    )

    return result


# ─── 내부 헬퍼 ───────────────────────────────────────────────────────────────

def _try_load_problem(problem_id: str) -> dict | None:
    """problem_id로 문제를 로드한다. 찾지 못하면 None 반환."""
    if not problem_id:
        return None
    try:
        return dict(load_problem(problem_id))
    except (KeyError, ValueError):
        return None


def _generate_causes(state: ChatState, problem: dict | None, llm) -> list[ResponseMessage]:
    """Turn 1: LLM이 문제를 분석해 막힌 원인 선택지를 동적으로 생성."""
    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "학생이 문제를 풀다가 막혀서 도움을 요청했습니다.\n"
        "주어진 문제와 학생 정보를 바탕으로, 이 학생이 막혔을 만한 원인 3~4가지를 "
        "선택지로 제시해주세요.\n"
        "반드시 send_causes 도구를 호출해 선택지를 전달하세요.\n"
        "각 선택지 id는 영문 snake_case로, label은 학생이 클릭하기 쉬운 짧은 한국어 문장으로 작성하세요."
    )

    if problem:
        problem_info = (
            f"현재 문제:\n"
            f"과목: {problem.get('subject', '알 수 없음')}\n"
            f"단원: {problem.get('unit', '알 수 없음')}\n"
            f"문제: {problem.get('question', '(문제 없음)')}"
        )
    else:
        current_task = state.get("current_task")
        if current_task:
            problem_info = (
                f"현재 과제: {current_task['subject']} - {current_task['unit']} "
                f"(난이도: {current_task['difficulty']})\n"
                "(구체적인 문제 데이터 없음)"
            )
        else:
            problem_info = "(문제 데이터 없음 — 일반적인 학습 막힘 상황)"

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"세그먼트: {segment.value}\n\n"
        f"{problem_info}\n\n"
        "이 학생이 막혔을 만한 원인 3~4가지를 선택지로 만들어주세요."
    )

    llm_with_tools = llm.bind_tools([send_causes])
    response = llm_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    return _parse_turn1_response(response)


def _build_coaching(
    state: ChatState,
    problem: dict,
    cause_label: str,
    llm,
) -> list[ResponseMessage]:
    """Turn 2: 선택한 원인에 맞는 코칭을 도구를 사용해 제공."""
    segment = state["segment"]
    grade_group = state["grade_group"]
    profile = state["student_profile"]

    problem_info = ""
    if problem:
        problem_info = (
            f"문제: {problem.get('question', '')}\n"
            f"정답: {problem.get('answer', '')}\n"
            f"설명: {problem.get('explanation', '')}"
        )

    system_prompt = (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        "학생이 막힌 원인을 선택했습니다. 이 원인에 맞게 학생을 도와주세요.\n"
        "적절한 도구를 골라 응답하세요:\n"
        "- send_text: 일반 코칭 텍스트\n"
        "- send_hint_card: 단계별 힌트가 효과적일 때\n"
        "- send_image_card: 그림/시각 자료로 설명할 때\n"
        "하나 또는 두 개의 도구를 사용하세요."
    )

    user_message = (
        f"학생: {profile['name']} ({profile['grade']}학년)\n"
        f"학생이 선택한 막힌 원인: '{cause_label}'\n\n"
        f"{problem_info}\n\n"
        "이 원인에 맞는 도움을 제공해주세요."
    )

    llm_with_tools = llm.bind_tools([send_text, send_hint_card, send_image_card])
    response = llm_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    return _parse_turn2_response(response)


def _parse_turn1_response(response) -> list[ResponseMessage]:
    """Turn 1 응답에서 choices 메시지를 추출."""
    for tc in getattr(response, "tool_calls", []):
        if tc["name"] == "send_causes":
            raw_items = tc["args"].get("items", [])
            try:
                choices = [(item["id"], item["label"]) for item in raw_items if "id" in item and "label" in item]
                if choices:
                    return [make_choices(choices)]
            except (TypeError, KeyError):
                pass

    # 폴백: LLM이 도구를 사용하지 않은 경우
    content = getattr(response, "content", "") or "어느 부분이 어려웠나요?"
    return [make_text(content)]


def _parse_turn2_response(response) -> list[ResponseMessage]:
    """Turn 2 응답에서 메시지들을 추출."""
    messages: list[ResponseMessage] = []

    for tc in getattr(response, "tool_calls", []):
        name = tc["name"]
        args = tc["args"]

        if name == "send_text":
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

    # 폴백: 도구 미사용
    if not messages:
        content = getattr(response, "content", "") or "함께 풀어봐요!"
        messages.append(make_text(content))

    return messages
