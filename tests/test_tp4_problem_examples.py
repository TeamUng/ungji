from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import ChoicesMessage, HintCardMessage, TextMessage
from app.services.nodes.tp4 import tp4


def _make_turn1_problem_state(make_chat_state, case2_student):
    """Turn 1: chat_history에 실제 problem_id 포함."""
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    state["chat_history"] = [HumanMessage(content="math_ratio_saltwater_001")]
    return state


def test_tp4_problem_content_in_llm_prompt(make_chat_state, case2_student, mock_llm):
    """문제 데이터가 LLM에게 전달되는 프롬프트에 포함되는지 확인한다."""
    mock_llm.next_tool_calls = [
        {
            "name": "send_causes",
            "args": {
                "items": [
                    {"id": "dont_understand_question", "label": "문제 말이 무슨 뜻인지 모르겠어요"},
                    {"id": "confused_what_to_divide", "label": "무엇을 무엇으로 나누는지 헷갈려요"},
                    {"id": "hard_to_calculate_decimal", "label": "소수로 계산하는 게 어려워요"},
                ]
            },
        }
    ]
    state = _make_turn1_problem_state(make_chat_state, case2_student)
    tp4(state)

    llm_messages = mock_llm.calls[0]["messages"]
    prompt_text = "\n".join(m.content for m in llm_messages)
    # Turn 1 프롬프트에는 question 필드가 포함된다
    assert "소금 37g" in prompt_text
    assert "148g" in prompt_text


def test_tp4_generates_choices_from_send_causes_tool(
    make_chat_state, case2_student, mock_llm
):
    """send_causes 도구 응답이 올바른 ChoicesMessage를 생성한다."""
    items = [
        {"id": "dont_understand_question", "label": "문제 말이 무슨 뜻인지 모르겠어요"},
        {"id": "confused_what_to_divide", "label": "무엇을 무엇으로 나누는지 헷갈려요"},
        {"id": "hard_to_calculate_decimal", "label": "소수로 계산하는 게 어려워요"},
    ]
    mock_llm.next_tool_calls = [{"name": "send_causes", "args": {"items": items}}]
    state = _make_turn1_problem_state(make_chat_state, case2_student)

    result = tp4(state)
    messages = result["tp4_response"]

    choices = next(m for m in messages if isinstance(m, ChoicesMessage))
    assert [item.id for item in choices.items] == [
        "dont_understand_question",
        "confused_what_to_divide",
        "hard_to_calculate_decimal",
    ]
    assert "무엇을 무엇으로 나누는지" in choices.items[1].label


def test_tp4_turn2_hint_card_after_dynamic_choice(
    make_chat_state, case2_student, mock_llm
):
    """Turn 2: send_hint_card 도구 응답이 올바른 HintCardMessage를 생성한다."""
    from app.data.loader import load_problem

    steps = [
        "(가)에서 소금은 37g, 소금물은 148g이에요.",
        "소금의 양을 소금물의 양으로 나누면 비율을 구할 수 있어요.",
        "그래서 (가)는 37 ÷ 148부터 계산해요.",
    ]
    mock_llm.next_tool_calls = [{"name": "send_hint_card", "args": {"steps": steps}}]

    problem_data = dict(load_problem("math_ratio_saltwater_001"))
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    state["current_problem"] = problem_data
    state["chat_history"] = [HumanMessage(content="confused_what_to_divide")]

    result = tp4(state)
    messages = result["tp4_response"]

    hint_card = next(m for m in messages if isinstance(m, HintCardMessage))
    assert hint_card.steps[0].content == "(가)에서 소금은 37g, 소금물은 148g이에요."
    assert "37 ÷ 148" in hint_card.steps[2].content
