from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import (
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    TextMessage,
)
from app.services.nodes.helper import TP4_PHASE_COACHING, helper


@pytest.fixture(autouse=True)
def allow_helper_input_guard(monkeypatch):
    monkeypatch.setattr(
        "app.services.nodes.helper.check_agent_input_sync",
        lambda input_text, state, *, agent_name: None,
    )


def _has_type(messages, message_type) -> bool:
    return any(isinstance(message, message_type) for message in messages)


def _first_agent_call_messages(mock_llm):
    for call in mock_llm.calls:
        messages = call["messages"]
        if (
            not call["kwargs"]
            and len(messages) >= 2
            and isinstance(messages[0], SystemMessage)
            and isinstance(messages[1], HumanMessage)
        ):
            return messages
    raise AssertionError("no helper LLM call found")


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

_TEXT_TOOL_CALL = [
    {"name": "send_text", "args": {"content": "next small coaching step"}}
]


class TestHelperProblemStart:
    def test_send_causes_tool_produces_choices_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        state["current_problem"] = _DUMMY_PROBLEM

        result = helper(state)

        assert _has_type(result["helper_response"], ChoicesMessage)
        assert result["tp4_phase"] == TP4_PHASE_COACHING
        assert result["tp4_turn_count"] == 1

    def test_choices_have_correct_ids(self, make_chat_state, case1_student, mock_llm):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        state["current_problem"] = _DUMMY_PROBLEM

        result = helper(state)

        choices = next(message for message in result["helper_response"] if isinstance(message, ChoicesMessage))
        ids = [item.id for item in choices.items]
        assert ids == ["no_concept", "hard_calc", "confused_question"]

    def test_known_problem_id_is_loaded(self, make_chat_state, case2_student, mock_llm, monkeypatch):
        def fail_if_called(*args, **kwargs):
            raise AssertionError("known problem ids should skip free-form input guard")

        monkeypatch.setattr("app.services.nodes.helper.check_agent_input_sync", fail_if_called)
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

    def test_unknown_problem_id_asks_for_problem(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _TEXT_TOOL_CALL
        state = _make_tp4_state(
            make_chat_state,
            case1_student,
            Segment.LOW_LAZY,
            GradeGroup.LOWER,
        )
        state["chat_history"] = [HumanMessage(content="nonexistent_id")]

        result = helper(state)

        assert result["current_problem"] == {}
        assert _has_type(result["helper_response"], TextMessage)


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
        state["tp4_turn_count"] = 1
        state["chat_history"] = [HumanMessage(content="계산이 어려워요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

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
        state["tp4_turn_count"] = 1
        state["chat_history"] = [HumanMessage(content="그림으로 보고 싶어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)

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
        state["tp4_turn_count"] = 1
        state["chat_history"] = [HumanMessage(content="글이 너무 길어요")]

        result = helper(state)

        assert _has_type(result["helper_response"], TextMessage)
        assert not _has_type(result["helper_response"], HintCardMessage)

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

        messages = _first_agent_call_messages(mock_llm)
        prompt_text = "\n".join(message.content for message in messages)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert "Helper의 책임" in messages[0].content
        assert "시스템이 먼저 확정한 helper decision" in prompt_text
        assert "intent: coach_next_step" in prompt_text
        assert "required_tool: send_text" in prompt_text


def test_unsafe_followup_blocks_without_advancing_tp4(
    make_chat_state, case2_student, mock_llm, monkeypatch
):
    monkeypatch.setattr(
        "app.services.nodes.helper.check_agent_input_sync",
        lambda input_text, state, *, agent_name: "blocked followup",
    )
    state = _make_tp4_state(
        make_chat_state,
        case2_student,
        Segment.LOW_DILIGENT,
        GradeGroup.UPPER,
    )
    state["current_problem"] = _DUMMY_PROBLEM
    state["tp4_turn_count"] = 2
    state["chat_history"] = [HumanMessage(content="unsafe followup")]

    result = helper(state)

    assert result["helper_response"][0].content == "blocked followup"
    assert "tp4_turn_count" not in result
    assert mock_llm.calls == []


def test_first_known_problem_decision_requires_send_causes(
    make_chat_state, case1_student, mock_llm
):
    mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
    state = _make_tp4_state(
        make_chat_state,
        case1_student,
        Segment.LOW_LAZY,
        GradeGroup.LOWER,
    )
    state["current_problem"] = _DUMMY_PROBLEM

    helper(state)

    prompt_text = "\n".join(message.content for message in _first_agent_call_messages(mock_llm))
    assert "intent: collect_stuck_cause" in prompt_text
    assert "required_tool: send_causes" in prompt_text
    assert "max_choices: 3" in prompt_text


def test_later_coaching_decision_requires_send_text(
    make_chat_state, case2_student, mock_llm
):
    mock_llm.next_tool_calls = _TEXT_TOOL_CALL
    state = _make_tp4_state(
        make_chat_state,
        case2_student,
        Segment.LOW_DILIGENT,
        GradeGroup.UPPER,
    )
    state["current_problem"] = _DUMMY_PROBLEM
    state["tp4_turn_count"] = 1
    state["chat_history"] = [HumanMessage(content="no_concept")]

    helper(state)

    prompt_text = "\n".join(message.content for message in _first_agent_call_messages(mock_llm))
    assert "intent: coach_next_step" in prompt_text
    assert "required_tool: send_text" in prompt_text


def test_wrong_helper_tool_triggers_one_repair_attempt(
    make_chat_state, case2_student, mock_llm, monkeypatch
):
    import app.services.nodes.helper as helper_module

    monkeypatch.setattr(
        helper_module,
        "guarded_invoke",
        lambda runnable, messages, state, **kwargs: runnable.invoke(messages),
    )
    mock_llm.queued_tool_calls = [
        [{"name": "send_hint_card", "args": {"steps": ["first"]}}],
        _TEXT_TOOL_CALL[0:1],
    ]
    state = _make_tp4_state(
        make_chat_state,
        case2_student,
        Segment.LOW_DILIGENT,
        GradeGroup.UPPER,
    )
    state["current_problem"] = _DUMMY_PROBLEM
    state["tp4_turn_count"] = 1
    state["chat_history"] = [HumanMessage(content="no_concept")]

    result = helper(state)

    assert _has_type(result["helper_response"], TextMessage)
    assert len(mock_llm.calls) == 2
    repair_message = mock_llm.calls[1]["messages"][-1].content
    assert "send_text" in repair_message


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
        state["tp4_turn_count"] = 1
        state["chat_history"] = [HumanMessage(content="no_concept")]

        result = helper(state)

        text = next(message.content for message in result["helper_response"] if isinstance(message, TextMessage))
        assert "LOW_DILIGENT" not in text
        assert Segment.LOW_DILIGENT.value not in text
