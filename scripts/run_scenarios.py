"""
Run the LangGraph scenario matrix, write CSV metrics, and write a Markdown transcript.

Examples:
    uv run python scripts/run_scenarios.py
    uv run python scripts/run_scenarios.py --all
    uv run python scripts/run_scenarios.py --grade-group middle --ability high
    uv run python scripts/run_scenarios.py --students lower-high-lazy upper-low-diligent
    uv run python scripts/run_scenarios.py --simulate-conversation
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Allow running this file directly from the repository root or scripts directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import configure_langsmith_tracing, settings

configure_langsmith_tracing()

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, MessageType, Segment, Touchpoint, UseCase
from app.core.logging import get_logger, setup_logging
from app.data.loader import StudentRecord, load_student
from app.schemas.chat import ChatResponse, ResponseMessage, Task
from app.services.decision_policy import classify_message_event
from app.services.graph import graph

logger = get_logger(__name__)


ABILITY_VALUES = ("low", "high")
DILIGENCE_VALUES = ("lazy", "diligent")
GRADE_GROUP_VALUES = tuple(group.value for group in GradeGroup)


@dataclass(frozen=True)
class ExpectedCase:
    grade_group: GradeGroup
    ability: str
    diligence: str
    segment: Segment


@dataclass(frozen=True)
class ResponseFields:
    response_text: str
    choices: str
    message_types: str
    error: str
    first_choice_id: str


EXPECTED_CASES: dict[str, ExpectedCase] = {
    "lower-low-lazy": ExpectedCase(GradeGroup.LOWER, "low", "lazy", Segment.LOW_LAZY),
    "lower-low-diligent": ExpectedCase(GradeGroup.LOWER, "low", "diligent", Segment.LOW_DILIGENT),
    "lower-high-lazy": ExpectedCase(GradeGroup.LOWER, "high", "lazy", Segment.HIGH_LAZY),
    "lower-high-diligent": ExpectedCase(GradeGroup.LOWER, "high", "diligent", Segment.HIGH_DILIGENT),
    "middle-low-lazy": ExpectedCase(GradeGroup.MIDDLE, "low", "lazy", Segment.LOW_LAZY),
    "middle-low-diligent": ExpectedCase(GradeGroup.MIDDLE, "low", "diligent", Segment.LOW_DILIGENT),
    "middle-high-lazy": ExpectedCase(GradeGroup.MIDDLE, "high", "lazy", Segment.HIGH_LAZY),
    "middle-high-diligent": ExpectedCase(GradeGroup.MIDDLE, "high", "diligent", Segment.HIGH_DILIGENT),
    "upper-low-lazy": ExpectedCase(GradeGroup.UPPER, "low", "lazy", Segment.LOW_LAZY),
    "upper-low-diligent": ExpectedCase(GradeGroup.UPPER, "low", "diligent", Segment.LOW_DILIGENT),
    "upper-high-lazy": ExpectedCase(GradeGroup.UPPER, "high", "lazy", Segment.HIGH_LAZY),
    "upper-high-diligent": ExpectedCase(GradeGroup.UPPER, "high", "diligent", Segment.HIGH_DILIGENT),
}

DEFAULT_STUDENT_IDS = [
    "lower-high-lazy",
    "upper-low-diligent",
]

TP_SCENARIOS = [
    (UseCase.TALK, Touchpoint.TP1, 1, "", "TP1 home-screen entry"),
    (UseCase.TALK, Touchpoint.TP2, 1, "", "TP2 unit completed"),
    (UseCase.TALK, Touchpoint.TP3, 1, "", "TP3 exit prevention"),
    (UseCase.LEARNING, Touchpoint.TP4, 1, "__problem_id__", "TP4 stuck: cause choices"),
    (UseCase.LEARNING, Touchpoint.TP4, 2, "__cause__", "TP4 stuck: coaching after cause"),
    (UseCase.TALK, Touchpoint.TP5, 1, "", "TP5 learning wrap-up"),
]

TP4_FALLBACK_CAUSE_BY_SUBJECT = {
    "국어": "confused_question",
    "수학": "confused_concept",
    "과학": "confused_relationship",
    "사회": "confused_context",
    "영어": "confused_vocabulary",
    "통합": "need_small_step",
}

TP4_SIMULATED_FOLLOWUPS = [
    "아직 어떤 숫자를 써야 하는지 잘 모르겠어요.",
    "그럼 비교하는 양을 전체 양으로 나누면 되나요?",
]

TP4_SIMULATED_FOLLOWUPS_BY_SUBJECT = {
    "국어": [
        "아직 어느 글자를 봐야 하는지 잘 모르겠어요.",
        "그럼 글자 아래에 붙은 걸 먼저 보면 되나요?",
    ],
    "수학": [
        "아직 어떤 숫자를 써야 하는지 잘 모르겠어요.",
        "그럼 비교하는 양을 전체 양으로 나누면 되나요?",
    ],
    "과학": [
        "아직 어디를 먼저 봐야 하는지 잘 모르겠어요.",
        "그럼 서로 어떤 관계인지 먼저 보면 되나요?",
    ],
    "사회": [
        "아직 무슨 뜻인지 잘 모르겠어요.",
        "그럼 중요한 말부터 하나씩 보면 되나요?",
    ],
    "영어": [
        "아직 어떤 단어를 봐야 하는지 잘 모르겠어요.",
        "그럼 모르는 단어부터 확인하면 되나요?",
    ],
    "통합": [
        "아직 어디부터 봐야 하는지 잘 모르겠어요.",
        "그럼 하나씩 관찰하면 되나요?",
    ],
}

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
DEFAULT_EXPECTATIONS_PATH = Path(__file__).parent / "scenarios" / "expected_cases.json"

CSV_COLUMNS = [
    "runner_mode",
    "student_id", "name", "grade", "grade_group", "segment",
    "expected_grade_group", "expected_ability", "expected_diligence",
    "expected_segment", "classification_ok",
    "preferred_subject", "strong_subject",
    "recent_avg_score", "avg_completion_rate",
    "wrong_content_rate", "wrong_content_total", "wrong_content_done",
    "skipping_habit", "guessing_habit", "careless_habit",
    "wrong_cause", "frequent_wrong_type",
    "task_index", "task_count", "available_units",
    "task_subject", "task_unit", "task_difficulty", "ai_predicted_score",
    "problem_id",
    "touchpoint", "use_case", "turn", "tp4_cause", "scenario_label",
    "has_wrong_answers", "wrong_content_done_today",
    "response_text", "choices", "message_types",
    "error",
]

EVAL_COLUMNS = [
    "case_id",
    "student_id",
    "touchpoint",
    "use_case",
    "turn",
    "scenario_label",
    "criterion",
    "expected",
    "actual",
    "passed",
    "note",
]


def select_student_ids(
    *,
    all_profiles: bool = False,
    students: Sequence[str] | None = None,
    grade_groups: Sequence[str] | None = None,
    abilities: Sequence[str] | None = None,
    diligences: Sequence[str] | None = None,
) -> list[str]:
    if all_profiles:
        return list(EXPECTED_CASES)

    if students:
        unknown = [student_id for student_id in students if student_id not in EXPECTED_CASES]
        if unknown:
            raise ValueError(f"Unknown student_id: {', '.join(unknown)}")
        return list(students)

    has_filters = bool(grade_groups or abilities or diligences)
    if not has_filters:
        return list(DEFAULT_STUDENT_IDS)

    grade_group_set = set(grade_groups or GRADE_GROUP_VALUES)
    ability_set = set(abilities or ABILITY_VALUES)
    diligence_set = set(diligences or DILIGENCE_VALUES)

    return [
        student_id
        for student_id, expected in EXPECTED_CASES.items()
        if expected.grade_group.value in grade_group_set
        and expected.ability in ability_set
        and expected.diligence in diligence_set
    ]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LangGraph scenario profiles.")
    parser.add_argument("--all", action="store_true", help="Run all 12 mock student profiles.")
    parser.add_argument("--students", nargs="+", help="Run exact student IDs.")
    parser.add_argument("--grade-group", nargs="+", choices=GRADE_GROUP_VALUES)
    parser.add_argument("--ability", nargs="+", choices=ABILITY_VALUES)
    parser.add_argument("--diligence", nargs="+", choices=DILIGENCE_VALUES)
    parser.add_argument("--list-students", action="store_true", help="Print available profiles and exit.")
    parser.add_argument(
        "--simulate-conversation",
        action="store_true",
        help=(
            "After each coach response, simulate a student reply and continue the graph. "
            "This increases LLM calls and adds follow-up rows to the CSV."
        ),
    )
    parser.add_argument(
        "--expectations",
        type=Path,
        default=DEFAULT_EXPECTATIONS_PATH,
        help=(
            "JSON file with scenario expectation checks. "
            "Defaults to scripts/scenarios/expected_cases.json."
        ),
    )
    parser.add_argument(
        "--skip-expectations",
        action="store_true",
        help="Skip expectation evaluation even when the expectations JSON exists.",
    )

    args = parser.parse_args(argv)
    criteria = args.grade_group or args.ability or args.diligence

    if args.all and (args.students or criteria):
        parser.error("--all cannot be combined with --students or criteria filters")
    if args.students and criteria:
        parser.error("--students cannot be combined with criteria filters")

    return args


def _student_ids_from_args(args: argparse.Namespace) -> list[str]:
    try:
        student_ids = select_student_ids(
            all_profiles=args.all,
            students=args.students,
            grade_groups=args.grade_group,
            abilities=args.ability,
            diligences=args.diligence,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if not student_ids:
        raise SystemExit("No student profiles matched the selected criteria.")

    return student_ids


def _print_available_students() -> None:
    print("student_id,grade_group,ability,diligence,segment")
    for student_id, expected in EXPECTED_CASES.items():
        print(
            f"{student_id},"
            f"{expected.grade_group.value},"
            f"{expected.ability},"
            f"{expected.diligence},"
            f"{expected.segment.value}"
        )


def _call_graph(
    thread_id: str,
    student_id: str,
    use_case: UseCase,
    touchpoint: Touchpoint,
    message_content: str = "",
    message_type: MessageType = MessageType.TEXT,
    state_overrides: dict[str, Any] | None = None,
) -> ChatResponse | None:
    message_event = classify_message_event(message_type, message_content)
    state: dict[str, Any] = {
        "thread_id": thread_id,
        "student_id": student_id,
        "use_case": use_case,
        "current_touchpoint": touchpoint,
        "current_message_type": message_event.message_type,
        "current_message_source": message_event.source,
        "current_message_requires_input_guard": message_event.should_check_input_guard,
        "chat_history": (
            [HumanMessage(content=message_event.content)]
            if message_event.should_append_human_message
            else []
        ),
        "response": None,
    }
    if state_overrides:
        state.update(state_overrides)
    config = {
        "configurable": {"thread_id": thread_id},
        "run_name": f"scenario:{touchpoint.value}:{student_id}",
        "tags": ["scenario-runner", use_case.value, touchpoint.value, student_id],
        "metadata": {
            "student_id": student_id,
            "use_case": use_case.value,
            "touchpoint": touchpoint.value,
            "runner_mode": "graph",
        },
    }
    result = graph.invoke(state, config=config)
    return result.get("response")


def _extract_response_fields(response: ChatResponse | None) -> ResponseFields:
    if response is None:
        return ResponseFields("", "", "", "LangGraph returned no response", "")

    response_texts: list[str] = []
    choices: list[str] = []
    message_types: list[str] = []
    first_choice_id = ""

    for msg in response.messages:
        message_types.append(msg.type)
        if msg.type == "text":
            response_texts.append(msg.content)
        elif msg.type == "choices":
            if msg.items and not first_choice_id:
                first_choice_id = msg.items[0].id
            choices.extend(item.label for item in msg.items)

    return ResponseFields(
        response_text="\n".join(response_texts),
        choices=" | ".join(choices),
        message_types="|".join(message_types),
        error="",
        first_choice_id=first_choice_id,
    )


def _derive_labels(record: StudentRecord) -> tuple[str, str]:
    from app.services.nodes.classify import get_grade_group, get_segment

    profile = record["profile"]
    pattern = record["learning_pattern"]
    return get_segment(profile, pattern).value, get_grade_group(profile["grade"]).value


def _task_problem_ids(task: Task | dict[str, Any]) -> list[str]:
    problem_ids = task.get("problem_ids") or []
    if isinstance(problem_ids, list) and problem_ids:
        return [str(problem_id) for problem_id in problem_ids if problem_id]

    legacy_problem_id = task.get("problem_id")
    return [str(legacy_problem_id)] if legacy_problem_id else []


def _task_problem_id(task: Task | dict[str, Any]) -> str:
    problem_ids = _task_problem_ids(task)
    return problem_ids[0] if problem_ids else ""


def _available_units(record: StudentRecord) -> str:
    return " | ".join(
        f"{index}. {task.get('subject', '')} - {task.get('unit', '')}"
        for index, task in enumerate(record["today_tasks"], 1)
    )


def _task_index(record: StudentRecord, selected_task: Task | dict[str, Any]) -> int:
    for index, task in enumerate(record["today_tasks"], 1):
        if task is selected_task or task == selected_task:
            return index
    return 0


def _classification_enums(record: StudentRecord) -> tuple[Segment, GradeGroup]:
    from app.services.nodes.classify import get_grade_group, get_segment

    profile = record["profile"]
    pattern = record["learning_pattern"]
    return get_segment(profile, pattern), get_grade_group(profile["grade"])


def _wrong_done_today(record: StudentRecord) -> bool:
    pattern = record["learning_pattern"]
    has_wrong = pattern["wrong_content_total"] > 0
    return has_wrong and pattern["wrong_content_done"] >= pattern["wrong_content_total"]


def _scenario_completed_tasks(
    record: StudentRecord,
    touchpoint: Touchpoint,
) -> list[Task]:
    tasks = record["today_tasks"]
    if touchpoint == Touchpoint.TP2:
        return list(tasks[:1])
    if touchpoint == Touchpoint.TP5:
        return list(tasks)
    return []


def _scenario_state_overrides(
    record: StudentRecord,
    touchpoint: Touchpoint,
    task: Task | dict[str, Any],
) -> dict[str, Any]:
    segment, grade_group = _classification_enums(record)
    today_tasks = record["today_tasks"]
    completed_tasks = _scenario_completed_tasks(record, touchpoint)
    remaining = [
        candidate
        for candidate in today_tasks
        if (candidate.get("subject"), candidate.get("unit"))
        not in {(done.get("subject"), done.get("unit")) for done in completed_tasks}
    ]

    if touchpoint == Touchpoint.TP2:
        current_task = remaining[0] if remaining else None
    elif touchpoint == Touchpoint.TP5:
        current_task = None
    else:
        current_task = task or (today_tasks[0] if today_tasks else None)

    pattern = record["learning_pattern"]
    return {
        "student_profile": record["profile"],
        "learning_history": record["learning_history"],
        "learning_pattern": pattern,
        "wrong_answer_pattern": record["wrong_answer_pattern"],
        "today_tasks": today_tasks,
        "completed_tasks": completed_tasks,
        "current_task": current_task,
        "current_task_remaining_count": 2 if touchpoint == Touchpoint.TP3 else None,
        "current_problem": None,
        "tp4_phase": "awaiting_problem",
        "tp4_turn_count": 0,
        "has_wrong_answers": pattern["wrong_content_total"] > 0,
        "wrong_content_done_today": _wrong_done_today(record),
        "today_score": record["profile"]["recent_avg_score"],
        "segment": segment,
        "grade_group": grade_group,
    }


def _scenario_message_type(message_content: str) -> MessageType:
    if message_content == "__problem_id__":
        return MessageType.INIT
    if message_content == "__cause__":
        return MessageType.CHOICE
    if message_content:
        return MessageType.TEXT
    return MessageType.INIT


def _select_scenario_task(record: StudentRecord, touchpoint: Touchpoint) -> Task | dict[str, Any]:
    tasks = record["today_tasks"]
    if not tasks:
        return {}

    if touchpoint == Touchpoint.TP4:
        for task in tasks:
            if _task_problem_ids(task):
                return task

    return tasks[0]


def _fallback_cause_for_task(task: Task | dict[str, Any]) -> str:
    subject = task.get("subject", "")
    return TP4_FALLBACK_CAUSE_BY_SUBJECT.get(subject, "need_help")


def _recommended_task_from_response(
    record: StudentRecord,
    fields: ResponseFields,
) -> Task | dict[str, Any] | None:
    response_context = f"{fields.response_text}\n{fields.choices}".lower()
    for task in record["today_tasks"]:
        unit = str(task.get("unit", ""))
        subject = str(task.get("subject", ""))
        if unit and unit.lower() in response_context:
            return task
        if subject and f"{subject} -" in response_context:
            return task
    return None


def _tp4_followups_for_task(task: Task | dict[str, Any]) -> list[str]:
    subject = str(task.get("subject", ""))
    return TP4_SIMULATED_FOLLOWUPS_BY_SUBJECT.get(subject, TP4_SIMULATED_FOLLOWUPS)


def _transcript_path(csv_path: Path) -> Path:
    return csv_path.with_name(csv_path.name.replace("scenario_results_", "scenario_transcript_")).with_suffix(".md")


def _message_to_transcript(message: ResponseMessage) -> str:
    if message.type == "text":
        return message.content
    if message.type == "choices":
        return "\n".join(f"- `{item.id}`: {item.label}" for item in message.items)
    if message.type == "hint_card":
        return "\n".join(f"{step.step}. {step.content}" for step in message.steps)
    if message.type == "image_card":
        return f"[image] {message.caption} ({message.image_url})"
    return str(message)


def _format_response_for_transcript(response: ChatResponse | None) -> str:
    if response is None:
        return "(no response)"
    return "\n\n".join(_message_to_transcript(message) for message in response.messages)


def _simulated_student_reply(
    touchpoint: Touchpoint,
    turn: int,
    task: Task | dict[str, Any] | None,
    fields: ResponseFields,
) -> str:
    if touchpoint == Touchpoint.TP4 and turn == 1:
        return fields.first_choice_id or _fallback_cause_for_task(task or {})
    if touchpoint == Touchpoint.TP4:
        if task is None:
            return "아직 어디부터 봐야 하는지 잘 모르겠어요."
        index = max(turn - 3, 0)
        followups = _tp4_followups_for_task(task)
        return followups[min(index, len(followups) - 1)]
    if touchpoint in (Touchpoint.TP1, Touchpoint.TP2):
        if task:
            return f"좋아요, {task.get('unit', '추천한 것')}부터 해볼게요."
        return "좋아요, 추천한 것부터 해볼게요."
    if touchpoint == Touchpoint.TP3:
        return "조금만 더 해보고 나갈게요."
    if touchpoint == Touchpoint.TP5:
        return "오늘은 여기까지 하고 내일 다시 할게요."
    return "네, 알겠어요."


def _append_transcript_header(
    transcript_lines: list[str],
    *,
    timestamp: str,
    student_ids: Sequence[str],
    simulate_conversation: bool,
) -> None:
    transcript_lines.extend([
        "# Scenario Conversation Transcript",
        "",
        f"- Generated: {timestamp}",
        f"- Student profiles: {', '.join(student_ids)}",
        f"- Simulated follow-up graph turns: {simulate_conversation}",
        "",
    ])


def _append_student_header(
    transcript_lines: list[str],
    *,
    student_id: str,
    record: StudentRecord,
    grade_group: str,
    segment: str,
) -> None:
    profile = record["profile"]
    transcript_lines.extend([
        "",
        f"## {student_id}",
        "",
        f"- Name: {profile['name']}",
        f"- Grade group: {grade_group}",
        f"- Segment: {segment}",
        "",
        "Available home-screen units:",
    ])
    for index, task in enumerate(record["today_tasks"], 1):
        transcript_lines.append(
            f"{index}. {task['subject']} - {task['unit']} "
            f"({task['problem_count']} problems, {task['estimated_time']} min, difficulty {task['difficulty']})"
        )
    transcript_lines.append("")


def _append_exchange(transcript_lines: list[str], role: str, content: str) -> None:
    transcript_lines.extend([f"**{role}:**", "", content or "(empty)", ""])


def _build_result_row(
    *,
    student_id: str,
    record: StudentRecord,
    expected: ExpectedCase,
    segment_val: str,
    grade_group_val: str,
    classification_ok: bool,
    has_wrong: bool,
    wrong_done_today: bool,
    task: Task | dict[str, Any],
    task_index: int,
    task_count: int,
    available_units: str,
    problem_id: str,
    touchpoint: Touchpoint,
    use_case: UseCase,
    turn: int,
    actual_content: str,
    label: str,
    fields: ResponseFields,
) -> dict[str, Any]:
    profile = record["profile"]
    pattern = record["learning_pattern"]
    wrong_pattern = record["wrong_answer_pattern"]

    return {
        "runner_mode": "graph",
        "student_id": student_id,
        "name": profile["name"],
        "grade": profile["grade"],
        "grade_group": grade_group_val,
        "segment": segment_val,
        "expected_grade_group": expected.grade_group.value,
        "expected_ability": expected.ability,
        "expected_diligence": expected.diligence,
        "expected_segment": expected.segment.value,
        "classification_ok": classification_ok,
        "preferred_subject": profile["preferred_subject"],
        "strong_subject": profile["strong_subject"],
        "recent_avg_score": profile["recent_avg_score"],
        "avg_completion_rate": profile["avg_completion_rate"],
        "wrong_content_rate": pattern["wrong_content_rate"],
        "wrong_content_total": pattern["wrong_content_total"],
        "wrong_content_done": pattern["wrong_content_done"],
        "skipping_habit": pattern["skipping_habit"],
        "guessing_habit": pattern["guessing_habit"],
        "careless_habit": pattern["careless_habit"],
        "wrong_cause": wrong_pattern["wrong_cause"],
        "frequent_wrong_type": wrong_pattern["frequent_wrong_type"],
        "task_index": task_index,
        "task_count": task_count,
        "available_units": available_units,
        "task_subject": task.get("subject", ""),
        "task_unit": task.get("unit", ""),
        "task_difficulty": task.get("difficulty", ""),
        "ai_predicted_score": task.get("ai_predicted_score", ""),
        "problem_id": problem_id,
        "touchpoint": touchpoint.value,
        "use_case": use_case.value,
        "turn": turn,
        "tp4_cause": actual_content if touchpoint == Touchpoint.TP4 and turn == 2 else "",
        "scenario_label": label,
        "has_wrong_answers": has_wrong,
        "wrong_content_done_today": wrong_done_today,
        "response_text": fields.response_text,
        "choices": fields.choices,
        "message_types": fields.message_types,
        "error": fields.error,
    }


def _load_scenario_expectations(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    expectations: list[dict[str, Any]] = []
    for case in raw.get("cases", []):
        case_id = case.get("case_id", "")
        student_id = case.get("student_id", "")
        for item in case.get("expectations", []):
            expectations.append({
                "case_id": case_id,
                "student_id": student_id,
                **item,
            })
    return expectations


def _matches_expectation(row: dict[str, Any], expectation: dict[str, Any]) -> bool:
    if row["student_id"] != expectation["student_id"]:
        return False
    if row["touchpoint"] != expectation["touchpoint"]:
        return False
    if row["use_case"] != expectation["use_case"]:
        return False
    if int(row["turn"]) != int(expectation["turn"]):
        return False

    scenario_label = expectation.get("scenario_label")
    return not scenario_label or row["scenario_label"] == scenario_label


def _combined_student_output(row: dict[str, Any]) -> str:
    return "\n".join(
        str(row.get(field, ""))
        for field in ("response_text", "choices", "message_types")
        if row.get(field)
    )


def _choice_count(row: dict[str, Any]) -> int:
    choices = str(row.get("choices", "")).strip()
    if not choices:
        return 0
    return len([choice for choice in choices.split(" | ") if choice.strip()])


def _expectation_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _message_types(row: dict[str, Any]) -> list[str]:
    return [
        message_type.strip()
        for message_type in str(row.get("message_types", "")).split("|")
        if message_type.strip()
    ]


def _eval_row(
    *,
    expectation: dict[str, Any],
    criterion: str,
    expected: Any,
    actual: Any,
    passed: bool,
    note: str = "",
) -> dict[str, Any]:
    return {
        "case_id": expectation.get("case_id", ""),
        "student_id": expectation.get("student_id", ""),
        "touchpoint": expectation.get("touchpoint", ""),
        "use_case": expectation.get("use_case", ""),
        "turn": expectation.get("turn", ""),
        "scenario_label": expectation.get("scenario_label", ""),
        "criterion": criterion,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "note": note,
    }


def _evaluate_expectation(
    row: dict[str, Any] | None,
    expectation: dict[str, Any],
) -> list[dict[str, Any]]:
    if row is None:
        return [_eval_row(
            expectation=expectation,
            criterion="row_exists",
            expected=True,
            actual=False,
            passed=False,
            note="No scenario result row matched this expectation.",
        )]

    output = _combined_student_output(row)
    eval_rows: list[dict[str, Any]] = []

    if expected_problem_id := expectation.get("expected_problem_id"):
        actual_problem_id = row.get("problem_id", "")
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="expected_problem_id",
            expected=expected_problem_id,
            actual=actual_problem_id,
            passed=actual_problem_id == expected_problem_id,
        ))

    if must_include_any := expectation.get("must_include_any"):
        matched = [term for term in must_include_any if term in output]
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="must_include_any",
            expected=" | ".join(must_include_any),
            actual=" | ".join(matched) if matched else output[:160],
            passed=bool(matched),
            note=expectation.get("must_include_any_note", ""),
        ))

    if must_include_all := expectation.get("must_include_all"):
        missing = [term for term in must_include_all if term not in output]
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="must_include_all",
            expected=" | ".join(must_include_all),
            actual=f"missing: {' | '.join(missing)}" if missing else "all present",
            passed=not missing,
        ))

    if must_not_include := expectation.get("must_not_include"):
        found = [term for term in must_not_include if term in output]
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="must_not_include",
            expected=" | ".join(must_not_include),
            actual=" | ".join(found) if found else "",
            passed=not found,
        ))

    required_message_types = _expectation_values(
        expectation.get("message_types_include")
        or expectation.get("required_message_types")
    )
    if required_message_types:
        actual_types = _message_types(row)
        missing_types = [
            message_type
            for message_type in required_message_types
            if message_type not in actual_types
        ]
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="message_types_include",
            expected=" | ".join(required_message_types),
            actual=" | ".join(actual_types),
            passed=not missing_types,
        ))

    if "min_choices" in expectation:
        min_choices = int(expectation["min_choices"])
        actual_count = _choice_count(row)
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="min_choices",
            expected=min_choices,
            actual=actual_count,
            passed=actual_count >= min_choices,
        ))

    if "max_choices" in expectation:
        max_choices = int(expectation["max_choices"])
        actual_count = _choice_count(row)
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="max_choices",
            expected=max_choices,
            actual=actual_count,
            passed=actual_count <= max_choices,
        ))

    if not eval_rows:
        eval_rows.append(_eval_row(
            expectation=expectation,
            criterion="row_exists",
            expected=True,
            actual=True,
            passed=True,
        ))

    return eval_rows


def _evaluate_rows_against_expectations(
    rows: list[dict[str, Any]],
    expectations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    eval_rows: list[dict[str, Any]] = []
    for expectation in expectations:
        matched_row = next(
            (row for row in rows if _matches_expectation(row, expectation)),
            None,
        )
        eval_rows.extend(_evaluate_expectation(matched_row, expectation))
    return eval_rows


def _configure_stdout() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "buffer"):
            setattr(
                sys,
                stream_name,
                io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"),
            )


def _flush_langsmith_traces() -> None:
    if not settings.LANGSMITH_API_KEY or settings.UNGJI_DISABLE_LANGSMITH_TRACING:
        return

    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
        logger.info("LangSmith trace flush completed")
    except Exception:
        logger.warning("LangSmith trace flush failed", exc_info=True)


def main(argv: Sequence[str] | None = None) -> None:
    _configure_stdout()
    setup_logging()

    args = _parse_args(argv)
    if args.list_students:
        _print_available_students()
        return

    student_ids = _student_ids_from_args(args)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"scenario_results_{timestamp}.csv"
    transcript_path = _transcript_path(csv_path)
    eval_path = RESULTS_DIR / f"scenario_eval_{timestamp}.csv"
    expectations = [] if args.skip_expectations else _load_scenario_expectations(args.expectations)

    print(f"\n{'=' * 70}")
    print("  LangGraph scenario runner")
    print(f"  Students: {len(student_ids)} | base scenarios per student: {len(TP_SCENARIOS)}")
    print(f"  Simulated follow-up graph turns: {args.simulate_conversation}")
    print(f"  CSV: {csv_path}")
    print(f"  Transcript: {transcript_path}")
    if expectations:
        print(f"  Expectation eval: {eval_path}")
    elif args.skip_expectations:
        print("  Expectation eval: skipped")
    else:
        print(f"  Expectation eval: no file at {args.expectations}")
    print(f"{'=' * 70}")

    logger.info(
        "LangGraph scenario runner started",
        extra={
            "student_count": len(student_ids),
            "scenario_count": len(TP_SCENARIOS),
            "simulate_conversation": args.simulate_conversation,
            "csv_path": str(csv_path),
            "transcript_path": str(transcript_path),
            "expectations_path": str(args.expectations),
            "expectation_count": len(expectations),
        },
    )

    all_rows: list[dict[str, Any]] = []
    transcript_lines: list[str] = []
    _append_transcript_header(
        transcript_lines,
        timestamp=timestamp,
        student_ids=student_ids,
        simulate_conversation=args.simulate_conversation,
    )

    for student_id in student_ids:
        expected = EXPECTED_CASES[student_id]
        record = load_student(student_id)
        profile = record["profile"]
        task_count = len(record["today_tasks"])
        available_units = _available_units(record)

        segment_val, grade_group_val = _derive_labels(record)
        classification_ok = (
            segment_val == expected.segment.value
            and grade_group_val == expected.grade_group.value
        )
        pattern = record["learning_pattern"]
        has_wrong = pattern["wrong_content_total"] > 0
        wrong_done_today = has_wrong and (
            pattern["wrong_content_done"] >= pattern["wrong_content_total"]
        )

        _append_student_header(
            transcript_lines,
            student_id=student_id,
            record=record,
            grade_group=grade_group_val,
            segment=segment_val,
        )

        tp4_thread_id = f"tp4-{student_id}-{uuid.uuid4()}"
        thread_ids: dict[Touchpoint, str] = {}
        selected_tp4_cause = ""
        last_tp4_response: ChatResponse | None = None

        print(f"\n  [{student_id}] {profile['name']} / {grade_group_val} / {segment_val}")
        if not classification_ok:
            print(
                "    [WARN] classification mismatch "
                f"(expected {expected.grade_group.value} / {expected.segment.value})"
            )

        for use_case, touchpoint, turn, message_content, label in TP_SCENARIOS:
            task = _select_scenario_task(record, touchpoint)
            task_index = _task_index(record, task)
            problem_id = _task_problem_id(task)

            if touchpoint == Touchpoint.TP4:
                thread_id = tp4_thread_id
            else:
                if touchpoint not in thread_ids:
                    thread_ids[touchpoint] = f"{touchpoint.value}-{student_id}-{uuid.uuid4()}"
                thread_id = thread_ids[touchpoint]

            if message_content == "__problem_id__":
                actual_content = problem_id
            elif message_content == "__cause__":
                actual_content = selected_tp4_cause or _fallback_cause_for_task(task)
            else:
                actual_content = message_content
            message_type = _scenario_message_type(message_content)
            state_overrides = (
                _scenario_state_overrides(record, touchpoint, task)
                if touchpoint != Touchpoint.TP4 or turn == 1
                else None
            )

            transcript_lines.extend(["", f"### {label}", ""])
            if actual_content:
                _append_exchange(transcript_lines, "Student", actual_content)
            else:
                _append_exchange(transcript_lines, "Student", "(opens this touchpoint)")

            response: ChatResponse | None = None
            try:
                response = _call_graph(
                    thread_id=thread_id,
                    student_id=student_id,
                    use_case=use_case,
                    touchpoint=touchpoint,
                    message_content=actual_content,
                    message_type=message_type,
                    state_overrides=state_overrides,
                )
                fields = _extract_response_fields(response)
                if touchpoint == Touchpoint.TP4 and turn == 1:
                    selected_tp4_cause = _simulated_student_reply(touchpoint, turn, task, fields)
                if touchpoint == Touchpoint.TP4:
                    last_tp4_response = response
            except Exception as exc:
                logger.exception(
                    "LangGraph scenario failed",
                    extra={
                        "student_id": student_id,
                        "use_case": use_case.value,
                        "touchpoint": touchpoint.value,
                        "turn": turn,
                        "task_index": task_index,
                        "problem_id": problem_id,
                    },
                )
                fields = ResponseFields("", "", "", str(exc), "")

            _append_exchange(transcript_lines, "Coach", _format_response_for_transcript(response))

            status = "[OK] " if not fields.error else "[ERR]"
            detail = f" [{actual_content}]" if touchpoint == Touchpoint.TP4 else ""
            print(f"    {status} {label}{detail}")
            if fields.response_text:
                preview = fields.response_text[:80].replace("\n", " ")
                print(f"      {preview}{'...' if len(fields.response_text) > 80 else ''}")
            if fields.error:
                print(f"      error: {fields.error}")

            all_rows.append(_build_result_row(
                student_id=student_id,
                record=record,
                expected=expected,
                segment_val=segment_val,
                grade_group_val=grade_group_val,
                classification_ok=classification_ok,
                has_wrong=has_wrong,
                wrong_done_today=wrong_done_today,
                task=task,
                task_index=task_index,
                task_count=task_count,
                available_units=available_units,
                problem_id=problem_id,
                touchpoint=touchpoint,
                use_case=use_case,
                turn=turn,
                actual_content=actual_content,
                label=label,
                fields=fields,
            ))

            if args.simulate_conversation and not fields.error and response is not None:
                if touchpoint == Touchpoint.TP4 and turn == 2:
                    last_tp4_response = _run_tp4_simulated_followups(
                        all_rows=all_rows,
                        transcript_lines=transcript_lines,
                        student_id=student_id,
                        record=record,
                        expected=expected,
                        segment_val=segment_val,
                        grade_group_val=grade_group_val,
                        classification_ok=classification_ok,
                        has_wrong=has_wrong,
                        wrong_done_today=wrong_done_today,
                        task=task,
                        task_index=task_index,
                        task_count=task_count,
                        available_units=available_units,
                        problem_id=problem_id,
                        thread_id=thread_id,
                        previous_response=last_tp4_response,
                    )
                elif touchpoint != Touchpoint.TP4:
                    _run_non_tp4_simulated_followup(
                        all_rows=all_rows,
                        transcript_lines=transcript_lines,
                        student_id=student_id,
                        record=record,
                        expected=expected,
                        segment_val=segment_val,
                        grade_group_val=grade_group_val,
                        classification_ok=classification_ok,
                        has_wrong=has_wrong,
                        wrong_done_today=wrong_done_today,
                        task=task,
                        task_index=task_index,
                        task_count=task_count,
                        available_units=available_units,
                        problem_id=problem_id,
                        thread_id=thread_id,
                        touchpoint=touchpoint,
                        previous_response=response,
                        base_label=label,
                    )

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    transcript_path.write_text("\n".join(transcript_lines).rstrip() + "\n", encoding="utf-8")

    eval_rows: list[dict[str, Any]] = []
    if expectations:
        eval_rows = _evaluate_rows_against_expectations(all_rows, expectations)
        with eval_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=EVAL_COLUMNS)
            writer.writeheader()
            writer.writerows(eval_rows)

    total = len(all_rows)
    errors = sum(1 for row in all_rows if row["error"])
    classification_errors = sum(1 for row in all_rows if not row["classification_ok"])
    eval_failures = sum(1 for row in eval_rows if not row["passed"])

    logger.info(
        "LangGraph scenario runner completed",
        extra={
            "total": total,
            "errors": errors,
            "classification_errors": classification_errors,
            "expectation_checks": len(eval_rows),
            "expectation_failures": eval_failures,
            "csv_path": str(csv_path),
            "transcript_path": str(transcript_path),
            "eval_path": str(eval_path) if eval_rows else "",
        },
    )
    _flush_langsmith_traces()

    print(f"\n{'=' * 70}")
    print(
        f"  Done: {total} rows | errors: {errors} | "
        f"classification mismatches: {classification_errors}"
    )
    if eval_rows:
        print(f"  Expectation checks: {len(eval_rows)} | failures: {eval_failures}")
    print(f"  CSV saved: {csv_path}")
    print(f"  Transcript saved: {transcript_path}")
    if eval_rows:
        print(f"  Eval saved: {eval_path}")
    print(f"{'=' * 70}\n")


def _run_non_tp4_simulated_followup(
    *,
    all_rows: list[dict[str, Any]],
    transcript_lines: list[str],
    student_id: str,
    record: StudentRecord,
    expected: ExpectedCase,
    segment_val: str,
    grade_group_val: str,
    classification_ok: bool,
    has_wrong: bool,
    wrong_done_today: bool,
    task: Task | dict[str, Any],
    task_index: int,
    task_count: int,
    available_units: str,
    problem_id: str,
    thread_id: str,
    touchpoint: Touchpoint,
    previous_response: ChatResponse,
    base_label: str,
) -> None:
    previous_fields = _extract_response_fields(previous_response)
    reply_task = _recommended_task_from_response(record, previous_fields)
    student_reply = _simulated_student_reply(touchpoint, 2, reply_task, previous_fields)
    label = f"{base_label} simulated student follow-up"

    transcript_lines.extend(["", f"### {label}", ""])
    _append_exchange(transcript_lines, "Student", student_reply)

    response: ChatResponse | None = None
    try:
        response = _call_graph(
            thread_id=thread_id,
            student_id=student_id,
            use_case=UseCase.CHAT,
            touchpoint=touchpoint,
            message_content=student_reply,
            message_type=MessageType.TEXT,
        )
        fields = _extract_response_fields(response)
    except Exception as exc:
        logger.exception(
            "Simulated non-TP4 follow-up failed",
            extra={"student_id": student_id, "touchpoint": touchpoint.value},
        )
        fields = ResponseFields("", "", "", str(exc), "")

    _append_exchange(transcript_lines, "Coach", _format_response_for_transcript(response))

    all_rows.append(_build_result_row(
        student_id=student_id,
        record=record,
        expected=expected,
        segment_val=segment_val,
        grade_group_val=grade_group_val,
        classification_ok=classification_ok,
        has_wrong=has_wrong,
        wrong_done_today=wrong_done_today,
        task=task,
        task_index=task_index,
        task_count=task_count,
        available_units=available_units,
        problem_id=problem_id,
        touchpoint=touchpoint,
        use_case=UseCase.CHAT,
        turn=2,
        actual_content=student_reply,
        label=label,
        fields=fields,
    ))


def _run_tp4_simulated_followups(
    *,
    all_rows: list[dict[str, Any]],
    transcript_lines: list[str],
    student_id: str,
    record: StudentRecord,
    expected: ExpectedCase,
    segment_val: str,
    grade_group_val: str,
    classification_ok: bool,
    has_wrong: bool,
    wrong_done_today: bool,
    task: Task | dict[str, Any],
    task_index: int,
    task_count: int,
    available_units: str,
    problem_id: str,
    thread_id: str,
    previous_response: ChatResponse | None,
) -> ChatResponse | None:
    last_response = previous_response

    for index, student_reply in enumerate(_tp4_followups_for_task(task), start=3):
        label = f"TP4 coaching follow-up {index - 2}"
        transcript_lines.extend(["", f"### {label}", ""])
        _append_exchange(transcript_lines, "Student", student_reply)

        response: ChatResponse | None = None
        try:
            response = _call_graph(
                thread_id=thread_id,
                student_id=student_id,
                use_case=UseCase.LEARNING,
                touchpoint=Touchpoint.TP4,
                message_content=student_reply,
                message_type=MessageType.TEXT,
            )
            fields = _extract_response_fields(response)
            last_response = response
        except Exception as exc:
            logger.exception(
                "Simulated TP4 follow-up failed",
                extra={"student_id": student_id, "turn": index, "problem_id": problem_id},
            )
            fields = ResponseFields("", "", "", str(exc), "")

        _append_exchange(transcript_lines, "Coach", _format_response_for_transcript(response))

        all_rows.append(_build_result_row(
            student_id=student_id,
            record=record,
            expected=expected,
            segment_val=segment_val,
            grade_group_val=grade_group_val,
            classification_ok=classification_ok,
            has_wrong=has_wrong,
            wrong_done_today=wrong_done_today,
            task=task,
            task_index=task_index,
            task_count=task_count,
            available_units=available_units,
            problem_id=problem_id,
            touchpoint=Touchpoint.TP4,
            use_case=UseCase.LEARNING,
            turn=index,
            actual_content=student_reply,
            label=label,
            fields=fields,
        ))

    return last_response


if __name__ == "__main__":
    main()
