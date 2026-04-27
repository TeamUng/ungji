# 아키텍처 검토 및 논의 사항

> PRD 기반 기술 스택 검토 결과 + 구체화가 필요한 논의 포인트 정리

---

## 1. 확정된 기술 스택

| 영역 | 선택 | 비고 |
| --- | --- | --- |
| 프론트엔드 | Next.js (App Router) on Vercel | 팀 숙련도에 따라 React+Vite도 가능 |
| 백엔드 | FastAPI + LangGraph (서버 상태 관리) | 현재 스캐폴드 그대로 활용 |
| LLM | langchain-upstage (ChatUpstage) | Upstage Solar Pro, OpenAI-compatible |
| 상태/DB | JSON 목업 데이터 + LangGraph InMemorySaver | DB 없이 MVP 진행, 추후 Supabase 전환 가능 |
| 에이전트 | 단일 LangGraph StateGraph + 조건부 라우팅 | 2개 MVP 케이스를 하나의 그래프로 처리 |
| 추적 | LangSmith 트레이싱 | .env에 키 설정 완료 |
| 테스트 | pytest (로직) + LangSmith Evaluation (LLM 품질) | LLM-as-a-judge 포함 |

---

## 2. 추가 의존성

```toml
# pyproject.toml에 추가 예정
"langgraph>=0.4",
"langchain-upstage>=0.3",
"langsmith>=0.3",
```

- Pydantic v2 (2.13.3)와 호환 확인됨
- LangServe는 신규 프로젝트 비추천 → 배제

---

## 3. 확정 디렉토리 구조

```
app/
  main.py                     # FastAPI 앱
  core/                       # config, constants, enums, logging ✅ 완료
  middleware/                  # request_logger ✅ 완료
  schemas/
    chat.py                   # ChatState, ChatRequest, ChatResponse, 응답 메시지 4종 ✅ 완료
    student.py                # StudentProfile, LearningHistory, LearningPattern, WrongAnswerPattern ✅ 완료
  api/
    routes/
      chat.py                 # POST /chat 엔드포인트 (T10)
  services/
    graph.py                  # LangGraph StateGraph + 조건부 라우팅 (T9)
    nodes/
      common.py               # 응답 builder + 세그먼트 출력 정책 helper (T4.5)
      classify.py             # 학생 데이터 로드 + segment/grade_group 판별 + State 초기화 (T4)
      tp1.py                  # 홈화면 진입 — 환영 메시지 + 세그먼트별 선택지 (T5)
      tp2.py                  # 단위 학습 완료 — 진행률 축하 + 다음 학습 제안 (T7)
      tp3.py                  # 이탈 시도 감지 — 리텐션 메시지 (T7)
      tp4.py                  # 학습 중 도움 요청 — 막힘 원인 선택지 + 원인별 분기 코칭 (T6)
      tp5.py                  # 오늘 학습 종료 — 오답 복습 유도 3분기 (T7)
    prompts/
      personas.py             # 학년 그룹별 말투 시스템 프롬프트 (T3)
      coaching.py             # 세그먼트별 코칭 전략 프롬프트 (T3)
  clients/
    upstage.py                # ChatUpstage 인스턴스 + LangSmith 트레이싱 (T2)
  data/
    loader.py                 # load_student(), load_problem() (T1)
    mock_students.json        # 목업 학생 데이터 — 빈 배열, 케이스 1·2 데이터 추후 입력 (T1)
    mock_problems.json        # 목업 문제·해설·힌트·단계별 풀이 — 빈 배열, 추후 입력 (T1)
```

---

## 4. 그래프 흐름

