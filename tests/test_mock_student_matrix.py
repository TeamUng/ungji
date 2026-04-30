from __future__ import annotations

from pathlib import Path

import pytest

import scripts.run_scenarios as runner
from app.core.enums import Touchpoint
from app.data.loader import load_problem, load_student
from app.schemas.chat import ChatResponse, ChoiceItem, ChoicesMessage, TextMessage
from app.services.nodes.classify import get_grade_group, get_segment
from app.services.nodes.motivator import _situation_tp1
from scripts.run_scenarios import (
    CSV_COLUMNS,
    DEFAULT_STUDENT_IDS,
    EXPECTED_CASES,
    ResponseFields,
    _available_units,
    _extract_response_fields,
    _format_response_for_transcript,
    _parse_args,
    _recommended_task_from_response,
    _scenario_message_type,
    _scenario_state_overrides,
    _select_scenario_task,
    _simulated_student_reply,
    _task_problem_id,
    _transcript_path,
    select_student_ids,
)


EXPECTED_IDS = {
    "lower-low-lazy",
    "lower-low-diligent",
    "lower-high-lazy",
    "lower-high-diligent",
    "middle-low-lazy",
    "middle-low-diligent",
    "middle-high-lazy",
    "middle-high-diligent",
    "upper-low-lazy",
    "upper-low-diligent",
    "upper-high-lazy",
    "upper-high-diligent",
}


def test_expected_case_matrix_has_all_12_profiles() -> None:
    assert set(EXPECTED_CASES) == EXPECTED_IDS


@pytest.mark.parametrize("student_id", sorted(EXPECTED_IDS))
def test_mock_student_exists(student_id: str) -> None:
    assert load_student(student_id)["student_id"] == student_id


@pytest.mark.parametrize("student_id,expected", EXPECTED_CASES.items())
def test_mock_student_classification_matches_expected(student_id: str, expected) -> None:
    student = load_student(student_id)

    assert get_grade_group(student["profile"]["grade"]) == expected.grade_group
    assert get_segment(student["profile"], student["learning_pattern"]) == expected.segment


@pytest.mark.parametrize("student_id", sorted(EXPECTED_IDS))
def test_each_mock_student_has_four_curriculum_units(student_id: str) -> None:
    student = load_student(student_id)

    assert len(student["today_tasks"]) == 4


@pytest.mark.parametrize("student_id", sorted(EXPECTED_IDS))
def test_each_curriculum_unit_has_resolvable_problem_ids(student_id: str) -> None:
    student = load_student(student_id)

    for task in student["today_tasks"]:
        problem_ids = task["problem_ids"]

        assert problem_ids, f"{student_id} task {task['unit']} should have TP4 problems"
        assert task.get("problem_id") == problem_ids[0]
        for problem_id in problem_ids:
            assert load_problem(problem_id)["problem_id"] == problem_id


def test_runner_default_selection_is_two_team_focus_profiles() -> None:
    assert select_student_ids() == DEFAULT_STUDENT_IDS
    assert DEFAULT_STUDENT_IDS == [
        "lower-high-lazy",
        "upper-low-diligent",
    ]


def test_runner_all_selection_returns_all_profiles() -> None:
    assert select_student_ids(all_profiles=True) == list(EXPECTED_CASES)


def test_runner_criteria_filters_combine() -> None:
    selected = select_student_ids(
        grade_groups=["middle"],
        abilities=["high"],
        diligences=["lazy"],
    )

    assert selected == ["middle-high-lazy"]


def test_runner_exact_student_selection_preserves_order() -> None:
    selected = select_student_ids(
        students=["upper-high-diligent", "lower-low-lazy"],
    )

    assert selected == ["upper-high-diligent", "lower-low-lazy"]


def test_runner_unknown_student_selection_raises() -> None:
    with pytest.raises(ValueError, match="ghost-student"):
        select_student_ids(students=["ghost-student"])


def test_runner_tp4_problem_selection_reads_from_problem_ids() -> None:
    student = load_student("lower-high-lazy")
    task = _select_scenario_task(student, Touchpoint.TP4)

    assert student["today_tasks"][0]["problem_ids"][0] == "lower_korean_paragraph_001"
    assert _task_problem_id(task) == "lower_korean_paragraph_002"


def test_focused_upper_case_still_uses_math_context() -> None:
    student = load_student("upper-low-diligent")
    task = _select_scenario_task(student, Touchpoint.TP4)

    assert _task_problem_id(task) == "math_ratio_saltwater_001"


def test_upper_case_tp2_state_moves_from_math_to_korean() -> None:
    student = load_student("upper-low-diligent")
    state = _scenario_state_overrides(student, Touchpoint.TP2, student["today_tasks"][0])

    assert state["completed_tasks"][0]["unit"] == "비와 비율"
    assert state["current_task"]["subject"] == "국어"
    assert state["current_task"]["unit"] == "정보와 표현 판단하기"


def test_tp3_state_has_one_remaining_current_task_problem_for_lower_demo() -> None:
    student = load_student("lower-high-lazy")
    state = _scenario_state_overrides(student, Touchpoint.TP3, student["today_tasks"][0])

    assert state["current_task_remaining_count"] == 1


def test_tp5_state_marks_today_tasks_completed() -> None:
    student = load_student("lower-high-lazy")
    state = _scenario_state_overrides(student, Touchpoint.TP5, student["today_tasks"][0])

    assert state["completed_tasks"] == student["today_tasks"]
    assert state["current_task"] is None


