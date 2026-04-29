from __future__ import annotations

import sys
import types
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.enums import (
    Difficulty,
    GradeGroup,
    Segment,
    Subject,
    Touchpoint,
    UseCase,
    WrongCause,
)
from app.data.loader import StudentRecord
from app.main import app
from app.schemas.chat import ChatState, Task


@pytest.fixture
def case1_student() -> StudentRecord:
    return {
        "student_id": "case-1-low-lazy-korean",
        "profile": {
            "name": "민준",
            "grade": 1,
            "preferred_subject": Subject.KOREAN,
            "strong_subject": Subject.KOREAN,
            "recent_avg_score": 62,
            "avg_completion_rate": 35,
        },
        "learning_history": {
            "subject_avg_scores": {Subject.KOREAN.value: 62},
            "subject_completion_rates": {Subject.KOREAN.value: 35},
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
            "repeated_wrong_subjects": [Subject.KOREAN.value],
            "wrong_cause": WrongCause.CONCEPT_LACK,
        },
        "today_tasks": [
            {
                "subject": Subject.KOREAN.value,
                "unit": "짧은 글 읽기",
                "problem_count": 3,
                "estimated_time": 5,
                "difficulty": Difficulty.LOW.value,
                "ai_predicted_score": 65,
            }
        ],
    }


@pytest.fixture
def case2_student() -> StudentRecord:
    return {
        "student_id": "case-2-low-diligent-math",
        "profile": {
            "name": "서연",
            "grade": 5,
            "preferred_subject": Subject.MATH,
            "strong_subject": Subject.SCIENCE,
            "recent_avg_score": 72,
            "avg_completion_rate": 88,
        },
        "learning_history": {
            "subject_avg_scores": {Subject.MATH.value: 72},
            "subject_completion_rates": {Subject.MATH.value: 88},
        },
        "learning_pattern": {
            "wrong_content_rate": 75,
            "wrong_content_total": 3,
            "wrong_content_done": 1,
            "skipping_habit": False,
            "guessing_habit": False,
            "careless_habit": False,
        },
        "wrong_answer_pattern": {
            "frequent_wrong_type": "비율과 비례식",
            "repeated_wrong_subjects": [Subject.MATH.value],
            "wrong_cause": WrongCause.CONCEPT_LACK,
        },
        "today_tasks": [
            {
                "subject": Subject.MATH.value,
                "unit": "비율과 비례식",
                "problem_count": 4,
                "estimated_time": 12,
                "difficulty": Difficulty.MEDIUM.value,
                "ai_predicted_score": 74,
            }
        ],
    }


@pytest.fixture
def high_diligent_student() -> StudentRecord:
    return {
        "student_id": "high-diligent",
        "profile": {
            "name": "하윤",
            "grade": 4,
            "preferred_subject": Subject.SCIENCE,
            "strong_subject": Subject.MATH,
            "recent_avg_score": 95,
            "avg_completion_rate": 92,
        },
        "learning_history": {
            "subject_avg_scores": {Subject.MATH.value: 95, Subject.SCIENCE.value: 97},
            "subject_completion_rates": {
                Subject.MATH.value: 92,
                Subject.SCIENCE.value: 94,
            },
        },
        "learning_pattern": {
            "wrong_content_rate": None,
            "wrong_content_total": 0,
            "wrong_content_done": 0,
            "skipping_habit": False,
            "guessing_habit": False,
            "careless_habit": False,
        },
        "wrong_answer_pattern": {
            "frequent_wrong_type": "",
            "repeated_wrong_subjects": [],
            "wrong_cause": WrongCause.MISTAKE,
        },
        "today_tasks": [
            {
                "subject": Subject.MATH.value,
                "unit": "응용 문제",
                "problem_count": 5,
                "estimated_time": 10,
                "difficulty": Difficulty.HIGH.value,
                "ai_predicted_score": 94,
            }
        ],
    }


@pytest.fixture
def high_lazy_student() -> StudentRecord:
    return {
        "student_id": "high-lazy",
        "profile": {
            "name": "도윤",
            "grade": 6,
            "preferred_subject": Subject.MATH,
            "strong_subject": Subject.MATH,
            "recent_avg_score": 93,
            "avg_completion_rate": 42,
        },
        "learning_history": {
            "subject_avg_scores": {Subject.MATH.value: 93},
            "subject_completion_rates": {Subject.MATH.value: 42},
        },
        "learning_pattern": {
            "wrong_content_rate": 25,
            "wrong_content_total": 2,
            "wrong_content_done": 0,
            "skipping_habit": True,
            "guessing_habit": False,
            "careless_habit": True,
        },
        "wrong_answer_pattern": {
            "frequent_wrong_type": "응용 문제",
            "repeated_wrong_subjects": [Subject.MATH.value],
            "wrong_cause": WrongCause.MISTAKE,
        },
        "today_tasks": [
            {
                "subject": Subject.MATH.value,
                "unit": "도전 문제",
                "problem_count": 3,
                "estimated_time": 7,
                "difficulty": Difficulty.HIGH.value,
                "ai_predicted_score": 91,
            }
        ],
    }


@pytest.fixture
def make_chat_state() -> Callable[..., ChatState]:
    def _make_chat_state(
        student: StudentRecord,
        *,
        segment: Segment,
        grade_group: GradeGroup,
        use_case: UseCase = UseCase.TALK,
        touchpoint: Touchpoint = Touchpoint.TP1,
        completed_tasks: list[Task] | None = None,
        current_task: Task | None = None,
    ) -> ChatState:
        today_tasks = student["today_tasks"]
        completed = completed_tasks or []
        learning_pattern = student["learning_pattern"]

        return {
            "thread_id": f"thread-{student['student_id']}",
            "student_id": student["student_id"],
            "student_profile": student["profile"],
            "learning_history": student["learning_history"],
            "learning_pattern": learning_pattern,
            "wrong_answer_pattern": student["wrong_answer_pattern"],
            "today_tasks": today_tasks,
            "completed_tasks": completed,
            "current_task": current_task or (today_tasks[0] if today_tasks else None),
            "has_wrong_answers": learning_pattern["wrong_content_total"] > 0,
            "wrong_content_done_today": (
                learning_pattern["wrong_content_total"] > 0
                and learning_pattern["wrong_content_done"]
                >= learning_pattern["wrong_content_total"]
            ),
            "today_score": student["profile"]["recent_avg_score"],
            "use_case": use_case,
            "grade_group": grade_group,
            "segment": segment,
            "chat_history": [],
            "current_touchpoint": touchpoint,
        }

    return _make_chat_state


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@dataclass
class FakeLLMResponse:
    content: str
    tool_calls: list = field(default_factory=list)


@dataclass
class FakeLLM:
    response_content: str = "테스트용 AI 코치 응답입니다."
    next_tool_calls: list = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def invoke(self, messages, **kwargs) -> FakeLLMResponse:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return FakeLLMResponse(content=self.response_content, tool_calls=list(self.next_tool_calls))

    def bind_tools(self, tools) -> "FakeLLM":
        return self

    async def ainvoke(self, messages, **kwargs) -> FakeLLMResponse:
        return self.invoke(messages, **kwargs)

    def stream(self, messages, **kwargs):
        yield self.invoke(messages, **kwargs)


@pytest.fixture
def mock_llm(monkeypatch) -> FakeLLM:
    fake_llm = FakeLLM()
    fake_module = types.ModuleType("app.clients.llm")
    fake_module.motivator_llm = fake_llm
    fake_module.helper_llm = fake_llm
    monkeypatch.setitem(sys.modules, "app.clients.llm", fake_module)
    return fake_llm
