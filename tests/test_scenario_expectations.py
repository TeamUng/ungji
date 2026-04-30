from pathlib import Path

from scripts.run_scenarios import (
    DEFAULT_EXPECTATIONS_PATH,
    _evaluate_expectation,
    _load_scenario_expectations,
)


def test_expected_cases_json_loads() -> None:
    expectations = _load_scenario_expectations(DEFAULT_EXPECTATIONS_PATH)

    assert expectations
    assert {expectation["student_id"] for expectation in expectations} == {
        "upper-low-diligent",
        "lower-high-lazy",
    }


def test_expectation_evaluation_checks_required_and_forbidden_text() -> None:
    expectation = {
        "case_id": "case",
        "student_id": "lower-high-lazy",
        "touchpoint": "tp3",
        "use_case": "talk",
        "turn": 1,
        "scenario_label": "TP3 exit prevention",
        "must_include_any": ["2문제", "거의"],
        "must_not_include": ["첫 식", "어디가 어려"],
        "max_choices": 0,
    }
    row = {
        "student_id": "lower-high-lazy",
        "touchpoint": "tp3",
        "use_case": "talk",
        "turn": 1,
        "scenario_label": "TP3 exit prevention",
        "response_text": "민준아, 거의 끝! 2문제만 더 하면 수학 끝이야.",
        "choices": "",
        "message_types": "text",
        "problem_id": "",
    }

    eval_rows = _evaluate_expectation(row, expectation)

    assert all(result["passed"] for result in eval_rows)


def test_expectation_evaluation_flags_forbidden_helper_language() -> None:
    expectation = {
        "case_id": "case",
        "student_id": "upper-low-diligent",
        "touchpoint": "tp3",
        "use_case": "talk",
        "turn": 1,
        "scenario_label": "TP3 exit prevention",
        "must_not_include": ["첫 식", "어디가 어려"],
    }
    row = {
        "student_id": "upper-low-diligent",
        "touchpoint": "tp3",
        "use_case": "talk",
        "turn": 1,
        "scenario_label": "TP3 exit prevention",
        "response_text": "그중 하나는 내가 같이 첫 식을 잡아줄게.",
        "choices": "",
        "message_types": "text",
        "problem_id": "",
    }

    eval_rows = _evaluate_expectation(row, expectation)

    assert not eval_rows[0]["passed"]
    assert eval_rows[0]["actual"] == "첫 식"


def test_expectation_evaluation_requires_min_choices_and_message_type() -> None:
    expectation = {
        "case_id": "case",
        "student_id": "lower-high-lazy",
        "touchpoint": "tp4",
        "use_case": "learning",
        "turn": 1,
        "scenario_label": "TP4 stuck: cause choices",
        "message_types_include": ["choices"],
        "min_choices": 1,
        "max_choices": 3,
    }
    row = {
        "student_id": "lower-high-lazy",
        "touchpoint": "tp4",
        "use_case": "learning",
        "turn": 1,
        "scenario_label": "TP4 stuck: cause choices",
        "response_text": "좋아, 한 단계만 같이 생각해보자.",
        "choices": "",
        "message_types": "text",
        "problem_id": "lower_korean_reading_001",
    }

    eval_rows = _evaluate_expectation(row, expectation)
    results = {row["criterion"]: row for row in eval_rows}

    assert results["message_types_include"]["passed"] is False
    assert results["min_choices"]["passed"] is False
    assert results["max_choices"]["passed"] is True


def test_expectations_file_stays_inside_scripts_scenarios() -> None:
    assert Path(DEFAULT_EXPECTATIONS_PATH).parts[-3:] == (
        "scripts",
        "scenarios",
        "expected_cases.json",
    )
