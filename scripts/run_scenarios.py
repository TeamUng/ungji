"""
LangGraph 시나리오 러너 — 저성취 학생 × 터치포인트 조합을 Solar Pro2로 실행하고
결과를 CSV로 저장한다.

사용법:
    uv run python scripts/run_scenarios.py

출력:
    - 터미널: 각 시나리오 결과 실시간 출력
    - scripts/results/scenario_results_YYYYMMDD_HHMMSS.csv
"""

from __future__ import annotations

import csv
import io
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Windows 터미널 한글·이모지 출력을 위해 stdout을 UTF-8로 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.core.logging import get_logger
from app.data.loader import load_student
from app.schemas.chat import ChatResponse
from app.services.graph import graph

logger = get_logger(__name__)

# ─── 설정 ─────────────────────────────────────────────────────────────────────

STUDENT_IDS = [
    "lower-low-diligent",
    "lower-low-lazy",
    "upper-low-diligent",
    "upper-low-lazy",
]

TP_SCENARIOS = [
    (UseCase.TALK,     Touchpoint.TP1, 1, "",           "TP1 홈화면 진입"),
    (UseCase.TALK,     Touchpoint.TP2, 1, "",           "TP2 단위 학습 완료"),
    (UseCase.TALK,     Touchpoint.TP3, 1, "",           "TP3 이탈 방지"),
    (UseCase.LEARNING, Touchpoint.TP4, 1, "",           "TP4 막힘 (원인 선택지)"),
    (UseCase.LEARNING, Touchpoint.TP4, 2, "__cause__",  "TP4 막힘 (원인 선택 후 코칭)"),
    (UseCase.TALK,     Touchpoint.TP5, 1, "",           "TP5 학습 종료"),
]

EXPECTED_CASES = {
    "lower-low-diligent": (Segment.LOW_DILIGENT.value, GradeGroup.LOWER.value),
    "lower-low-lazy": (Segment.LOW_LAZY.value, GradeGroup.LOWER.value),
    "upper-low-diligent": (Segment.LOW_DILIGENT.value, GradeGroup.UPPER.value),
    "upper-low-lazy": (Segment.LOW_LAZY.value, GradeGroup.UPPER.value),
}

TP4_CAUSE_BY_SUBJECT = {
    "국어": "too_long",
    "수학": "confused_concept",
}

# ─── 결과 저장 경로 ───────────────────────────────────────────────────────────

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CSV_COLUMNS = [
    "runner_mode",
    "student_id", "name", "grade", "grade_group", "segment",
    "expected_grade_group", "expected_segment", "classification_ok",
    "preferred_subject", "strong_subject",
    "recent_avg_score", "avg_completion_rate",
    "wrong_content_rate", "wrong_content_total", "wrong_content_done",
    "skipping_habit", "guessing_habit", "careless_habit",
    "wrong_cause", "frequent_wrong_type",
    "task_subject", "task_unit", "task_difficulty", "ai_predicted_score",
    "touchpoint", "use_case", "turn", "tp4_cause", "scenario_label",
    "has_wrong_answers", "wrong_content_done_today",
    "response_text", "choices", "message_types",
    "error",
]

# ─── LangGraph 호출 ───────────────────────────────────────────────────────────

def _call_graph(
    thread_id: str,
    student_id: str,
    use_case: UseCase,
    touchpoint: Touchpoint,
    message_content: str,
) -> ChatResponse | None:
    state: dict = {
        "thread_id": thread_id,
        "student_id": student_id,
        "use_case": use_case,
        "current_touchpoint": touchpoint,
        "chat_history": (
            [HumanMessage(content=message_content)]
            if message_content
            else []
        ),
        "response": None,
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state, config=config)
    return result.get("response")


def _extract_response_fields(response: ChatResponse | None) -> tuple[str, str, str, str]:
    if response is None:
        return "", "", "", "LangGraph 응답 없음"

    response_texts: list[str] = []
    choices: list[str] = []
    message_types: list[str] = []

    for msg in response.messages:
        message_types.append(msg.type)
        if msg.type == "text":
            response_texts.append(msg.content)
        elif msg.type == "choices":
            choices.extend(item.label for item in msg.items)

    return (
        "\n".join(response_texts),
        " | ".join(choices),
        "|".join(message_types),
        "",
    )


# ─── 세그먼트·학년 그룹 계산 ──────────────────────────────────────────────────

def _derive_labels(record: dict) -> tuple[str, str]:
    from app.services.nodes.classify import get_grade_group, get_segment
    profile = record["profile"]
    pattern = record["learning_pattern"]
    return get_segment(profile, pattern).value, get_grade_group(profile["grade"]).value


# ─── 메인 실행 ────────────────────────────────────────────────────────────────

