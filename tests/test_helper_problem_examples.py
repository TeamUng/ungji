from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import ChoicesMessage, HintCardMessage
from app.services.nodes.helper import helper


def _make_turn1_problem_state(make_chat_state, case2_student):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    state["chat_history"] = [HumanMessage(content="math_ratio_saltwater_001")]
    return state


def test_helper_problem_content_in_llm_prompt(make_chat_state, case2_student, mock_llm):
    mock_llm.next_tool_calls = [
        {
            "name": "send_causes",
            "args": {
                "items": [
                    {"id": "dont_understand_question", "label": "문제가 무슨 말인지 모르겠어요"},
                    {"id": "confused_what_to_divide", "label": "무엇으로 나눌지 헷갈려요"},
                    {"id": "hard_to_calculate_decimal", "label": "소수 계산이 어려워요"},
                ]
            },
        }
    ]
    state = _make_turn1_problem_state(make_chat_state, case2_student)
    helper(state)

    prompt_text = "\n".join(message.content for message in mock_llm.calls[0]["messages"])
    assert "37" in prompt_text
    assert "148" in prompt_text


def test_helper_generates_choices_from_send_causes_tool(
    make_chat_state, case2_student, mock_llm
):
    items = [
        {"id": "dont_understand_question", "label": "문제가 무슨 말인지 모르겠어요"},
        {"id": "confused_what_to_divide", "label": "무엇으로 나눌지 헷갈려요"},
        {"id": "hard_to_calculate_decimal", "label": "소수 계산이 어려워요"},
    ]
    mock_llm.next_tool_calls = [{"name": "send_causes", "args": {"items": items}}]
    state = _make_turn1_problem_state(make_chat_state, case2_student)

    result = helper(state)
    messages = result["helper_response"]

    choices = next(message for message in messages if isinstance(message, ChoicesMessage))
    assert [item.id for item in choices.items] == [
        "dont_understand_question",
        "confused_what_to_divide",
        "hard_to_calculate_decimal",
    ]
    assert "무엇으로 나눌지" in choices.items[1].label


def test_helper_turn2_hint_card_after_dynamic_choice(
    make_chat_state, case2_student, mock_llm
):
    from app.data.loader import load_problem

    steps = [
        "(가)에서 소금은 37g, 소금물은 148g이에요.",
        "소금의 양을 소금물의 양으로 나누면 비율을 구할 수 있어요.",
        "그래서 37 ÷ 148부터 계산해요.",
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

    result = helper(state)
    messages = result["helper_response"]

    hint_card = next(message for message in messages if isinstance(message, HintCardMessage))
    assert hint_card.steps[0].content == "(가)에서 소금은 37g, 소금물은 148g이에요."
    assert "37 ÷ 148" in hint_card.steps[2].content
