from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from app.core.logging import get_logger
from app.schemas.chat import Task
from app.schemas.student import (
    LearningHistory,
    LearningPattern,
    StudentProfile,
    WrongAnswerPattern,
)

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent
STUDENTS_FILE = DATA_DIR / "mock_students.json"
PROBLEMS_FILE = DATA_DIR / "mock_problems.json"


class StudentRecord(TypedDict):
    """학생 한 명에 대해 그래프 초기화에 필요한 목업 데이터 묶음."""

    student_id: str
    profile: StudentProfile
    learning_history: LearningHistory
    learning_pattern: LearningPattern
    wrong_answer_pattern: WrongAnswerPattern
    today_tasks: list[Task]


class ProblemPassage(TypedDict):
    label: str
    text: str


class ProblemChoice(TypedDict):
    id: str
    label: str


class ProblemRecord(TypedDict):
    """학습 중 도움 요청(TP4)에서 참조할 문제 목업 데이터."""

    problem_id: str
    subject: str
    unit: str
    question: str
    answer: str
    explanation: str
    hints: list[str]
    steps: list[str]
    source_image_path: NotRequired[str]
    passage: NotRequired[list[ProblemPassage]]
    topic_sentence: NotRequired[str]
    choices: NotRequired[list[ProblemChoice]]
    evidence: NotRequired[dict[str, str]]


def _read_json_array(path: Path, data_name: str) -> list[dict[str, Any]]:
    """JSON 파일을 읽고, 최상위 구조가 배열인지 확인한다.

    지금 단계에서는 Pydantic 모델까지 만들지 않고 가볍게 검증합니다.
    대신 파일 구조가 크게 잘못되었을 때는 바로 알아챌 수 있도록
    "최상위는 배열", "배열 안의 값은 객체"라는 최소 규칙만 검사합니다.
    """

    logger.debug(
        "목업 데이터 파일 읽기 시작",
        extra={"data_name": data_name, "data_file": str(path)},
    )

    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.exception(
            "목업 데이터 파일을 찾을 수 없음",
            extra={"data_name": data_name, "data_file": str(path)},
        )
        raise
    except json.JSONDecodeError as exc:
        logger.exception(
            "목업 데이터 JSON 파싱 실패",
            extra={"data_name": data_name, "data_file": str(path)},
        )
        raise ValueError(f"{data_name} JSON 형식이 올바르지 않습니다: {path}") from exc

    if not isinstance(data, list):
        logger.error(
            "목업 데이터 최상위 구조가 배열이 아님",
            extra={"data_name": data_name, "data_file": str(path)},
        )
        raise ValueError(f"{data_name} JSON은 배열이어야 합니다: {path}")

    if not all(isinstance(item, dict) for item in data):
        logger.error(
            "목업 데이터 배열 안에 객체가 아닌 값이 있음",
            extra={"data_name": data_name, "data_file": str(path)},
        )
        raise ValueError(f"{data_name} JSON 배열의 각 항목은 객체여야 합니다: {path}")

    logger.debug(
        "목업 데이터 파일 읽기 완료",
        extra={"data_name": data_name, "count": len(data)},
    )

    return cast(list[dict[str, Any]], data)


def load_student(student_id: str) -> StudentRecord:
    """student_id에 맞는 학생 목업 데이터를 반환한다.

    없을 때는 `KeyError`를 던집니다. 이후 API 계층에서 이 예외를 잡으면
    "없는 학생입니다" 같은 4xx 응답으로 바꾸기 쉽습니다.
    """

    students = _read_json_array(STUDENTS_FILE, "students")

    for student in students:
        if student.get("student_id") == student_id:
            logger.info("학생 목업 데이터 조회 성공", extra={"student_id": student_id})
            return cast(StudentRecord, student)

    logger.warning("학생 목업 데이터 조회 실패", extra={"student_id": student_id})
    raise KeyError(f"학생 ID를 찾을 수 없습니다: {student_id}")


def load_problem(problem_id: str) -> ProblemRecord:
    """problem_id에 맞는 문제 목업 데이터를 반환한다."""

    problems = _read_json_array(PROBLEMS_FILE, "problems")

    for problem in problems:
        if problem.get("problem_id") == problem_id:
            logger.info("문제 목업 데이터 조회 성공", extra={"problem_id": problem_id})
            return cast(ProblemRecord, problem)

    logger.warning("문제 목업 데이터 조회 실패", extra={"problem_id": problem_id})
    raise KeyError(f"문제 ID를 찾을 수 없습니다: {problem_id}")
