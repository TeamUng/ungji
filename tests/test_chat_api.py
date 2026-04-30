from __future__ import annotations

import json
from unittest.mock import patch

from app.core.enums import MessageType, Touchpoint, UseCase
from app.schemas.chat import ChatResponse, TextMessage


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────

def _parse_sse(body: str) -> list[dict]:
    """SSE body에서 data 이벤트를 파싱해 dict 리스트로 반환한다."""
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def _post_chat(client, student_id: str, use_case: UseCase, touchpoint: Touchpoint,
               thread_id: str, content: str = "", context: dict | None = None):
    return client.post("/chat", json={
        "thread_id": thread_id,
        "student_id": student_id,
        "use_case": use_case.value,
        "current_touchpoint": touchpoint.value,
        "message": {"type": MessageType.INIT.value, "content": content},
        **({"context": context} if context is not None else {}),
    })


def _patch_student(student):
    """load_student를 chat 라우터와 classify 노드 양쪽에서 패치한다."""
    return (
        patch("app.api.routes.chat.load_student", return_value=student),
        patch("app.services.nodes.classify.load_student", return_value=student),
    )


# ─── 케이스 1: 홈화면 진입 e2e ───────────────────────────────────────────────

def test_case1_home_screen_returns_sse(client, case1_student, mock_llm):
    p1, p2 = _patch_student(case1_student)
    with p1, p2:
        response = _post_chat(
            client, case1_student["student_id"],
            UseCase.TALK, Touchpoint.TP1,
            thread_id="case1-tp1-home",
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _parse_sse(response.text)
    assert len(events) >= 1

    msg_types = [m["type"] for m in events[0]["messages"]]
    assert "text" in msg_types


def test_case1_home_screen_thread_id_in_response(client, case1_student, mock_llm):
    thread_id = "case1-thread-abc"
    p1, p2 = _patch_student(case1_student)
    with p1, p2:
        response = _post_chat(
            client, case1_student["student_id"],
            UseCase.TALK, Touchpoint.TP1,
            thread_id=thread_id,
        )

    events = _parse_sse(response.text)
    assert events[0]["thread_id"] == thread_id


def test_chat_request_context_is_passed_to_graph(client, case2_student):
    class FakeGraph:
        initial_state = None

        async def astream(self, initial_state, config):
            self.initial_state = initial_state
            yield {
                "fake": {
                    "response": ChatResponse(
                        thread_id=initial_state["thread_id"],
                        messages=[TextMessage(content="ok")],
                    )
                }
            }

    fake_graph = FakeGraph()
    context = {
        "completed_task_refs": [
            {
                "subject": case2_student["today_tasks"][0]["subject"],
                "unit": case2_student["today_tasks"][0]["unit"],
            }
        ],
        "current_task_remaining_count": 2,
        "current_problem_id": case2_student["today_tasks"][0]["problem_id"],
    }

    with (
        patch("app.api.routes.chat.load_student", return_value=case2_student),
        patch("app.api.routes.chat.graph", fake_graph),
    ):
        response = _post_chat(
            client,
            case2_student["student_id"],
            UseCase.LEARNING,
            Touchpoint.TP4,
            thread_id="context-passthrough",
            context=context,
        )

    assert response.status_code == 200
    assert fake_graph.initial_state["request_context"].current_task_remaining_count == 2
    assert fake_graph.initial_state["request_context"].current_problem_id == (
        case2_student["today_tasks"][0]["problem_id"]
    )


# ─── 케이스 2: 학습 중 도움 요청 e2e ─────────────────────────────────────────

def test_case2_learning_tp4_returns_sse(client, case2_student, mock_llm):
    mock_llm.next_tool_calls = [
        {
            "name": "send_causes",
            "args": {
                "items": [
                    {"id": "no_concept", "label": "개념을 모르겠어요"},
                    {"id": "hard_calc", "label": "계산이 어려워요"},
                ]
            },
        }
    ]
    p1, p2 = _patch_student(case2_student)
    with p1, p2:
        response = _post_chat(
            client, case2_student["student_id"],
            UseCase.LEARNING, Touchpoint.TP4,
            thread_id="case2-tp4-first",
            context={
                "current_problem_id": case2_student["today_tasks"][0]["problem_id"],
            },
        )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert len(events) >= 1

    # 원인 미선택 → send_causes 도구 응답 → choices 메시지
    msg_types = [m["type"] for m in events[0]["messages"]]
    assert "choices" in msg_types


def test_case2_learning_tp4_response_has_messages(client, case2_student, mock_llm):
    p1, p2 = _patch_student(case2_student)
    with p1, p2:
        response = _post_chat(
            client, case2_student["student_id"],
            UseCase.LEARNING, Touchpoint.TP4,
            thread_id="case2-tp4-msg-check",
        )

    events = _parse_sse(response.text)
    assert "messages" in events[0]
    assert len(events[0]["messages"]) >= 1


# ─── 에러 핸들링 ──────────────────────────────────────────────────────────────

def test_unknown_student_id_returns_404(client):
    response = _post_chat(
        client, "존재하지않는학생ID",
        UseCase.TALK, Touchpoint.TP1,
        thread_id="unknown-student-thread",
    )
    assert response.status_code == 404


def test_404_detail_mentions_student(client):
    response = _post_chat(
        client, "ghost-student-999",
        UseCase.TALK, Touchpoint.TP1,
        thread_id="ghost-student-thread",
    )
    assert response.status_code == 404
    assert "student" in response.json()["detail"].lower()
