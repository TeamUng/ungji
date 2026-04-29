from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from app.core.enums import Touchpoint, UseCase
from app.data.loader import StudentRecord
from app.services.graph import graph
from app.services.nodes.helper import TP4_PHASE_COACHING
from app.services.prompts.agents import HELPER_ROLE, MOTIVATOR_ROLE


def _invoke(student: StudentRecord, use_case: UseCase, touchpoint: Touchpoint) -> dict:
    thread_id = f"test-{student['student_id']}-{touchpoint}-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "thread_id": thread_id,
        "student_id": student["student_id"],
        "use_case": use_case,
        "current_touchpoint": touchpoint,
        "response": None,
    }
    with patch("app.services.nodes.classify.load_student", return_value=student):
        return graph.invoke(initial, config=config)


def test_case1_talk_tp1_routes_to_motivator(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.TALK, Touchpoint.TP1)

    assert result["response"] is not None
    assert "text" in [message.type for message in result["response"].messages]


def test_case1_learning_tp4_routes_to_helper(case1_student, mock_llm):
    result = _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP4)

    assert result["response"] is not None


def test_case2_talk_tp1_routes_to_motivator(case2_student, mock_llm):
    result = _invoke(case2_student, UseCase.TALK, Touchpoint.TP1)

    assert result["response"] is not None
    assert "text" in [message.type for message in result["response"].messages]


def test_case2_learning_tp4_routes_to_helper(case2_student, mock_llm):
    result = _invoke(case2_student, UseCase.LEARNING, Touchpoint.TP4)

    assert result["response"] is not None


def test_tp2_routing(case1_student, mock_llm):
    assert _invoke(case1_student, UseCase.TALK, Touchpoint.TP2)["response"] is not None


def test_tp3_routing(case1_student, mock_llm):
    assert _invoke(case1_student, UseCase.TALK, Touchpoint.TP3)["response"] is not None


def test_tp5_routing(case1_student, mock_llm):
    assert _invoke(case1_student, UseCase.TALK, Touchpoint.TP5)["response"] is not None


def test_chat_with_non_tp4_routes_to_motivator(case1_student, mock_llm):
    _invoke(case1_student, UseCase.CHAT, Touchpoint.TP1)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert MOTIVATOR_ROLE in system_content


def test_chat_with_tp4_routes_to_helper(case1_student, mock_llm):
    _invoke(case1_student, UseCase.CHAT, Touchpoint.TP4)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert HELPER_ROLE in system_content


def test_invalid_touchpoint_learning_with_tp1_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.LEARNING, Touchpoint.TP1)


def test_invalid_touchpoint_talk_with_tp4_raises(case1_student, mock_llm):
    with pytest.raises(Exception):
        _invoke(case1_student, UseCase.TALK, Touchpoint.TP4)


def test_classify_runs_only_on_first_turn(case1_student, mock_llm):
    thread_id = f"session-test-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "thread_id": thread_id,
        "student_id": case1_student["student_id"],
        "use_case": UseCase.TALK,
        "current_touchpoint": Touchpoint.TP1,
        "response": None,
    }

    with patch("app.services.nodes.classify.load_student", return_value=case1_student) as mock_load:
        graph.invoke(initial, config=config)
        assert mock_load.call_count == 1

        graph.invoke({
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="too_long")],
        }, config=config)

        assert mock_load.call_count == 1


def test_user_and_coach_history_are_preserved_between_turns(case1_student, mock_llm):
    thread_id = f"session-history-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    mock_llm.response_content = "홈 화면 코칭 응답"

    with patch("app.services.nodes.classify.load_student", return_value=case1_student):
        graph.invoke({
            "thread_id": thread_id,
            "student_id": case1_student["student_id"],
            "use_case": UseCase.TALK,
            "current_touchpoint": Touchpoint.TP1,
            "response": None,
        }, config=config)

        mock_llm.response_content = "TP4 코칭 응답"
        result = graph.invoke({
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="too_long")],
        }, config=config)

    contents = [message.content for message in result["chat_history"]]
    assert "홈 화면 코칭 응답" in contents
    assert "too_long" in contents
    assert "TP4 코칭 응답" in contents


def test_first_turn_chat_history_survives_classify_for_tp4_problem_id(case2_student, mock_llm):
    thread_id = f"session-first-history-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    with patch("app.services.nodes.classify.load_student", return_value=case2_student):
        result = graph.invoke({
            "thread_id": thread_id,
            "student_id": case2_student["student_id"],
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="math_ratio_saltwater_001")],
            "response": None,
        }, config=config)

    assert result["current_problem"]["problem_id"] == "math_ratio_saltwater_001"
    assert "math_ratio_saltwater_001" in [message.content for message in result["chat_history"]]


def test_tp4_continues_as_agentic_conversation(case2_student, mock_llm):
    thread_id = f"session-tp4-multiturn-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    with patch("app.services.nodes.classify.load_student", return_value=case2_student):
        mock_llm.next_tool_calls = [
            {
                "name": "send_causes",
                "args": {
                    "items": [
                        {"id": "too_long", "label": "글이 너무 길어요"},
                        {"id": "confused_concept", "label": "개념이 헷갈려요"},
                    ]
                },
            }
        ]
        turn1 = graph.invoke({
            "thread_id": thread_id,
            "student_id": case2_student["student_id"],
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="math_ratio_saltwater_001")],
            "response": None,
        }, config=config)

        assert turn1["tp4_phase"] == TP4_PHASE_COACHING

        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "좋아, 먼저 문제를 짧게 나눠보자."}}
        ]
        turn2 = graph.invoke({
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="too_long")],
        }, config=config)

        assert turn2["tp4_phase"] == TP4_PHASE_COACHING

        mock_llm.next_tool_calls = [
            {"name": "send_text", "args": {"content": "이번에는 어떤 양을 비교하는지 보자."}}
        ]
        turn3 = graph.invoke({
            "use_case": UseCase.LEARNING,
            "current_touchpoint": Touchpoint.TP4,
            "chat_history": [HumanMessage(content="어떤 숫자를 써야 하는지 모르겠어요")],
        }, config=config)

    contents = [message.content for message in turn3["chat_history"]]
    assert turn3["tp4_phase"] == TP4_PHASE_COACHING
    assert turn3["tp4_turn_count"] == 3
    assert any("too_long" in content for content in contents)
    assert any("좋아, 먼저 문제를 짧게 나눠보자." in content for content in contents)
    assert any("어떤 숫자를 써야 하는지 모르겠어요" in content for content in contents)
