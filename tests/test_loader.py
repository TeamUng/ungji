from __future__ import annotations

import json

import pytest

from app.data import loader


def _write_json(path, data):
    """테스트용 JSON 파일을 UTF-8로 저장하는 작은 헬퍼."""

    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_load_student_returns_matching_student(tmp_path, monkeypatch):
    # 실제 app/data/mock_students.json은 빈 배열입니다.
    # 그래서 테스트에서는 임시 파일을 만들고 로더가 그 파일을 보도록 바꿉니다.
    students_file = tmp_path / "mock_students.json"
    _write_json(
        students_file,
        [
            {
                "student_id": "student-1",
                "profile": {
                    "name": "지우",
                    "grade": 1,
                    "preferred_subject": "국어",
                    "strong_subject": "국어",
                    "recent_avg_score": 62,
                    "avg_completion_rate": 35,
                },
                "learning_history": {
                    "subject_avg_scores": {"국어": 62},
                    "subject_completion_rates": {"국어": 35},
                },
                "learning_pattern": {
                    "wrong_content_rate": 20,
                    "wrong_content_total": 2,
                    "wrong_content_done": 0,
                    "skipping_habit": True,
                    "guessing_habit": False,
                    "careless_habit": True,
                },
                "wrong_answer_pattern": {
                    "frequent_wrong_type": "짧은 글 읽기",
                    "repeated_wrong_subjects": ["국어"],
                    "wrong_cause": "개념 부족",
                },
                "today_tasks": [
                    {
                        "subject": "국어",
                        "unit": "짧은 글 읽기",
                        "problem_count": 3,
                        "estimated_time": 5,
                        "difficulty": "하",
                        "ai_predicted_score": 65,
                    }
                ],
            }
        ],
    )
    monkeypatch.setattr(loader, "STUDENTS_FILE", students_file)

    student = loader.load_student("student-1")

    assert student["student_id"] == "student-1"
    assert student["profile"]["name"] == "지우"
    assert student["today_tasks"][0]["unit"] == "짧은 글 읽기"


def test_load_student_raises_key_error_when_student_does_not_exist(
    tmp_path, monkeypatch
):
    students_file = tmp_path / "mock_students.json"
    _write_json(students_file, [])
    monkeypatch.setattr(loader, "STUDENTS_FILE", students_file)

    with pytest.raises(KeyError, match="missing-student"):
        loader.load_student("missing-student")


def test_load_problem_returns_matching_problem(tmp_path, monkeypatch):
    problems_file = tmp_path / "mock_problems.json"
    _write_json(
        problems_file,
        [
            {
                "problem_id": "problem-1",
                "subject": "수학",
                "unit": "비율과 비례식",
                "question": "사과 2개와 배 3개의 비율은?",
                "answer": "2:3",
                "explanation": "사과 수와 배 수를 차례대로 비교합니다.",
                "hints": ["먼저 사과 수를 봅니다.", "그 다음 배 수를 봅니다."],
                "steps": ["사과는 2개입니다.", "배는 3개입니다.", "비율은 2:3입니다."],
            }
        ],
    )
    monkeypatch.setattr(loader, "PROBLEMS_FILE", problems_file)

    problem = loader.load_problem("problem-1")

    assert problem["problem_id"] == "problem-1"
    assert problem["subject"] == "수학"
    assert problem["steps"][-1] == "비율은 2:3입니다."


def test_load_problem_raises_key_error_when_problem_does_not_exist(
    tmp_path, monkeypatch
):
    problems_file = tmp_path / "mock_problems.json"
    _write_json(problems_file, [])
    monkeypatch.setattr(loader, "PROBLEMS_FILE", problems_file)

    with pytest.raises(KeyError, match="missing-problem"):
        loader.load_problem("missing-problem")


def test_demo_lower_korean_paragraph_problems_are_registered():
    first_problem = loader.load_problem("lower_korean_paragraph_001")
    second_problem = loader.load_problem("lower_korean_paragraph_002")

    assert first_problem["unit"] == "문단의 짜임 - 긴글 이해하기"
    assert first_problem["source_image_path"] == "reference/g2-korean-example-question-01.png"
    assert first_problem["answer"] == "2"
    assert "종이컵" in first_problem["question"]

    assert second_problem["unit"] == "문단의 짜임 - 중심 문장과 뒷받침 문장 찾기"
    assert second_problem["source_image_path"] == "reference/g2-korean-example-question-02.png"
    assert second_problem["answer"] == "4"
    assert "해일" in second_problem["question"]
