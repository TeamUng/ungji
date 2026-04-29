from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import (
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    TextMessage,
)
from app.services.nodes.helper import TP4_PHASE_COACHING, helper


def _has_type(messages, message_type) -> bool:
    return any(isinstance(message, message_type) for message in messages)


def _make_tp4_state(make_chat_state, student, segment, grade_group):
    return make_chat_state(
        student,
        segment=segment,
        grade_group=grade_group,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )


_DUMMY_PROBLEM = {
    "problem_id": "test_001",
    "subject": "수학",
    "unit": "분수",
    "question": "1/2 + 1/4 = ?",
    "answer": "3/4",
    "explanation": "분모를 통분하면 됩니다.",
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


class TestHelperProblemStart:
    def test_send_causes_tool_produces_choices_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )

        result = helper(state)

        assert _has_type(result["helper_response"], ChoicesMessage)
        assert result["tp4_phase"] == TP4_PHASE_COACHING
        assert result["tp4_turn_count"] == 1

    def test_choices_have_correct_ids(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )

        result = helper(state)

        choices = next(message for message in result["helper_response"] if isinstance(message, ChoicesMessage))
        ids = [item.id for item in choices.items]
        assert ids == ["no_concept", "hard_calc", "confused_question"]

    def test_known_problem_id_is_loaded(self, make_chat_state, case2_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
        )
        state["chat_history"] = [HumanMessage(content="math_ratio_saltwater_001")]

        result = helper(state)

        assert result["current_problem"].get("problem_id") == "math_ratio_saltwater_001"
        assert result["tp4_phase"] == TP4_PHASE_COACHING

    def test_unknown_problem_id_still_lets_llm_coach(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
        )
        state["chat_history"] = [HumanMessage(content="nonexistent_id")]

        result = helper(state)

        assert result["current_problem"] == {}
        assert _has_type(result["helper_response"], ChoicesMessage)


class TestHelperCoachingConversation:
    def test_send_text_produces_text_message(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "좋아, 한 단계씩 같이 보자."}}
        ]
        state = _make_tp4_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["tp4_phase"] = TP4_PHASE_COACHING
        state["tp4_turn_count"] = 1
        state["chat_history"] = [HumanMessage(content="개념을 잘 모르겠어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)
        assert result["tp4_phase"] == TP4_PHASE_COACHING
        assert result["tp4_turn_count"] == 2
        assert "current_problem" not in result

    def test_send_hint_card_produces_hint_card_message(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_hint_card", "args": {"steps": ["기준량 찾기", "비교하는 양 찾기"]}}
        ]
        state = _make_tp4_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["chat_history"] = [HumanMessage(content="계산이 어려워요")]

        result = helper(state)

        assert _has_type(result["helper_response"], HintCardMessage)

    def test_send_image_card_produces_image_card_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_image_card", "args": {"caption": "분수 막대 그림"}}
        ]
        state = _make_tp4_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["chat_history"] = [HumanMessage(content="그림으로 보고 싶어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], ImageCardMessage)

    def test_multiple_tools_produce_multiple_messages(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "먼저 문제를 짧게 나눠보자."}},
            {"name": "send_hint_card", "args": {"steps": ["묻는 것 찾기", "숫자 찾기"]}},
        ]
        state = _make_tp4_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["chat_history"] = [HumanMessage(content="글이 너무 길어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)
        assert _has_type(result["helper_response"], HintCardMessage)

    def test_fallback_text_when_no_tool_call(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = []
        mock_llm.response_content = "좋아요, 한 단계씩 같이 생각해 볼까요?"
        state = _make_tp4_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["chat_history"] = [HumanMessage(content="아직 모르겠어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

    def test_prompt_treats_followup_as_agentic_conversation(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "좋아, 이번에는 숫자를 찾아보자."}}
        ]
        state = _make_tp4_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["tp4_phase"] = TP4_PHASE_COACHING
        state["tp4_turn_count"] = 2
        state["chat_history"] = [HumanMessage(content="어떤 숫자를 써야 하는지 모르겠어요")]

        helper(state)

        messages = mock_llm.calls[-1]["messages"]
        prompt_text = "\n".join(message.content for message in messages)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert "Helper의 책임" in messages[0].content
        assert "고정된 백엔드 분류값" in prompt_text
        assert "원인 선택지는" in prompt_text


class TestHelperSegmentNotExposed:
    def test_choices_do_not_expose_segment_name(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )

        result = helper(state)

        for message in result["helper_response"]:
            if isinstance(message, TextMessage):
                assert "LOW_LAZY" not in message.content
            elif isinstance(message, ChoicesMessage):
                assert all("LOW_LAZY" not in item.label for item in message.items)

    def test_coaching_does_not_expose_segment_name(self, make_chat_state, case2_student, mock_llm):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "잘 하고 있어요."}}
        ]
        state = _make_tp4_state(
            make_chat_state,
            case2_student,
            Segment.LOW_DILIGENT,
            GradeGroup.UPPER,
        )
        state["current_problem"] = _DUMMY_PROBLEM
        state["chat_history"] = [HumanMessage(content="no_concept")]

        result = helper(state)

        text = next(message.content for message in result["helper_response"] if isinstance(message, TextMessage))
        assert "LOW_DILIGENT" not in text
        assert Segment.LOW_DILIGENT.value not in text
