# 워크로그 — feature/T10-chat-api

**날짜**: 2026-04-28
**작업자**: Luke
**브랜치**: feature/T10-chat-api

---

## 작업 개요

LangGraph 그래프를 FastAPI `/chat` 엔드포인트에 연결하고 SSE(Server-Sent Events)로 `ChatResponse`를 스트리밍하는 T10 구현.

---

## 구현 세부

### 엔드포인트 흐름

1. `POST /chat` → `ChatRequest` 역직렬화
2. `load_student(request.student_id)` 선행 검증 → 없으면 404
3. `initial_state` 구성 — `request.message.content`가 있으면 `HumanMessage`로 변환해 `chat_history`에 주입
4. `graph.astream(initial_state, config)` 비동기 스트리밍
5. 각 이벤트의 노드 출력에서 `response` 키를 탐지 → `data: {json}\n\n` 형식으로 SSE 전송

### 에러 처리

| 케이스 | 처리 |
|---|---|
| `student_id` 미존재 | 스트리밍 전 `HTTPException(404)` |
| LLM / 그래프 오류 | `logger.exception()` + 예외 재전파 |

### 알려진 제약

`classify` 노드가 매 요청마다 `chat_history: []`를 리셋하기 때문에, TP4의 다중 턴 원인 감지 플로우(`chat_history`로 원인 선택 전달)는 현재 API 단일 호출로는 동작하지 않음. 다중 턴 지원은 T11 이후 `classify` 설계 변경 시 재논의 필요.

---

## 테스트 결과

```
uv run pytest tests/test_chat_api.py -v
============================== 6 passed in 0.07s ==============================

uv run pytest
============================= 126 passed in 1.88s ==============================
```

---

## 변경 파일

- `app/api/__init__.py` [신규]
- `app/api/routes/__init__.py` [신규]
- `app/api/routes/chat.py` [신규]
- `app/main.py` [수정] — chat_router include
- `tests/test_chat_api.py` [신규]
- `TODO.md` [수정] — T10 체크박스 완료 처리
