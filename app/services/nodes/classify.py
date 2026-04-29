from __future__ import annotations

from app.core import constants
from app.core.enums import GradeGroup, Segment
from app.core.logging import get_logger
from app.data.loader import load_student
from app.schemas.chat import ChatState
from app.schemas.student import LearningPattern, StudentProfile

logger = get_logger(__name__)


def get_grade_group(grade: int) -> GradeGroup:
    if grade <= constants.LOWER_GRADE_MAX:
        return GradeGroup.LOWER
    elif grade <= constants.MIDDLE_GRADE_MAX:
        return GradeGroup.MIDDLE
    return GradeGroup.UPPER


def get_segment(profile: StudentProfile, learning_pattern: LearningPattern) -> Segment:
    is_high = profile["recent_avg_score"] >= constants.HIGH_ACHIEVER_SCORE_THRESHOLD

    wrong_rate = learning_pattern["wrong_content_rate"]
    is_diligent = profile["avg_completion_rate"] >= constants.DILIGENT_COMPLETION_RATE_THRESHOLD and (
        wrong_rate is None or wrong_rate >= constants.DILIGENT_WRONG_CONTENT_THRESHOLD
    )

    if is_high and is_diligent:
        return Segment.HIGH_DILIGENT
    elif is_high:
        return Segment.HIGH_LAZY
    elif is_diligent:
        return Segment.LOW_DILIGENT
    else:
        return Segment.LOW_LAZY


def classify(state: ChatState) -> dict:
    student_id = state["student_id"]

    logger.info("classify 노드 시작", extra={"student_id": student_id})

    record = load_student(student_id)
    profile = record["profile"]
    learning_pattern = record["learning_pattern"]

    segment = get_segment(profile, learning_pattern)
    grade_group = get_grade_group(profile["grade"])

    has_wrong = learning_pattern["wrong_content_total"] > 0
    wrong_done_today = has_wrong and (
        learning_pattern["wrong_content_done"] >= learning_pattern["wrong_content_total"]
    )

    logger.info(
        "classify 노드 완료",
        extra={
            "student_id": student_id,
            "segment": segment.value,
            "grade_group": grade_group.value,
        },
    )

    return {
        "student_profile": profile,
        "learning_history": record["learning_history"],
        "learning_pattern": learning_pattern,
        "wrong_answer_pattern": record["wrong_answer_pattern"],
        "today_tasks": record["today_tasks"],
        "completed_tasks": [],
        "current_task": record["today_tasks"][0] if record["today_tasks"] else None,
        "current_problem": None,
        "tp4_phase": "awaiting_problem",
        "tp4_turn_count": 0,
        "has_wrong_answers": has_wrong,
        "wrong_content_done_today": wrong_done_today,
        "today_score": profile["recent_avg_score"],
        "segment": segment,
        "grade_group": grade_group,
    }