```
[진입] POST /chat { use_case, current_touchpoint, ... }
  ↓
[classify 노드] — student_id로 mock 데이터 로드, segment/grade_group 판별, State 초기화
  ↓
[라우팅] use_case + current_touchpoint 기준 분기
  ├─ talk  / tp1 → [TP1 노드] 환영 메시지 + 세그먼트별 선택지
  ├─ talk  / tp2 → [TP2 노드] 진행률 축하 + 다음 학습 제안
  ├─ talk  / tp3 → [TP3 노드] 리텐션 메시지
  ├─ talk  / tp5 → [TP5 노드] 오답 복습 유도 (3분기)
  │                  ├─ 오답 없음 → "오늘 다 맞았어!"
  │                  ├─ 오답 있음 + 복습 완료 → "오답 N개 다 끝냈어!"
  │                  └─ 오답 있음 + 복습 미진행 → "N개 중 M개 남았어!"
  └─ learning / tp4 → [TP4 노드] 막힘 원인 선택지 → 원인별 분기 코칭
                       ├─ 개념 부족: 쉬운 설명 + 비유 + 단계별 풀이
                       ├─ 계산 오류: 검산 유도
                       ├─ 문제 이해 실패: 핵심 조건 재확인
                       └─ 회피/이탈: 초소형 목표 제안 → teach-back 유도
```

---

## 5. 논의 안건 및 결과

### 5-1. API 설계

| 안건 | 선택지 | 결과 |
| --- | --- | --- |
| 진입 시점을 API에서 어떻게 구분? | A) 단일 `/chat` 엔드포인트 (context 파라미터로 구분)<br>B) 엔드포인트 분리 (`/chat/home`, `/chat/learning`, `/chat/complete`) | **A) 단일 `/chat`** — 홈→학습 전환 시 세션 유지에 유리, LangGraph thread_id 기반 상태 관리와 자연스럽게 맞음 |
| 대화 턴 처리 방식? | A) 매 턴 API 호출 (REST)<br>B) WebSocket 실시간 | **A) 매 턴 API 호출** — 단순하고 예측 가능, MVP에 적합 |
| LLM 응답 스트리밍? | A) 필요 없음 (한 번에 응답)<br>B) 있으면 좋겠음 (SSE)<br>C) 필수 | **B) SSE로 구현** — UX 자연스러움, FastAPI StreamingResponse로 구현 가능 |
| 챗봇 응답이 복수 메시지? | A) 한 번에 복수 메시지 (배열)<br>B) 항상 단일 메시지 | **A) 복수 메시지 배열** — 환영 메시지 + 선택지 버튼을 한 응답에 담을 수 있음 |

### 5-2. 학생 유형 판단

| 안건 | 선택지 | 결과 |
| --- | --- | --- |
| 페르소나 수? | A) PRD 활성화 유형 4개<br>B) 취소선 유형 포함 5개 이상 | **A) 4개** — 모범, 고성취+불성실, 저성취+성실, 공부안하는학생 |
| 유형 선택 방식? | A) 백엔드 mock 데이터 기반 (student_id로 조회 후 서버가 판단)<br>B) 프론트 드롭다운 선택<br>C) 두 가지 모두 | **A) 백엔드 mock 데이터 기반** — student_id 전달 → 서버가 정답률/완료율/건너뛰기 등 데이터로 유형 판단. 개별화된 것처럼 보이는 효과 |
| 판단 시점? | A) 세션 시작 시 1회<br>B) 매 대화마다 재판단 | **A) 세션 시작 시 1회** — 첫 진입 시 mock 데이터 기반 판단 후 해당 세션 동안 유지 |

### 5-3. 해설/코칭 데이터 방식

| 안건 | 선택지 | 결과 |
| --- | --- | --- |
| 문제 해설/풀이 안내 방식? | A) 미리 준비된 해설 데이터만 사용<br>B) LLM이 직접 생성<br>C) 혼합 | **C) 혼합** — 기본 해설/힌트/단계별 풀이는 `mock_problems.json`에 미리 작성, 학생 반응에 따른 추가 설명(비유, 쉬운 표현, 격려)은 LLM이 해설 데이터를 참고하여 학년/유형 말투로 생성 |

---

## 6. 합의 기반 API 구조 (초안)

### Request

