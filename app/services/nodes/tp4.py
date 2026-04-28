from __future__ import annotations

from app.core.enums import GradeGroup, Segment, Subject, Touchpoint
from app.core.logging import get_logger
from app.schemas.chat import (
    ChatState,
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    ResponseMessage,
    TextMessage,
)
from app.services.nodes.common import (
    build_placeholder_messages,
    make_choices,
    make_hint_card,
    make_image_card,
    make_text,
)
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

logger = get_logger(__name__)

# ─── 알려진 원인 ID 집합 ─────────────────────────────────────────────────────

_KOREAN_CAUSES = {"too_long", "dont_get_situation", "dont_get_feeling", "dont_want_now"}
_MATH_CAUSES = {"confused_concept", "find_compare_numbers", "build_expression", "check_calculation"}
_ALL_CAUSES = _KOREAN_CAUSES | _MATH_CAUSES


def tp4(state: ChatState) -> dict:
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

    cause = _get_selected_cause(state)

    if cause is None:
        messages = build_placeholder_messages(segment, grade_group, Touchpoint.TP4)
    else:
        messages = _build_coaching_response(state, cause)

    logger.info(
        "tp4 노드 완료",
        extra={
            "student_id": state["student_id"],
            "cause": cause,
            "message_types": [type(m).__name__ for m in messages],
        },
    )

    return {"tp4_response": messages}


# ─── 내부 헬퍼 ───────────────────────────────────────────────────────────────

def _get_selected_cause(state: ChatState) -> str | None:
    chat_history = state.get("chat_history", [])
    if not chat_history:
        return None

    last = chat_history[-1]
    # langchain HumanMessage: .type == "human"
    if getattr(last, "type", None) == "human":
        content = getattr(last, "content", "").strip()
        if content in _ALL_CAUSES:
            return content

    return None


def _build_coaching_response(state: ChatState, cause: str) -> list[ResponseMessage]:
    segment = state["segment"]
    grade_group = state["grade_group"]

    system_prompt = _build_system_prompt(segment, grade_group, cause)
    llm_text = _invoke_llm(system_prompt, cause)

    messages: list[ResponseMessage] = _assemble_messages(cause, llm_text, state)

    # 수학+성실 세그먼트: teach-back 유도 메시지 추가
    if cause in _MATH_CAUSES and segment == Segment.LOW_DILIGENT:
        messages.append(_make_teach_back_prompt(grade_group))

    return messages


def _build_system_prompt(segment: Segment, grade_group: GradeGroup, cause: str) -> str:
    persona = get_persona(grade_group)
    strategy = get_coaching_strategy(segment)
    cause_context = _CAUSE_CONTEXT.get(cause, "")
    return f"{persona}\n\n{strategy}\n\n현재 상황: {cause_context}"


def _invoke_llm(system_prompt: str, cause: str) -> str:
    from app.clients.upstage import llm
    from langchain_core.messages import HumanMessage, SystemMessage

    user_context = _CAUSE_USER_PROMPT.get(cause, "도움이 필요해요.")
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_context)])
    return response.content