def test_runner_available_units_includes_all_four_units() -> None:
    student = load_student("upper-low-diligent")
    available_units = _available_units(student)

    for task in student["today_tasks"]:
        assert task["subject"] in available_units
        assert task["unit"] in available_units
    assert available_units.count(" | ") == 3


def test_runner_csv_columns_include_curriculum_unit_context() -> None:
    assert "task_index" in CSV_COLUMNS
    assert "task_count" in CSV_COLUMNS
    assert "available_units" in CSV_COLUMNS
    assert "problem_id" in CSV_COLUMNS


def test_runner_parse_args_supports_simulated_conversation() -> None:
    args = _parse_args(["--simulate-conversation"])

    assert args.simulate_conversation is True


def test_runner_transcript_path_sits_next_to_csv() -> None:
    csv_path = Path("scripts/results/scenario_results_20260429_120000.csv")

    assert _transcript_path(csv_path) == Path("scripts/results/scenario_transcript_20260429_120000.md")


def test_runner_transcript_format_includes_choice_ids() -> None:
    response = ChatResponse(
        thread_id="test",
        messages=[
            ChoicesMessage(items=[
                ChoiceItem(id="too_long", label="글이 너무 길어요"),
                ChoiceItem(id="confused_concept", label="개념이 헷갈려요"),
            ])
        ],
    )

    transcript = _format_response_for_transcript(response)

    assert "`too_long`" in transcript
    assert "글이 너무 길어요" in transcript


def test_runner_simulated_tp4_reply_uses_first_choice_id() -> None:
    student = load_student("upper-low-lazy")
    task = _select_scenario_task(student, Touchpoint.TP4)
    response = ChatResponse(
        thread_id="test",
        messages=[ChoicesMessage(items=[ChoiceItem(id="too_long", label="글이 너무 길어요")])],
    )
    fields = _extract_response_fields(response)

    assert _simulated_student_reply(Touchpoint.TP4, 1, task, fields) == "too_long"


def test_runner_detects_recommended_unit_for_simulated_reply() -> None:
    student = load_student("upper-low-lazy")
    recommended = student["today_tasks"][1]
    response = ChatResponse(
        thread_id="test",
        messages=[TextMessage(content=f"{recommended['subject']} - {recommended['unit']}부터 시작해보자.")],
    )
    fields = _extract_response_fields(response)

    detected = _recommended_task_from_response(student, fields)
    reply = _simulated_student_reply(Touchpoint.TP1, 2, detected, fields)

    assert detected == recommended
    assert recommended["unit"] in reply


def test_runner_simulated_reply_uses_neutral_fallback_without_detected_unit() -> None:
    fields = ResponseFields(
        response_text="좋아, 추천한 것부터 해보자.",
        choices="",
        message_types="text",
        error="",
        first_choice_id="",
    )

    reply = _simulated_student_reply(Touchpoint.TP2, 2, None, fields)

    assert reply == "좋아요, 추천한 것부터 해볼게요."


def test_runner_message_types_match_real_api_semantics() -> None:
    from app.core.enums import MessageType

    assert _scenario_message_type("__problem_id__") == MessageType.INIT
    assert _scenario_message_type("__cause__") == MessageType.CHOICE
    assert _scenario_message_type("조금만 더 해보고 나갈게요.") == MessageType.TEXT


def test_runner_tp4_followup_matches_korean_reading_context() -> None:
    student = load_student("lower-high-lazy")
    task = _select_scenario_task(student, Touchpoint.TP4)
    fields = ResponseFields("", "", "text", "", "")

    reply = _simulated_student_reply(Touchpoint.TP4, 3, task, fields)

    assert "숫자" not in reply
    assert "문장" in reply


def test_runner_main_writes_csv_and_transcript(tmp_path, monkeypatch) -> None:
    def fake_call_graph(*, thread_id, student_id, use_case, touchpoint, message_content="", **kwargs):
        if touchpoint == Touchpoint.TP4 and message_content:
            return ChatResponse(
                thread_id=thread_id,
                messages=[ChoicesMessage(items=[ChoiceItem(id="too_long", label="글이 너무 길어요")])],
            )
        return ChatResponse(thread_id=thread_id, messages=[TextMessage(content="코칭 응답")])

    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "_call_graph", fake_call_graph)
    monkeypatch.setattr(runner, "_configure_stdout", lambda: None)

    runner.main(["--students", "lower-low-lazy"])

    csv_files = list(tmp_path.glob("scenario_results_*.csv"))
    transcript_files = list(tmp_path.glob("scenario_transcript_*.md"))

    assert len(csv_files) == 1
    assert len(transcript_files) == 1
    assert "Scenario Conversation Transcript" in transcript_files[0].read_text(encoding="utf-8")


def test_tp1_situation_includes_four_home_screen_units() -> None:
    student = load_student("lower-low-lazy")
    text = _situation_tp1({
        "student_profile": student["profile"],
        "today_tasks": student["today_tasks"],
        "learning_pattern": student["learning_pattern"],
    })

    assert "4개 단원" in text
    assert "추천 단원 하나" in text
    assert "선택지처럼 나열하지 말고" not in text
    for task in student["today_tasks"]:
        assert task["unit"] in text


def test_tp1_graph_response_fields_stay_text_only_for_text_response() -> None:
    response = ChatResponse(thread_id="test", messages=[TextMessage(content="수학 단원부터 시작해 보자!")])
    fields = _extract_response_fields(response)

    assert fields.message_types == "text"
    assert fields.response_text == "수학 단원부터 시작해 보자!"
    assert fields.choices == ""
