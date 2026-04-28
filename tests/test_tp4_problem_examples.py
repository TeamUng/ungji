from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import ChoicesMessage, HintCardMessage, TextMessage
from app.services.nodes.tp4 import tp4


def _make_math_problem_state(make_chat_state, case2_student, cause: str | None = None):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    assert state["current_task"] is not None
    state["current_task"] = {
        **state["current_task"],
        "problem_id": "math_ratio_saltwater_001",
    }
    if cause:
        state["chat_history"] = [HumanMessage(content=cause)]
    return state


def test_tp4_generates_problem_based_cause_choices(
    make_chat_state,
    case2_student,
    mock_llm,
):
    mock_llm.response_content = json.dumps(
        {
            "coach_text": "어디가 막혔는지 먼저 골라볼까요?",
            "choices": [
                {
                    "id": "dont_understand_question",
                    "label": "문제 말이 무슨 뜻인지 모르겠어요",
                },
                {
                    "id": "confused_what_to_divide",
                    "label": "무엇을 무엇으로 나누는지 헷갈려요",
                },
                {
                    "id": "hard_to_calculate_decimal",
                    "label": "소수로 계산하는 게 어려워요",
                },
            ],
        },
        ensure_ascii=False,
    )
    state = _make_math_problem_state(make_chat_state, case2_student)

    result = tp4(state)
    messages = result["tp4_response"]

    assert isinstance(messages[0], TextMessage)
    choices = next(message for message in messages if isinstance(message, ChoicesMessage))
    assert [item.id for item in choices.items] == [
        "dont_understand_question",
        "confused_what_to_divide",
        "hard_to_calculate_decimal",
    ]
    assert "무엇을 무엇으로 나누는지" in choices.items[1].label

    llm_messages = mock_llm.calls[0]["messages"]
    prompt_text = "\n".join(message.content for message in llm_messages)
    assert "소금 37g" in prompt_text
    assert "37 ÷ 148 = 0.25" in prompt_text


def test_tp4_generates_problem_based_hint_steps_after_dynamic_choice(
    make_chat_state,
    case2_student,
    mock_llm,
):
    mock_llm.response_content = json.dumps(
        {
            "coach_text": "좋아요. 이 문제는 전체 소금물 중 소금이 얼마나 있는지 보는 문제예요.",
            "hint_steps": [
                "(가)에서 소금은 37g, 소금물은 148g이에요.",
                "소금의 양을 소금물의 양으로 나누면 비율을 구할 수 있어요.",
                "그래서 (가)는 37 ÷ 148부터 계산해요.",
            ],
        },
        ensure_ascii=False,
    )
    state = _make_math_problem_state(
        make_chat_state,
        case2_student,
        cause="confused_what_to_divide",
    )

    result = tp4(state)
    messages = result["tp4_response"]

    assert isinstance(messages[0], TextMessage)
    hint_card = next(message for message in messages if isinstance(message, HintCardMessage))
    assert hint_card.steps[0].content == "(가)에서 소금은 37g, 소금물은 148g이에요."
    assert "37 ÷ 148" in hint_card.steps[2].content
    assert isinstance(messages[-1], TextMessage)
    assert "본인 말" in messages[-1].content
