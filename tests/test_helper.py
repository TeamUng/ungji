from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import (
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    TextMessage,
)
from app.services.nodes.helper import helper


def _has_type(messages, message_type) -> bool:
    return any(isinstance(message, message_type) for message in messages)


def _make_turn1_state(make_chat_state, student, segment, grade_group, problem_id: str | None = None):
    state = make_chat_state(
        student,
        segment=segment,
        grade_group=grade_group,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    if problem_id:
        state["chat_history"] = [HumanMessage(content=problem_id)]
    return state


def _make_turn2_state(make_chat_state, student, segment, grade_group, cause: str, problem: dict):
    state = make_chat_state(
        student,
        segment=segment,
        grade_group=grade_group,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    state["current_problem"] = problem
    state["chat_history"] = [HumanMessage(content=cause)]
    return state


_DUMMY_PROBLEM = {
    "problem_id": "test_001",
    "subject": "수학",
    "unit": "분수",
    "question": "1/2 + 1/4 = ?",
    "answer": "3/4",
    "explanation": "분모를 통분합니다.",
}

_CAUSES_TOOL_CALL = [
    {
        "name": "send_causes",
        "args": {
            "items": [
                {"id": "no_concept", "label": "개념을 잘 모르겠어요"},
                {"id": "hard_calc", "label": "계산이 어려워요"},
                {"id": "confused_question", "label": "문제가 이해 안 돼요"},
            ]
        },
    }
]


class TestHelperTurn1:
    def test_send_causes_tool_produces_choices_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = helper(state)

        assert _has_type(result["helper_response"], ChoicesMessage)

    def test_choices_have_correct_ids(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = helper(state)

        choices = next(message for message in result["helper_response"] if isinstance(message, ChoicesMessage))
        ids = [item.id for item in choices.items]
        assert ids == ["no_concept", "hard_calc", "confused_question"]

    def test_fallback_text_when_no_tool_call(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = []
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

    def test_result_includes_current_problem_key(self, make_chat_state, case2_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
            problem_id="math_ratio_saltwater_001",
        )
        result = helper(state)

        assert "current_problem" in result
        assert result["current_problem"].get("problem_id") == "math_ratio_saltwater_001"

    def test_unknown_problem_id_still_generates_causes(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
            problem_id="nonexistent_id",
        )
        result = helper(state)

        assert "helper_response" in result
        assert _has_type(result["helper_response"], ChoicesMessage)


class TestHelperTurn2:
    def test_send_text_produces_text_message(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "개념부터 같이 볼까요?"}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
            cause="no_concept",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

    def test_send_hint_card_produces_hint_card_message(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_hint_card", "args": {"steps": ["1단계", "2단계", "3단계"]}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
            cause="hard_calc",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        assert _has_type(result["helper_response"], HintCardMessage)

    def test_send_image_card_produces_image_card_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_image_card", "args": {"caption": "분수 그림 설명"}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
            cause="confused_question",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        assert _has_type(result["helper_response"], ImageCardMessage)

    def test_multiple_tools_produces_multiple_messages(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "같이 생각해볼까요?"}},
            {"name": "send_hint_card", "args": {"steps": ["1단계", "2단계"]}},
        ]
        state = _make_turn2_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
            cause="no_concept",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        messages = result["helper_response"]
        assert _has_type(messages, TextMessage)
        assert _has_type(messages, HintCardMessage)

    def test_fallback_text_when_no_tool_call(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = []
        mock_llm.response_content = "함께 생각해볼까요?"
        state = _make_turn2_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
            cause="no_concept",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

    def test_hint_card_steps_content(self, make_chat_state, case2_student, mock_llm):
        steps = ["기준량을 확인해요.", "비교하는 양을 찾아요.", "식을 세워요."]
        mock_llm.next_tool_calls = [
            {"name": "send_hint_card", "args": {"steps": steps}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
            cause="hard_calc",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        hint_card = next(message for message in result["helper_response"] if isinstance(message, HintCardMessage))
        contents = [step.content for step in hint_card.steps]
        assert "기준량을 확인해요." in contents
        assert "식을 세워요." in contents

    def test_turn2_does_not_include_current_problem_in_result(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "잘하고 있어요"}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
            cause="no_concept",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        assert "current_problem" not in result


class TestHelperSegmentNotExposed:
    def test_turn1_causes_no_segment_exposed(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = helper(state)

        for message in result["helper_response"]:
            if isinstance(message, TextMessage):
                assert "LOW_LAZY" not in message.content
            elif isinstance(message, ChoicesMessage):
                assert all("LOW_LAZY" not in item.label for item in message.items)

    def test_turn2_coaching_no_segment_exposed(self, make_chat_state, case2_student, mock_llm):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "잘하고 있어요"}}
        ]
        state = _make_turn2_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
            cause="no_concept",
            problem=_DUMMY_PROBLEM,
        )
        result = helper(state)

        text = next(message.content for message in result["helper_response"] if isinstance(message, TextMessage))
        assert "LOW_DILIGENT" not in text
        assert Segment.LOW_DILIGENT.value not in text
