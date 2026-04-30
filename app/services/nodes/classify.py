from __future__ import annotations

from time import perf_counter

from app.core import constants
from app.core.enums import GradeGroup, Segment
from app.core.logging import get_logger
from app.data.loader import load_problem, load_student
from app.schemas.chat import ChatRequestContext, ChatState, Task, TaskRef
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
    started = perf_counter()

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

    context = state.get("request_context")
    completed_tasks = _resolve_completed_tasks(record["today_tasks"], context)
    current_task = _resolve_current_task(record["today_tasks"], context)
    current_problem = _resolve_current_problem(context)
    if current_problem and current_task is None:
        current_task = _find_task_for_problem_id(
            record["today_tasks"],
            str(current_problem.get("problem_id", "")),
        )
    if current_task is None:
        current_task = record["today_tasks"][0] if record["today_tasks"] else None
    if context:
        logger.debug(
            "chat request context applied in classify",
            extra={
                "student_id": student_id,
                "completed_task_count": len(completed_tasks),
                "has_current_task": current_task is not None,
                "current_task_remaining_count": _context_value(
                    context,
                    "current_task_remaining_count",
                ),
                "has_current_problem": current_problem is not None,
            },
        )

    logger.info(
        "classify 노드 완료",
        extra={
            "student_id": student_id,
            "segment": segment.value,
            "grade_group": grade_group.value,
            "duration_ms": _elapsed_ms(started),
        },
    )

    return {
        "student_profile": profile,
        "learning_history": record["learning_history"],
        "learning_pattern": learning_pattern,
        "wrong_answer_pattern": record["wrong_answer_pattern"],
        "today_tasks": record["today_tasks"],
        "completed_tasks": completed_tasks,
        "current_task": current_task,
        "current_task_remaining_count": _context_value(context, "current_task_remaining_count"),
        "current_problem": current_problem,
        "tp4_phase": "awaiting_problem",
        "tp4_turn_count": 0,
        "has_wrong_answers": has_wrong,
        "wrong_content_done_today": wrong_done_today,
        "today_score": profile["recent_avg_score"],
        "segment": segment,
        "grade_group": grade_group,
    }


def _resolve_completed_tasks(
    today_tasks: list[Task],
    context: ChatRequestContext | dict | None,
) -> list[Task]:
    refs = _context_value(context, "completed_task_refs", []) or []
    return [
        task
        for task in (_resolve_task_ref(today_tasks, ref) for ref in refs)
        if task is not None
    ]


def _resolve_current_task(
    today_tasks: list[Task],
    context: ChatRequestContext | dict | None,
) -> Task | None:
    ref = _context_value(context, "current_task_ref")
    if ref:
        task = _resolve_task_ref(today_tasks, ref)
        if task:
            return task

    current_problem_id = _context_value(context, "current_problem_id")
    if current_problem_id:
        return _find_task_for_problem_id(today_tasks, str(current_problem_id))

    return None


def _resolve_current_problem(context: ChatRequestContext | dict | None) -> dict | None:
    problem_id = _context_value(context, "current_problem_id")
    if not problem_id:
        return None

    try:
        return dict(load_problem(str(problem_id)))
    except (KeyError, ValueError):
        logger.warning(
            "request context problem id not found",
            extra={"problem_id": str(problem_id)},
        )
        return None


def _resolve_task_ref(today_tasks: list[Task], ref: TaskRef | dict) -> Task | None:
    problem_id = _ref_value(ref, "problem_id")
    if problem_id:
        task = _find_task_for_problem_id(today_tasks, str(problem_id))
        if task:
            return task

    subject = _ref_value(ref, "subject")
    unit = _ref_value(ref, "unit")
    for task in today_tasks:
        if subject and unit:
            if task.get("subject") == subject and task.get("unit") == unit:
                return task
        elif subject and task.get("subject") == subject:
            return task
        elif unit and task.get("unit") == unit:
            return task

    return None


def _find_task_for_problem_id(today_tasks: list[Task], problem_id: str) -> Task | None:
    if not problem_id:
        return None
    for task in today_tasks:
        problem_ids = task.get("problem_ids", [])
        if task.get("problem_id") == problem_id or problem_id in problem_ids:
            return task
    return None


def _context_value(
    context: ChatRequestContext | dict | None,
    field: str,
    default=None,
):
    if context is None:
        return default
    if isinstance(context, dict):
        return context.get(field, default)
    return getattr(context, field, default)


def _ref_value(ref: TaskRef | dict, field: str) -> str | None:
    if isinstance(ref, dict):
        return ref.get(field)
    return getattr(ref, field, None)


def _elapsed_ms(started: float) -> int:
    return round((perf_counter() - started) * 1000)
