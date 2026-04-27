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

## 3. 추천 디렉토리 구조

```
app/
  main.py                     # FastAPI 앱 (현재 그대로)
  core/                       # config, logging (현재 그대로)
  middleware/                  # request_logger (현재 그대로)
  api/routes/
    chat.py                   # POST /chat 엔드포인트
  schemas/
    chat.py                   # ChatRequest, ChatResponse, ChoiceButton
    student.py                # StudentProfile, StudentType enum
  services/
    graph.py                  # LangGraph StateGraph 정의 (단일 그래프)
    nodes/
      classify.py             # 학생 유형 판단 노드
      home_coach.py           # 홈화면 코칭 노드
      learning_coach.py       # 학습 중 코칭 노드
      diagnose.py             # 막힘 원인 진단 노드
    prompts/
      personas.py             # 학년별 페르소나/말투
      coaching.py             # 유형별 코칭 프롬프트
  clients/
    upstage.py                # ChatUpstage 인스턴스
  data/
    mock_students.json        # 목업 학생 데이터
    mock_problems.json        # 목업 문제/해설 데이터
```

---

## 4. 그래프 흐름 (현재 이해)

```
[진입] → [학생유형판단] → [홈화면/학습중 분기]
  ├─ 홈화면: [유형별 선택지 생성] → [선택 처리] → [학습 시작]
  └─ 학습중: [막힘 원인 진단] → [원인별 코칭 분기]
       ├─ 개념부족: [쉬운설명] → [이해확인(teach-back)]
       ├─ 계산오류: [검산유도]
       └─ 회피/이탈: [초소형목표제안]
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
  "entry_point": "home",
  "message": {
    "type": "choice",
    "content": "비율 개념 쉽게 다시 보기"
  }
}
```

- `thread_id`: 대화 세션 식별 (프론트에서 UUID 생성)
- `student_id`: 학생 식별 (mock 데이터 조회용)
- `entry_point`: 첫 메시지에만 포함 (`"home"` | `"learning"` | `"complete"`), 이후 생략 가능
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

## 7. 미결 논의 사항

| # | 안건 | 상태 |
| --- | --- | --- |
| 7-1 | PRD 1-4의 코칭 레이어 4개를 독립 LangGraph 노드로 분리할지, 프롬프트 분기로 처리할지 | 미결 |
| 7-2 | 케이스 1/2의 mock_problems.json 데이터 형태 구체화 | 미결 |
| 7-3 | 두 케이스 간 공유 로직 범위 (어디까지 공통, 어디부터 과목/학년 특화) | 미결 |
| 7-4 | `config.py`에 `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` 추가 | 미결 (구현 시 처리) |

---

## 8. 다음 단계

1. ~~핵심 설계 결정~~ → 완료 (섹션 5)
2. 미결 논의 사항 합의 (섹션 7)
3. 의존성 추가 (`uv add langgraph langchain-upstage langsmith`)
4. LangGraph 그래프 스켈레톤 구현
5. 케이스 1, 케이스 2 목업 데이터 작성
6. API 엔드포인트 구현 (POST /chat + SSE)
7. 프론트엔드 챗봇 UI 구현