```json
{
  "thread_id": "abc-123",
  "student_id": "student_01",
  "use_case": "talk",
  "current_touchpoint": "tp1",
  "message": {
    "type": "init",
    "content": ""
  }
}
```

- `thread_id`: 대화 세션 식별 (프론트에서 UUID 생성)
- `student_id`: 학생 식별 (mock 데이터 조회용)
- `use_case`: `"talk"` (tp1/tp2/tp3/tp5) | `"learning"` (tp4)
- `current_touchpoint`: `"tp1"` | `"tp2"` | `"tp3"` | `"tp4"` | `"tp5"`
- `message.type`: `"init"` (첫 진입) | `"text"` (자유 입력) | `"choice"` (선택지 클릭)

### Response (SSE 스트림)

```json
{
  "thread_id": "abc-123",
  "messages": [
    {
      "type": "text",
      "content": "안녕! 오늘도 같이 공부해볼까?"
    },
    {
      "type": "choices",
      "items": [
        {"id": "c1", "label": "3분만 가볍게 시작하기"},
        {"id": "c2", "label": "아주 쉬운 문제 1개만 풀기"},
        {"id": "c3", "label": "AI가 오늘 할 것 골라주기"}
      ]
    },
    {
      "type": "image_card",
      "image_url": "/assets/mock/story_01.png",
      "caption": "토끼가 울고 있어요"
    },
    {
      "type": "hint_card",
      "steps": [
        {"step": 1, "content": "먼저 문제에서 비교하는 두 수를 찾아보자"},
        {"step": 2, "content": "두 수의 관계를 비율로 나타내보자"}
      ]
    }
  ]
}
```

---

## 7. 논의 사항 결과

| # | 안건 | 상태 | 결정 내용 |
| --- | --- | --- | --- |
| 7-1 | PRD 1-4의 코칭 레이어 4개를 독립 LangGraph 노드로 분리할지, 프롬프트 분기로 처리할지 | ✅ 결정 | **TP4 단일 노드 내 프롬프트 분기**로 처리 — 막힘 원인별 응답을 TP4 노드 안에서 분기 (별도 노드 분리 없음) |
| 7-2 | 케이스 1/2의 mock_problems.json 데이터 형태 구체화 | 🔲 미결 | 테스트 시나리오 확정 후 작성 (STATE_DESIGN 8-2) |
| 7-3 | 두 케이스 간 공유 로직 범위 (어디까지 공통, 어디부터 과목/학년 특화) | ✅ 결정 | **classify 노드 공통**, TP1~TP5 노드는 과목 무관하게 동일 로직 — 과목·학년 특화는 프롬프트와 mock 데이터로 처리 |
| 7-4 | `config.py`에 `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` 추가 | ✅ 결정 | T2 구현 시 처리 |
| 7-5 | 세그먼트별 응답 형태를 어디서 관리할지 | ✅ 결정 | PRD는 요구사항 원천으로 유지하고, 실제 출력 형태와 팀 고도화 기준은 `docs/SEGMENT_RESPONSE_POLICY.md` + `nodes/common.py` helper에서 관리 |

---

## 8. 구현 현황

| Phase | 내용 | 상태 |
| --- | --- | --- |
| Phase 0 | enums, constants, schemas (ChatState, 응답 4종), pyproject.toml | ✅ 완료 |
| Phase 1 | T1(데이터 로더), T2(Upstage 클라이언트), T3(프롬프트) | 🔲 진행 예정 |
| Phase 1.5 | T4.5(응답 builder + 세그먼트 출력 정책) | 🔲 진행 예정 |
| Phase 2 | T4(classify), T5(TP1), T6(TP4), T7(TP2/3/5), T8(conftest) | 🔲 Phase 1 완료 후 |
| Phase 3 | T9(LangGraph StateGraph 조립) | 🔲 Phase 2 완료 후 |
| Phase 4 | T10(POST /chat + SSE) | 🔲 Phase 3 완료 후 |
| Phase 5 | T11(프론트엔드 챗봇 UI) | 🔲 Phase 4 완료 후 |
