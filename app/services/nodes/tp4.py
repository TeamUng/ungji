from __future__ import annotations

import json
from typing import Any

from app.core.enums import GradeGroup, Segment, Subject, Touchpoint
from app.core.logging import get_logger
from app.data.loader import ProblemRecord, load_problem
from app.schemas.chat import (
    ChatState,
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    ResponseMessage,
    TextMessage,
)
from app.services.nodes.common import (
    CHOICE_ID_PATTERN,
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
    problem = _get_current_problem(state)

    if cause is None:
        if problem is None:
            messages = build_placeholder_messages(segment, grade_group, Touchpoint.TP4)
        else:
            messages = _build_problem_cause_choices(state, problem)
    else:
        messages = _build_coaching_response(state, cause, problem)

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
        if content in _ALL_CAUSES or CHOICE_ID_PATTERN.fullmatch(content):
            return content

    return None


def _get_current_problem(state: ChatState) -> ProblemRecord | None:
    current_task = state.get("current_task")
    if not current_task:
        return None

    problem_id = current_task.get("problem_id")
    if not problem_id:
        return None

    try:
        return load_problem(problem_id)
    except KeyError:
        logger.warning(
            "TP4 문제 데이터를 찾을 수 없어 기본 코칭으로 fallback",
            extra={"problem_id": problem_id, "student_id": state["student_id"]},
        )
        return None


def _build_problem_cause_choices(
    state: ChatState,
    problem: ProblemRecord,
) -> list[ResponseMessage]:
    system_prompt = _build_problem_system_prompt(
        state=state,
        problem=problem,
        purpose="막힘 원인 선택지 생성",
    )
    user_prompt = (
        "학생이 문제 풀이 중 챗봇 도움 버튼을 눌렀습니다.\n"
        "학생이 직접 고를 수 있도록, 이 문제에서 막혔을 만한 지점을 3~4개 선택지로 만들어주세요.\n"
        "반드시 JSON 객체만 반환하세요.\n\n"
        "형식:\n"
        "{\n"
        '  "coach_text": "학생에게 보여줄 짧은 안내 문장",\n'
        '  "choices": [\n'
        '    {"id": "stable_snake_case", "label": "학생에게 보일 선택지"}\n'
        "  ]\n"
        "}\n"
    )
    payload = _invoke_json_llm(system_prompt, user_prompt)

    coach_text = _clean_text(
        payload.get("coach_text"),
        "어디가 막혔는지 먼저 골라볼까요?",
    )
    choices = _normalize_choices(payload.get("choices")) or _fallback_cause_choices(problem)

    return [make_text(coach_text), make_choices(choices)]


def _build_coaching_response(
    state: ChatState,
    cause: str,
    problem: ProblemRecord | None,
) -> list[ResponseMessage]:
    segment = state["segment"]
    grade_group = state["grade_group"]

    if problem is not None:
        messages = _build_problem_coaching_response(state, cause, problem)
    else:
        system_prompt = _build_system_prompt(segment, grade_group, cause)
        llm_text = _invoke_llm(system_prompt, _CAUSE_USER_PROMPT.get(cause, "도움이 필요해요."))
        messages = _assemble_messages(cause, llm_text, state)

    if _should_append_teach_back(state, cause, problem):
        messages.append(_make_teach_back_prompt(grade_group))

    return messages


def _build_problem_coaching_response(
    state: ChatState,
    cause: str,
    problem: ProblemRecord,
) -> list[ResponseMessage]:
    system_prompt = _build_problem_system_prompt(
        state=state,
        problem=problem,
        purpose="선택한 막힘 원인에 따른 단계별 코칭",
    )
    user_prompt = (
        f"학생이 선택한 막힘 원인 ID: {cause}\n\n"
        "해설지를 근거로 학생이 스스로 풀 수 있게 도와주세요.\n"
        "정답을 바로 말하지 말고, 작은 단위 힌트부터 제시하세요.\n"
        "반드시 JSON 객체만 반환하세요.\n\n"
        "형식:\n"
        "{\n"
        '  "coach_text": "학생에게 보여줄 설명",\n'
        '  "hint_steps": ["첫 번째 힌트", "두 번째 힌트"]\n'
        "}\n"
    )
    payload = _invoke_json_llm(system_prompt, user_prompt)

    coach_text = _clean_text(
        payload.get("coach_text"),
        "좋아요. 문제에서 필요한 정보부터 하나씩 확인해봐요.",
    )
    hint_steps = _normalize_steps(payload.get("hint_steps")) or _fallback_hint_steps(problem)

    return [make_text(coach_text), make_hint_card(hint_steps)]


def _build_system_prompt(segment: Segment, grade_group: GradeGroup, cause: str) -> str:
    persona = get_persona(grade_group)
    strategy = get_coaching_strategy(segment)
    cause_context = _CAUSE_CONTEXT.get(cause, "")
    return f"{persona}\n\n{strategy}\n\n현재 상황: {cause_context}"


def _build_problem_system_prompt(
    state: ChatState,
    problem: ProblemRecord,
    purpose: str,
) -> str:
    persona = get_persona(state["grade_group"])
    strategy = get_coaching_strategy(state["segment"])
    return (
        f"{persona}\n\n"
        f"{strategy}\n\n"
        f"작업 목적: {purpose}\n"
        "내부 세그먼트명은 학생에게 절대 노출하지 마세요.\n"
        "학생에게는 쉽고 자연스러운 표현만 보여주세요.\n"
        "정답을 바로 노출하지 말고, 해설지를 근거로 단계적으로 유도하세요.\n\n"
        "[문제 데이터]\n"
        f"과목: {problem['subject']}\n"
        f"단원: {problem['unit']}\n"
        f"문제: {problem['question']}\n"
        f"정답: {problem['answer']}\n"
        f"해설: {problem['explanation']}\n"
    )


def _invoke_llm(system_prompt: str, user_context: str) -> str:
    from app.clients.upstage import llm
    from langchain_core.messages import HumanMessage, SystemMessage

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_context)])
    return response.content


