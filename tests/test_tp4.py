from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.schemas.chat import (
    ChoicesMessage,
    HintCardMessage,
    ImageCardMessage,
    TextMessage,
)
from app.services.nodes.tp4 import tp4


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────

def _has_type(messages, msg_type) -> bool:
    return any(isinstance(m, msg_type) for m in messages)


def _make_turn1_state(make_chat_state, student, segment, grade_group, problem_id: str | None = None):
    """Turn 1 상태: current_problem 미설정, chat_history에 선택적 problem_id."""
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
    """Turn 2 상태: current_problem 설정, chat_history에 선택한 원인."""
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
    "hints": ["분모를 같게 만들어요."],
    "steps": ["1/2 = 2/4로 통분해요.", "2/4 + 1/4 = 3/4를 계산해요."],
}

_CAUSES_TOOL_CALL = [
    {
        "name": "send_causes",
        "args": {
            "items": [
                {"id": "no_concept", "label": "개념을 모르겠어요"},
                {"id": "hard_calc", "label": "계산이 어려워요"},
                {"id": "confused_question", "label": "문제가 이해 안 돼요"},
            ]
        },
    }
]


# ─── Turn 1: 원인 선택지 생성 ─────────────────────────────────────────────────

class TestTp4Turn1:
    """Turn 1: current_problem이 없는 상태에서 원인 선택지를 생성한다."""

    def test_send_causes_tool_produces_choices_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], ChoicesMessage)

    def test_choices_have_correct_ids(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = tp4(state)

        choices = next(m for m in result["tp4_response"] if isinstance(m, ChoicesMessage))
        ids = [item.id for item in choices.items]
        assert "no_concept" in ids
        assert "hard_calc" in ids
        assert "confused_question" in ids

    def test_fallback_text_when_no_tool_call(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = []
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], TextMessage)

    def test_result_includes_current_problem_key(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            problem_id="math_ratio_saltwater_001",
        )
        result = tp4(state)

        assert "current_problem" in result

    def test_result_has_problem_data_for_known_problem_id(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            problem_id="math_ratio_saltwater_001",
        )
        result = tp4(state)

        problem = result.get("current_problem")
        assert problem is not None
        assert problem.get("problem_id") == "math_ratio_saltwater_001"

    def test_unknown_problem_id_still_generates_causes(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER,
            problem_id="nonexistent_id",
        )
        result = tp4(state)

        # 문제를 못 찾아도 원인 선택지는 생성된다
        assert "tp4_response" in result
        assert len(result["tp4_response"]) > 0


# ─── Turn 2: 원인에 맞는 코칭 ─────────────────────────────────────────────────

class TestTp4Turn2:
    """Turn 2: current_problem이 있는 상태에서 선택한 원인에 맞게 코칭한다."""

    def test_send_text_produces_text_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "개념부터 같이 복습해봐요!"}}
        ]
        state = _make_turn2_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER,
            cause="no_concept", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], TextMessage)

    def test_send_hint_card_produces_hint_card_message(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_hint_card", "args": {"steps": ["1단계", "2단계", "3단계"]}}
        ]
        state = _make_turn2_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            cause="hard_calc", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], HintCardMessage)

    def test_send_image_card_produces_image_card_message(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_image_card", "args": {"caption": "분수 그림 설명"}}
        ]
        state = _make_turn2_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER,
            cause="confused_question", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], ImageCardMessage)

    def test_multiple_tools_produces_multiple_messages(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "같이 풀어봐요."}},
            {"name": "send_hint_card", "args": {"steps": ["1단계", "2단계"]}},
        ]
        state = _make_turn2_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            cause="no_concept", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        messages = result["tp4_response"]
        assert _has_type(messages, TextMessage)
        assert _has_type(messages, HintCardMessage)

    def test_fallback_text_when_no_tool_call(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = []
        mock_llm.response_content = "함께 풀어봐요!"
        state = _make_turn2_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER,
            cause="no_concept", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        assert _has_type(result["tp4_response"], TextMessage)

    def test_turn2_does_not_include_current_problem_in_result(
        self, make_chat_state, case1_student, mock_llm
    ):
        """Turn 2 결과에는 current_problem이 포함되지 않는다 (이미 state에 저장됨)."""
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "잘 하고 있어요!"}}
        ]
        state = _make_turn2_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER,
            cause="no_concept", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        assert "current_problem" not in result

    def test_hint_card_steps_content(
        self, make_chat_state, case2_student, mock_llm
    ):
        steps = ["기준량을 확인해요.", "비교량을 찾아요.", "식을 써요."]
        mock_llm.next_tool_calls = [
            {"name": "send_hint_card", "args": {"steps": steps}}
        ]
        state = _make_turn2_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            cause="hard_calc", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)

        hint_card = next(m for m in result["tp4_response"] if isinstance(m, HintCardMessage))
        contents = [s.content for s in hint_card.steps]
        assert "기준량을 확인해요." in contents
        assert "식을 써요." in contents


# ─── 세그먼트명 노출 방지 ─────────────────────────────────────────────────────

class TestTp4SegmentNotExposed:
    """내부 세그먼트 식별자가 응답 메시지에 노출되지 않아야 한다."""

    INTERNAL_NAMES = ["LOW_LAZY", "LOW_DILIGENT", "HIGH_LAZY", "HIGH_DILIGENT",
                      "못함+불성실", "못함+성실", "잘함+불성실", "잘함+성실"]

    def _check_no_segment(self, messages):
        for m in messages:
            for name in self.INTERNAL_NAMES:
                if isinstance(m, TextMessage):
                    assert name not in m.content
                elif isinstance(m, ChoicesMessage):
                    for item in m.items:
                        assert name not in item.label
                elif isinstance(m, ImageCardMessage):
                    assert name not in m.caption
                elif isinstance(m, HintCardMessage):
                    for step in m.steps:
                        assert name not in step.content

    def test_turn1_causes_no_segment_exposed(
        self, make_chat_state, case1_student, mock_llm
    ):
        mock_llm.next_tool_calls = _CAUSES_TOOL_CALL
        state = _make_turn1_state(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER
        )
        result = tp4(state)
        self._check_no_segment(result["tp4_response"])

    def test_turn2_coaching_no_segment_exposed(
        self, make_chat_state, case2_student, mock_llm
    ):
        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "잘 하고 있어요!"}}
        ]
        state = _make_turn2_state(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER,
            cause="no_concept", problem=_DUMMY_PROBLEM,
        )
        result = tp4(state)
        self._check_no_segment(result["tp4_response"])