def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"scenario_results_{timestamp}.csv"

    print(f"\n{'='*70}")
    print(f"  LangGraph 시나리오 러너 (Solar Pro2)")
    print(f"  학생 {len(STUDENT_IDS)}명 × 터치포인트 {len(TP_SCENARIOS)}종")
    print(f"  결과 저장: {csv_path}")
    print(f"{'='*70}")

    logger.info(
        "LangGraph scenario runner started",
        extra={
            "student_count": len(STUDENT_IDS),
            "scenario_count": len(TP_SCENARIOS),
            "csv_path": str(csv_path),
        },
    )

    all_rows: list[dict] = []

    for student_id in STUDENT_IDS:
        record = load_student(student_id)
        profile = record["profile"]
        pattern = record["learning_pattern"]
        wrong_pattern = record["wrong_answer_pattern"]
        task = record["today_tasks"][0] if record["today_tasks"] else {}

        segment_val, grade_group_val = _derive_labels(record)
        expected_segment, expected_grade_group = EXPECTED_CASES[student_id]
        classification_ok = (
            segment_val == expected_segment
            and grade_group_val == expected_grade_group
        )
        has_wrong = pattern["wrong_content_total"] > 0
        wrong_done_today = has_wrong and (
            pattern["wrong_content_done"] >= pattern["wrong_content_total"]
        )

        subject = task.get("subject", "")
        tp4_cause = TP4_CAUSE_BY_SUBJECT.get(subject, "too_long")
        tp4_thread_id = f"tp4-{student_id}-{uuid.uuid4()}"
        thread_ids: dict[Touchpoint, str] = {}

        print(f"\n  [{student_id}] {profile['name']} / {grade_group_val} / {segment_val}")
        if not classification_ok:
            print(
                "    [WARN] 기대 분류와 다름 "
                f"(expected {expected_grade_group} / {expected_segment})"
            )

        for use_case, touchpoint, turn, message_content, label in TP_SCENARIOS:
            if touchpoint == Touchpoint.TP4:
                thread_id = tp4_thread_id
            else:
                if touchpoint not in thread_ids:
                    thread_ids[touchpoint] = f"{touchpoint.value}-{student_id}-{uuid.uuid4()}"
                thread_id = thread_ids[touchpoint]

            actual_content = tp4_cause if message_content == "__cause__" else message_content

            try:
                response = _call_graph(
                    thread_id=thread_id,
                    student_id=student_id,
                    use_case=use_case,
                    touchpoint=touchpoint,
                    message_content=actual_content,
                )
                response_text, choices, message_types, error = _extract_response_fields(response)
            except Exception as exc:
                logger.exception(
                    "LangGraph scenario failed",
                    extra={
                        "student_id": student_id,
                        "use_case": use_case.value,
                        "touchpoint": touchpoint.value,
                        "turn": turn,
                    },
                )
                response_text = ""
                choices = ""
                message_types = ""
                error = str(exc)

            status = "[OK] " if not error else "[ERR]"
            tp4_info = f" [{tp4_cause}]" if touchpoint == Touchpoint.TP4 and turn == 2 else ""
            print(f"    {status} {label}{tp4_info}")
            if response_text:
                preview = response_text[:80].replace("\n", " ")
                print(f"      → {preview}{'...' if len(response_text) > 80 else ''}")
            if error:
                print(f"      오류: {error}")

            all_rows.append({
                "runner_mode": "graph",
                "student_id": student_id,
                "name": profile["name"],
                "grade": profile["grade"],
                "grade_group": grade_group_val,
                "segment": segment_val,
                "expected_grade_group": expected_grade_group,
                "expected_segment": expected_segment,
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
                "task_subject": subject,
                "task_unit": task.get("unit", ""),
                "task_difficulty": task.get("difficulty", ""),
                "ai_predicted_score": task.get("ai_predicted_score", ""),
                "touchpoint": touchpoint.value,
                "use_case": use_case.value,
                "turn": turn,
                "tp4_cause": tp4_cause if touchpoint == Touchpoint.TP4 and turn == 2 else "",
                "scenario_label": label,
                "has_wrong_answers": has_wrong,
                "wrong_content_done_today": wrong_done_today,
                "response_text": response_text,
                "choices": choices,
                "message_types": message_types,
                "error": error,
            })

    # CSV 저장
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    total = len(all_rows)
    errors = sum(1 for r in all_rows if r["error"])
    classification_errors = sum(1 for r in all_rows if not r["classification_ok"])

    logger.info(
        "LangGraph scenario runner completed",
        extra={
            "total": total,
            "errors": errors,
            "classification_errors": classification_errors,
            "csv_path": str(csv_path),
        },
    )

    print(f"\n{'='*70}")
    print(f"  완료: {total}개 시나리오, 오류: {errors}개, 분류 불일치: {classification_errors}개")
    print(f"  CSV 저장됨: {csv_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
