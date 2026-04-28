# 워크로그 — feature/T6-tp4-node

**날짜**: 2026-04-28
**작업자**: Luke
**브랜치**: feature/T6-tp4-node

---

## 작업 개요

TP4 노드(학습 중 도움 요청) 구현. 케이스 1(저학년 국어, 못함+불성실)과 케이스 2(고학년 수학, 못함+성실)에서 막힘 원인을 선택지로 진단하고, 원인별로 분기 코칭 응답을 반환한다.

---

## 구현 세부

### 흐름

1. **1단계 (원인 미선택)**: `chat_history`에 원인 HumanMessage가 없으면 `build_placeholder_messages`로 진단 선택지 4종 반환
2. **2단계 (원인 선택 후)**: 마지막 HumanMessage의 content가 알려진 cause ID이면 원인별 분기 코칭 응답 조립
3. **3단계 (teach-back)**: `Segment.LOW_DILIGENT` + 수학 원인 조합이면 마지막에 teach-back TextMessage 자동 추가

### 원인 → 메시지 타입

| cause | 응답 타입 |
|---|---|
| `too_long` | TextMessage |
| `dont_get_situation` | TextMessage + ImageCardMessage |
| `dont_get_feeling` | TextMessage + ChoicesMessage(감정 좁히기) |
| `dont_want_now` | TextMessage |
| `confused_concept` | TextMessage |
| `find_compare_numbers` | TextMessage |
| `build_expression` | TextMessage + HintCardMessage(3단계) |
| `check_calculation` | TextMessage |

### 설계 결정

- `chat_history`의 마지막 `HumanMessage.content`로 원인을 감지 — 별도 ChatState 필드 추가 없이 LangGraph 표준 state 활용
- 메시지 타입 구조는 코드에서 고정, 텍스트 내용은 LLM 생성 (SEGMENT_RESPONSE_POLICY.md 원칙 준수)
- 내부 세그먼트명(LOW_LAZY 등)은 응답 메시지 어디에도 노출하지 않음

---

## 테스트 결과

```
uv run pytest tests/test_tp4.py -v
============================= 15 passed in 0.08s ==============================

uv run pytest
============================= 78 passed in 4.41s ==============================
```

---

## 변경 파일

- `app/services/nodes/tp4.py` [신규]
- `tests/test_tp4.py` [신규]
- `TODO.md` [수정] — T6 체크박스 완료 처리