def _assemble_messages(cause: str, llm_text: str, state: ChatState) -> list[ResponseMessage]:
    """원인별로 고정된 메시지 타입 구조에 LLM 텍스트를 채운다."""

    if cause == "too_long":
        # 문장 분리 전략 → TextMessage
        return [make_text(llm_text)]

    if cause == "dont_get_situation":
        # 상황 이해 막힘 → TextMessage + ImageCardMessage
        return [
            make_text(llm_text),
            make_image_card(
                image_url="https://placeholder.invalid/situation_card",
                caption="글 속 상황을 그림으로 살펴봐",
            ),
        ]

    if cause == "dont_get_feeling":
        # 감정 이해 막힘 → TextMessage + ChoicesMessage (감정 좁히기)
        feeling_choices = [
            ("happy_excited", "신나고 기쁜 느낌"),
            ("sad_scared", "슬프거나 무서운 느낌"),
            ("angry_upset", "화나거나 억울한 느낌"),
            ("confused_unsure", "헷갈리고 모르겠는 느낌"),
        ]
        return [make_text(llm_text), make_choices(feeling_choices)]

    if cause == "dont_want_now":
        # 동기 없음 → 초소형 목표 TextMessage
        return [make_text(llm_text)]

    if cause == "confused_concept":
        # 개념 혼동 → 비유 설명 TextMessage
        return [make_text(llm_text)]

    if cause == "find_compare_numbers":
        # 기준량/비교량 혼동 → TextMessage
        return [make_text(llm_text)]

    if cause == "build_expression":
        # 식 세우기 막힘 → TextMessage + HintCardMessage
        hint_steps = [
            "무엇을 전체(기준)로 볼지 먼저 정해요.",
            "비교하는 양이 전체 중 얼마인지 찾아요.",
            "비율 = 비교하는 양 ÷ 기준량 식을 써요.",
        ]
        return [make_text(llm_text), make_hint_card(hint_steps)]

    if cause == "check_calculation":
        # 계산 오류 → 검산 유도 TextMessage
        return [make_text(llm_text)]

    # 예상하지 못한 cause는 기본 텍스트 응답
    return [make_text(llm_text)]


def _make_teach_back_prompt(grade_group: GradeGroup) -> TextMessage:
    prompts = {
        GradeGroup.LOWER: "이제 네가 한 번 설명해줄 수 있어?",
        GradeGroup.MIDDLE: "이제 네 말로 한 번 설명해볼 수 있어?",
        GradeGroup.UPPER: "이제 방금 푼 방법을 본인 말로 한 번 설명해볼 수 있어요?",
    }
    return make_text(prompts.get(grade_group, "이제 네 말로 설명해볼까요?"))


# ─── 원인별 컨텍스트·프롬프트 ────────────────────────────────────────────────

_CAUSE_CONTEXT: dict[str, str] = {
    "too_long": "학생이 글이 너무 길어서 읽기 어렵다고 했어. 문장을 짧게 나눠 읽는 방법을 알려줘.",
    "dont_get_situation": "학생이 글 속 상황이 무슨 상황인지 모르겠다고 했어. 상황을 그림처럼 떠올리도록 도와줘.",
    "dont_get_feeling": "학생이 주인공의 마음을 모르겠다고 했어. 감정을 좁혀가는 선택지로 유도해줘.",
    "dont_want_now": "학생이 지금 하기 싫다고 했어. 아주 작은 한 가지 목표만 제시해줘.",
    "confused_concept": "학생이 비율 개념이 헷갈린다고 했어. 일상 속 비유로 쉽게 설명해줘.",
    "find_compare_numbers": "학생이 어떤 수끼리 비교해야 할지 모르겠다고 했어. 기준량과 비교량을 찾는 방법을 유도해줘.",
    "build_expression": "학생이 식을 어떻게 세우는지 모르겠다고 했어. 단계별 힌트로 식 세우기를 도와줘.",
    "check_calculation": "학생이 계산하다가 틀렸다고 했어. 검산 방법을 단계적으로 유도해줘.",
}

_CAUSE_USER_PROMPT: dict[str, str] = {
    "too_long": "글이 너무 길어서 어떻게 읽어야 할지 모르겠어요.",
    "dont_get_situation": "무슨 상황인지 잘 모르겠어요.",
    "dont_get_feeling": "주인공이 어떤 마음인지 모르겠어요.",
    "dont_want_now": "지금 하기 싫어요.",
    "confused_concept": "비율이 무슨 뜻인지 헷갈려요.",
    "find_compare_numbers": "어떤 수끼리 비교해야 할지 모르겠어요.",
    "build_expression": "식을 어떻게 세우는지 모르겠어요.",
    "check_calculation": "계산하다가 틀렸어요.",
}
