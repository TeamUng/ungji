"""
E2E 시나리오 러너 — 모든 학생 × 터치포인트 조합을 실행하고 결과를 CSV로 저장한다.

사용법:
    uv run python scripts/run_scenarios.py

출력:
    - 터미널: 각 시나리오 결과 실시간 출력
    - scripts/results/scenario_results_YYYYMMDD_HHMMSS.csv
"""

from __future__ import annotations

import csv
import io
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Windows 터미널 한글·이모지 출력을 위해 stdout을 UTF-8로 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.main import app
from app.data.loader import load_student

# ─── 설정 ─────────────────────────────────────────────────────────────────────

STUDENT_IDS = [
    "lower-low-lazy",
    "lower-low-diligent",
    "lower-high-lazy",
    "lower-high-diligent",
    "upper-low-lazy",
    "upper-low-diligent",
    "upper-high-lazy",
    "upper-high-diligent",
]

# 터치포인트별 (use_case, touchpoint, turn, message_content, label)
# TP4는 2턴: 1턴(원인 선택지 요청) + 2턴(원인 선택)
# TP4 cause는 학생 과목에 따라 결정 (국어→too_long, 수학→confused_concept)
TP_SCENARIOS = [
    ("talk",     "tp1", 1, "",           "TP1 홈화면 진입"),
    ("talk",     "tp2", 1, "",           "TP2 단위 학습 완료"),
    ("talk",     "tp3", 1, "",           "TP3 이탈 방지"),
    ("learning", "tp4", 1, "",           "TP4 막힘 (원인 선택지)"),
    ("learning", "tp4", 2, "__cause__",  "TP4 막힘 (원인 선택 후 코칭)"),
    ("talk",     "tp5", 1, "",           "TP5 학습 종료"),
]

# 과목별 TP4 원인 ID
TP4_CAUSE_BY_SUBJECT = {
    "국어": "too_long",
    "수학": "confused_concept",
}

# ─── 결과 저장 경로 ───────────────────────────────────────────────────────────

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CSV_COLUMNS = [
    "student_id", "name", "grade", "grade_group", "segment",
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

# ─── SSE 파싱 ─────────────────────────────────────────────────────────────────

def _parse_sse(raw: str) -> dict | None:
    for line in raw.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                pass
    return None


# ─── API 호출 ─────────────────────────────────────────────────────────────────

def _call_api(
    client: TestClient,
    thread_id: str,
    student_id: str,
    use_case: str,
    touchpoint: str,
    message_content: str,
) -> dict | None:
    payload = {
        "thread_id": thread_id,
        "student_id": student_id,
        "use_case": use_case,
        "current_touchpoint": touchpoint,
        "message": {"type": "init" if not message_content else "choice", "content": message_content},
    }
    with client.stream("POST", "/chat", json=payload) as resp:
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        raw = resp.read().decode("utf-8")
        return _parse_sse(raw)


# ─── 세그먼트·학년 그룹 계산 (분류 결과 표시용) ──────────────────────────────

def _derive_labels(record: dict) -> tuple[str, str]:
    from app.services.nodes.classify import get_grade_group, get_segment
    profile = record["profile"]
    pattern = record["learning_pattern"]
    segment = get_segment(profile, pattern)
    grade_group = get_grade_group(profile["grade"])
    return segment.value, grade_group.value


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"scenario_results_{timestamp}.csv"

    print(f"\n{'='*70}")
    print(f"  E2E 시나리오 러너  |  학생 {len(STUDENT_IDS)}명 × 터치포인트 {len(TP_SCENARIOS)}종")
    print(f"  결과 저장: {csv_path}")
    print(f"{'='*70}\n")

    rows: list[dict] = []

    with TestClient(app) as client:
        for student_id in STUDENT_IDS:
            record = load_student(student_id)
            profile = record["profile"]
            pattern = record["learning_pattern"]
            wrong_pattern = record["wrong_answer_pattern"]
            task = record["today_tasks"][0] if record["today_tasks"] else {}

            segment_val, grade_group_val = _derive_labels(record)
            has_wrong = pattern["wrong_content_total"] > 0
            wrong_done_today = has_wrong and (
                pattern["wrong_content_done"] >= pattern["wrong_content_total"]
            )

            subject = task.get("subject", "")
            tp4_cause = TP4_CAUSE_BY_SUBJECT.get(subject, "too_long")

            # 같은 학생의 다중 턴(TP4)은 같은 thread_id를 공유해야 한다
            tp4_thread_id = f"tp4-{student_id}-{uuid.uuid4()}"
            # 나머지 터치포인트는 각각 독립 thread_id
            thread_ids: dict[str, str] = {}

            print(f"▶ {student_id} ({profile['name']}, {grade_group_val}, {segment_val})")

            for use_case, touchpoint, turn, message_content, label in TP_SCENARIOS:
                # TP4는 같은 thread_id 재사용, 나머지는 터치포인트별 고유
                if touchpoint == "tp4":
                    thread_id = tp4_thread_id
                else:
                    key = f"{touchpoint}"
                    if key not in thread_ids:
                        thread_ids[key] = f"{touchpoint}-{student_id}-{uuid.uuid4()}"
                    thread_id = thread_ids[key]

                # TP4 2턴의 실제 원인 ID 치환
                actual_content = tp4_cause if message_content == "__cause__" else message_content

                try:
                    result = _call_api(client, thread_id, student_id, use_case, touchpoint, actual_content)
                except Exception as exc:
                    result = {"error": str(exc)}

                # 응답 파싱
                error = ""
                response_text = ""
                choices = ""
                message_types = ""

                if result is None:
                    error = "SSE 응답 파싱 실패"
                elif "error" in result:
                    error = result["error"]
                else:
                    messages = result.get("messages", [])
                    message_types = "|".join(m.get("type", "") for m in messages)
                    for msg in messages:
                        if msg.get("type") == "text":
                            response_text = msg.get("content", "")
                        elif msg.get("type") == "choices":
                            choices = " | ".join(
                                item.get("label", "") for item in msg.get("items", [])
                            )

                # 터미널 출력
                status = "[OK] " if not error else "[ERR]"
                tp4_info = f" [{tp4_cause}]" if touchpoint == "tp4" and turn == 2 else ""
                print(f"  {status} {label}{tp4_info}")
                if response_text:
                    preview = response_text[:80].replace("\n", " ")
                    print(f"    → {preview}{'...' if len(response_text) > 80 else ''}")
                if choices:
                    print(f"    선택지: {choices}")
                if error:
                    print(f"    오류: {error}")

                rows.append({
                    "student_id": student_id,
                    "name": profile["name"],
                    "grade": profile["grade"],
                    "grade_group": grade_group_val,
                    "segment": segment_val,
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
                    "touchpoint": touchpoint,
                    "use_case": use_case,
                    "turn": turn,
                    "tp4_cause": tp4_cause if touchpoint == "tp4" and turn == 2 else "",
                    "scenario_label": label,
                    "has_wrong_answers": has_wrong,
                    "wrong_content_done_today": wrong_done_today,
                    "response_text": response_text,
                    "choices": choices,
                    "message_types": message_types,
                    "error": error,
                })

            print()

    # CSV 저장
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    errors = sum(1 for r in rows if r["error"])
    print(f"{'='*70}")
    print(f"  완료: {total}개 시나리오, 오류: {errors}개")
    print(f"  CSV 저장됨: {csv_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
