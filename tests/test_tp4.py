from __future__ import annotations

import pytest
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


def _state_with_cause(make_chat_state, student, segment, grade_group, cause: str | None):
    state = make_chat_state(
        student,
        segment=segment,
        grade_group=grade_group,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    if cause:
        state["chat_history"] = [HumanMessage(content=cause)]
    return state


# ─── 케이스 1 (국어, LOW_LAZY, LOWER) ────────────────────────────────────────

class TestTp4Case1Korean:
    """케이스 1: 저학년 국어, 못함+불성실 세그먼트"""

    def _make_state(self, make_chat_state, case1_student, cause: str | None):
        return _state_with_cause(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER, cause
        )

    def test_no_cause_returns_choices(self, make_chat_state, case1_student, mock_llm):
        state = self._make_state(make_chat_state, case1_student, None)
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)
        assert _has_type(messages, ChoicesMessage)

    def test_too_long_returns_text(self, make_chat_state, case1_student, mock_llm):
        state = self._make_state(make_chat_state, case1_student, "too_long")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)

    def test_dont_get_situation_returns_image_card(self, make_chat_state, case1_student, mock_llm):
        state = self._make_state(make_chat_state, case1_student, "dont_get_situation")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, ImageCardMessage)

    def test_dont_get_feeling_returns_choices(self, make_chat_state, case1_student, mock_llm):
        state = self._make_state(make_chat_state, case1_student, "dont_get_feeling")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, ChoicesMessage)

    def test_dont_want_now_returns_text(self, make_chat_state, case1_student, mock_llm):
        state = self._make_state(make_chat_state, case1_student, "dont_want_now")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)

    def test_no_teach_back_for_case1(self, make_chat_state, case1_student, mock_llm):
        # 국어(LOW_LAZY)는 teach-back을 추가하지 않는다
        state = self._make_state(make_chat_state, case1_student, "too_long")
        result = tp4(state)
        messages = result["tp4_response"]

        # LOW_LAZY는 teach-back 없음 → TextMessage 1개만
        assert len(messages) == 1


# ─── 케이스 2 (수학, LOW_DILIGENT, UPPER) ────────────────────────────────────

class TestTp4Case2Math:
    """케이스 2: 고학년 수학, 못함+성실 세그먼트"""

    def _make_state(self, make_chat_state, case2_student, cause: str | None):
        return _state_with_cause(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER, cause
        )

    def test_no_cause_returns_choices(self, make_chat_state, case2_student, mock_llm):
        state = self._make_state(make_chat_state, case2_student, None)
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)
        assert _has_type(messages, ChoicesMessage)

    def test_confused_concept_returns_text(self, make_chat_state, case2_student, mock_llm):
        state = self._make_state(make_chat_state, case2_student, "confused_concept")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)

    def test_find_compare_numbers_returns_text(self, make_chat_state, case2_student, mock_llm):
        state = self._make_state(make_chat_state, case2_student, "find_compare_numbers")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)

    def test_build_expression_returns_hint_card(self, make_chat_state, case2_student, mock_llm):
        state = self._make_state(make_chat_state, case2_student, "build_expression")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, HintCardMessage)

    def test_check_calculation_returns_text(self, make_chat_state, case2_student, mock_llm):
        state = self._make_state(make_chat_state, case2_student, "check_calculation")
        result = tp4(state)
        messages = result["tp4_response"]

        assert _has_type(messages, TextMessage)

    def test_teach_back_appended_for_math_low_diligent(
        self, make_chat_state, case2_student, mock_llm
    ):
        # 수학 LOW_DILIGENT는 마지막에 teach-back TextMessage를 추가한다
        for cause in ("confused_concept", "find_compare_numbers", "build_expression", "check_calculation"):
            state = self._make_state(make_chat_state, case2_student, cause)
            result = tp4(state)
            messages = result["tp4_response"]

            last = messages[-1]
            assert isinstance(last, TextMessage), f"cause={cause}: 마지막 메시지가 TextMessage여야 함"

    def test_build_expression_hint_card_has_steps(
        self, make_chat_state, case2_student, mock_llm
    ):
        state = self._make_state(make_chat_state, case2_student, "build_expression")
        result = tp4(state)
        messages = result["tp4_response"]

        hint_cards = [m for m in messages if isinstance(m, HintCardMessage)]
        assert hint_cards, "HintCardMessage가 없음"
        assert len(hint_cards[0].steps) >= 2, "힌트 단계가 2개 이상이어야 함"


# ─── 세그먼트명 노출 방지 ─────────────────────────────────────────────────────

class TestTp4SegmentNotExposed:
    """내부 세그먼트 식별자가 응답 메시지에 노출되지 않아야 한다."""

    INTERNAL_NAMES = ["LOW_LAZY", "LOW_DILIGENT", "HIGH_LAZY", "HIGH_DILIGENT",
                      "못함+불성실", "못함+성실", "잘함+불성실", "잘함+성실"]

    def _check_no_segment_in_messages(self, messages):
        for m in messages:
            for name in self.INTERNAL_NAMES:
                if isinstance(m, TextMessage):
                    assert name not in m.content, f"세그먼트명 '{name}'이 TextMessage에 노출됨"
                elif isinstance(m, ChoicesMessage):
                    for item in m.items:
                        assert name not in item.label, f"세그먼트명 '{name}'이 선택지 label에 노출됨"
                elif isinstance(m, ImageCardMessage):
                    assert name not in m.caption
                elif isinstance(m, HintCardMessage):
                    for step in m.steps:
                        assert name not in step.content

    def test_case1_no_cause(self, make_chat_state, case1_student, mock_llm):
        state = _state_with_cause(
            make_chat_state, case1_student, Segment.LOW_LAZY, GradeGroup.LOWER, None
        )
        result = tp4(state)
        self._check_no_segment_in_messages(result["tp4_response"])

    def test_case2_build_expression(self, make_chat_state, case2_student, mock_llm):
        state = _state_with_cause(
            make_chat_state, case2_student, Segment.LOW_DILIGENT, GradeGroup.UPPER, "build_expression"
        )
        result = tp4(state)
        self._check_no_segment_in_messages(result["tp4_response"])