def _invoke_json_llm(system_prompt: str, user_context: str) -> dict[str, Any]:
    raw_content = _invoke_llm(system_prompt, user_context)
    try:
        return _parse_json_object(raw_content)
    except ValueError:
        logger.warning("TP4 LLM JSON 파싱 실패, fallback 사용")
        return {}


def _parse_json_object(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()
    if not content:
        raise ValueError("empty LLM response")

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise ValueError("LLM response does not contain a JSON object")

    parsed = json.loads(content[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response must be an object")
    return parsed


def _normalize_choices(value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        return []

    choices: list[tuple[str, str]] = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        choice_id = str(item.get("id", "")).strip()
        label = str(item.get("label", "")).strip()
        if not choice_id or not label:
            continue
        if not CHOICE_ID_PATTERN.fullmatch(choice_id):
            continue
        choices.append((choice_id, label))

    return choices


def _normalize_steps(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    steps: list[str] = []
    for item in value[:5]:
        content = str(item).strip()
        if content:
            steps.append(content)
    return steps


def _clean_text(value: Any, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    return value or fallback


def _fallback_cause_choices(problem: ProblemRecord) -> list[tuple[str, str]]:
    if problem["subject"] == Subject.MATH.value:
        return [
            ("dont_understand_question", "문제 말이 무슨 뜻인지 모르겠어요"),
            ("confused_what_to_divide", "무엇을 무엇으로 나누는지 헷갈려요"),
            ("hard_to_build_expression", "식을 어떻게 세우는지 모르겠어요"),
            ("hard_to_calculate_decimal", "계산해서 답으로 쓰는 게 어려워요"),
        ]

    return [
        ("dont_understand_question", "문제 말이 무슨 뜻인지 모르겠어요"),
        ("dont_know_first_step", "처음에 뭘 해야 할지 모르겠어요"),
        ("confused_concept", "중요한 말이 헷갈려요"),
        ("want_smaller_step", "더 작게 나눠서 보고 싶어요"),
    ]


def _fallback_hint_steps(problem: ProblemRecord) -> list[str]:
    if problem.get("hints"):
        return problem["hints"][:3]
    if problem.get("steps"):
        return problem["steps"][:3]
    return [
        "문제에서 구하라고 한 것을 먼저 찾아요.",
        "해설에서 첫 번째로 확인한 조건을 다시 봐요.",
        "그 조건을 이용해 식이나 답의 시작 부분을 만들어봐요.",
    ]


_CONTEXTUAL_HINT_FALLBACK = [
    "문제에서 전체(기준)가 되는 양을 찾아요.",
    "비교하는 양이 전체 중 얼마인지 확인해요.",
    "비율 = 비교하는 양 ÷ 기준량 식을 써요.",
]


def _generate_contextual_hint_steps(state: ChatState) -> list[str]:
    """문제 ID가 없는 기존 경로에서도 태스크 맥락 기반 힌트를 생성한다."""

    current_task = state.get("current_task")
    task_context = (
        f"과목: {current_task['subject']}, 단원: {current_task['unit']}"
        if current_task
        else "수학 식 세우기"
    )
    system_prompt = _build_system_prompt(
        state["segment"],
        state["grade_group"],
        "build_expression",
    )
    user_prompt = (
        f"{task_context}\n"
        "학생이 식을 어떻게 세우는지 모르겠다고 했습니다. "
        "이 태스크에서 식을 세우는 방법을 3~4단계로 나눠주세요. "
        "각 단계는 한 문장으로 쓰고, 번호 없이 줄바꿈으로 구분하세요."
    )

    try:
        raw_steps = _invoke_llm(system_prompt, user_prompt)
        steps = [step.strip() for step in raw_steps.splitlines() if step.strip()]
        if len(steps) >= 2:
            return steps[:4]
    except Exception:
        logger.warning(
            "TP4 태스크 맥락 힌트 생성 실패, fallback 사용",
            extra={"task_context": task_context},
        )

    return _CONTEXTUAL_HINT_FALLBACK


def _should_append_teach_back(
    state: ChatState,
    cause: str,
    problem: ProblemRecord | None,
) -> bool:
    if state["segment"] != Segment.LOW_DILIGENT:
        return False

    if cause in _MATH_CAUSES:
        return True

    if problem is not None and problem["subject"] == Subject.MATH.value:
        return True

    current_task = state.get("current_task")
    if current_task is not None and current_task.get("subject") == Subject.MATH.value:
        return True

    return False


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
        # 식 세우기 막힘 → 문제 ID가 없어도 태스크 맥락 기반 단계 힌트 생성
        hint_steps = _generate_contextual_hint_steps(state)
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
