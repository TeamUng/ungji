# TODO

## 구현 목표

PRD 케이스 1·2가 처음부터 끝까지 작동하는 것.

| 케이스 | 대상 | 세그먼트 | 흐름 |
|--------|------|---------|------|
| 케이스 1 | 초1~2 / 국어 / 짧은 글 읽기 | 못함+불성실 | 홈화면 → 쉬운 국어 활동 제안 → 학습 중 막힘 → 선택지+쉬운 설명 |
| 케이스 2 | 초5~6 / 수학 / 비율·비례식 | 못함+성실 | 홈화면 → 비율 약점 보완 제안 → 학습 중 막힘 → 단계별 코칭+teach-back |

---

## Phase 0 — 완료 ✅

- [x] `app/core/enums.py` 신규 — Segment, GradeGroup, UseCase, Touchpoint, Subject, Difficulty, WrongCause, MessageType
- [x] `app/core/constants.py` 신규 — 세그먼트 판별 임계값, 학년 그룹 경계, recent_period=7
- [x] `app/schemas/student.py` 신규 — StudentProfile, LearningHistory, LearningPattern, WrongAnswerPattern TypedDict
- [x] `app/schemas/chat.py` 신규 — Task, ChatState (LangGraph), ChatRequest, ChatResponse, 응답 메시지 4종 (Pydantic)
- [x] `pyproject.toml` 수정 — langgraph, langchain-upstage, langsmith 추가

---

## Phase 1 — 기반 세팅 (T1·T2·T3 병렬 진행)

> T1·T2·T3 완료 후 Phase 2 시작 가능

---

### T1. 데이터 로더

> mock JSON의 구조를 확정하고 로더 코드 작성. 실제 데이터는 별도 제공 예정.

**브랜치**: `feature/T1-data-loader`
**담당 파일**: `app/data/__init__.py`, `app/data/loader.py`, `tests/test_loader.py`
**의존**: 없음 | **블로킹**: T4, T5, T6, T7, T8

- [x] `app/data/` 디렉토리 생성 및 `__init__.py` 추가
- [x] `mock_students.json` JSON 스키마 정의 (StudentProfile + LearningHistory + LearningPattern + WrongAnswerPattern 구조 기반, 데이터는 빈 배열로)
- [x] `mock_problems.json` JSON 스키마 정의 (문제·해설·힌트·단계별풀이 구조, 데이터는 빈 배열로)
- [x] `loader.py` — `load_student(student_id: str)` 구현 (StudentProfile 등 반환)
- [x] `loader.py` — `load_problem(problem_id: str)` 구현
- [x] `loader.py` — 존재하지 않는 ID 입력 시 명확한 예외(`KeyError` 또는 커스텀) 처리
- [x] `tests/test_loader.py` 작성 — 정상 조회 케이스
- [x] `tests/test_loader.py` 작성 — 존재하지 않는 ID 예외 케이스
- [x] **완료 기준**: `uv run pytest tests/test_loader.py` 통과

---

### T2. Upstage 클라이언트 + config 보완

> ChatUpstage 인스턴스를 생성하고 LangSmith 트레이싱을 연결한다.

**브랜치**: `feature/T2-upstage-client`
**담당 파일**: `app/clients/__init__.py`, `app/clients/upstage.py`, `app/core/config.py`, `.env.example`
**의존**: 없음 | **블로킹**: T5, T6, T7

- [x] `app/core/config.py` 수정 — `LANGSMITH_API_KEY: str = ""`, `LANGSMITH_PROJECT: str = ""` 추가
- [x] `.env.example` 수정 — 신규 키 항목 추가
- [x] `app/clients/` 디렉토리 생성 및 `__init__.py` 추가
- [x] `app/clients/upstage.py` — settings에서 키 읽어서 `ChatUpstage` 인스턴스 생성
- [x] `app/clients/upstage.py` — LangSmith 트레이싱 활성화 설정
- [ ] `tests/test_upstage_client.py` 작성 — 클라이언트 초기화 검증 (실제 API 호출은 mock)
- [ ] **완료 기준**: `from app.clients.upstage import llm` import 정상, `uv run pytest tests/test_upstage_client.py` 통과

---

### T3. 페르소나 + 코칭 프롬프트

> 학년 그룹별 말투와 세그먼트별 코칭 전략을 텍스트 함수로 정의한다.

**브랜치**: `feature/T3-prompts`
**담당 파일**: `app/services/__init__.py`, `app/services/prompts/__init__.py`, `app/services/prompts/personas.py`, `app/services/prompts/coaching.py`, `tests/test_prompts.py`
**의존**: 없음 | **블로킹**: T5, T6, T7

- [x] `app/services/` 및 `app/services/prompts/` 디렉토리 생성, `__init__.py` 추가
- [x] `personas.py` — `get_persona(grade_group: GradeGroup) -> str` 구현
  - [x] `lower` (1~2학년): 짧은 문장, 쉬운 단어, 이모처럼 다정하게, 한 번에 하나만
  - [x] `middle` (3~4학년): 친근한 친구/형, 선택지로 이유 말하게 유도
  - [x] `upper` (5~6학년): 존댓말 혼합, 차분한 코치형, 논리·존중 중심
- [x] `coaching.py` — `get_coaching_strategy(segment: Segment) -> str` 구현
  - [x] `못함+불성실`: 초소형 목표, 즉시 성공 경험, 짧은 대화, 흥미 기반
  - [x] `못함+성실`: 막힘 원인 진단, 단계별 설명, 격려, 쉬운 표현
  - [x] `잘함+불성실`: 짧고 명확한 시작점, 도전형 선택지
  - [x] `잘함+성실`: 칭찬+심화 문제, 사고 확장 질문
- [ ] `tests/test_prompts.py` 작성 — 3개 학년 그룹 × 4개 세그먼트 반환값 존재 검증
- [ ] `tests/test_prompts.py` — 케이스 1 (lower + 못함+불성실) 프롬프트 내용 검증
- [ ] `tests/test_prompts.py` — 케이스 2 (upper + 못함+성실) 프롬프트 내용 검증
- [ ] **완료 기준**: `uv run pytest tests/test_prompts.py` 통과

---

## Phase 1.5 — 공통 응답 골격 + 세그먼트 정책

> T5~T7을 각자 구현하기 전에, 세그먼트별 응답을 안정적으로 갈아 끼울 수 있는 공통 틀을 먼저 만든다.
> 세부 문구와 날카로운 코칭 기획은 팀 합의 후 `docs/SEGMENT_RESPONSE_POLICY.md` 기준으로 나눠 고도화한다.

---

### T4.5. 응답 builder + 세그먼트 출력 정책

> 메시지 타입과 선택지 구조는 코드에서 안정적으로 고정하고, 세그먼트별 문구·힌트 깊이·선택지 label은 팀 합의 후 고도화한다.

**브랜치**: `feature/T4-5-response-policy`
**담당 파일**: `docs/SEGMENT_RESPONSE_POLICY.md`, `app/services/nodes/common.py`, `tests/test_response_builders.py`
**의존**: Phase 0, T3 | **블로킹**: T5, T6, T7

- [x] `docs/SEGMENT_RESPONSE_POLICY.md` 작성 — 세그먼트별 출력 방향과 TP별 기본 정책 정리
- [x] `app/services/nodes/common.py` — `TextMessage`, `ChoicesMessage`, `ImageCardMessage`, `HintCardMessage` 생성 helper 구현
- [x] `app/services/nodes/common.py` — 선택지 `id`는 stable snake_case, 학생 노출 문구는 `label`로 분리
- [x] `app/services/nodes/common.py` — `segment + grade_group + current_touchpoint` 기반 기본 응답 정책 선택 helper 구현
- [x] `tests/test_response_builders.py` 작성 — 4개 메시지 타입 builder 검증
- [x] `tests/test_response_builders.py` 작성 — 내부 세그먼트명이 응답 label/content에 노출되지 않는지 검증
- [x] `tests/test_response_builders.py` 작성 — 케이스 1·2 기본 placeholder 응답 타입 검증
- [x] **완료 기준**: `uv run pytest tests/test_response_builders.py` 통과, T5~T7 노드가 공통 helper를 import해 사용할 수 있음

---

## Phase 2 — 노드 구현 (T1·T2·T3 완료 후, T4~T8 병렬 진행)

> T4~T8은 서로 간 의존 없음. 다만 T5~T7은 T4.5 공통 응답 골격을 먼저 공유하면 세그먼트별 고도화 시 충돌을 줄일 수 있다.

---

### T4. classify 노드

> student_id로 학생 데이터를 로드하고 세그먼트·학년 그룹을 판별해 State를 초기화한다.

**브랜치**: `feature/T4-classify-node`
**담당 파일**: `app/services/nodes/__init__.py`, `app/services/nodes/classify.py`, `tests/test_classify.py`
**의존**: T1 | **블로킹**: T9

- [ ] `app/services/nodes/` 디렉토리 생성 및 `__init__.py` 추가
- [ ] `tests/test_classify.py` 작성 — 케이스 1 학생 → `segment=못함+불성실`, `grade_group=lower` 검증
- [ ] `tests/test_classify.py` 작성 — 케이스 2 학생 → `segment=못함+성실`, `grade_group=upper` 검증
- [ ] `tests/test_classify.py` — 오답 없는 학생(wrong_content_rate=None) → 성실도 불이익 없음 검증
- [ ] `tests/test_classify.py` — 학년 경계값 (2→lower, 3→middle, 4→middle, 5→upper)
- [ ] `classify.py` — `load_student()`로 데이터 로드 후 `ChatState` 초기화
- [ ] `classify.py` — `constants.py` 임계값 기준 `segment` 판별 로직
- [ ] `classify.py` — `grade` → `grade_group` 변환 로직
- [ ] **완료 기준**: `uv run pytest tests/test_classify.py` 통과

---

### T5. TP1 노드 — 홈화면 진입

> 세그먼트·학년 그룹에 맞는 환영 메시지와 선택지를 생성한다. 케이스 1·2의 시작점.

**브랜치**: `feature/T5-tp1-node`
**담당 파일**: `app/services/nodes/tp1.py`, `tests/test_tp1.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [ ] `tests/test_tp1.py` 작성 — 케이스 1 (lower + 못함+불성실) → 응답에 `choices` 포함, 짧고 쉬운 말투 검증
- [ ] `tests/test_tp1.py` 작성 — 케이스 2 (upper + 못함+성실) → 응답에 `choices` 포함, 코치형 말투 검증
- [ ] `tests/test_tp1.py` — 케이스 1과 케이스 2의 선택지 내용이 다른지 검증
- [ ] `tp1.py` — `get_persona()` + `get_coaching_strategy()` 조합으로 시스템 프롬프트 구성
- [ ] `tp1.py` — 학생 이름·선호 과목·AI 예상점수·오늘 태스크 컨텍스트 주입
- [ ] `tp1.py` — 세그먼트별 선택지 생성 (PRD 1-5 + `docs/SEGMENT_RESPONSE_POLICY.md` 기준 4개 세그먼트 × 선택지)
- [ ] **완료 기준**: `uv run pytest tests/test_tp1.py` 통과, 응답에 `TextMessage` + `ChoicesMessage` 포함 확인

---

### T6. TP4 노드 — 학습 중 도움 요청

> 막힘 원인을 선택지로 진단하고 원인에 따라 분기 코칭한다. 케이스 1·2의 핵심 기능.

**브랜치**: `feature/T6-tp4-node`
**담당 파일**: `app/services/nodes/tp4.py`, `tests/test_tp4.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [ ] `tests/test_tp4.py` 작성 — 케이스 1 국어: 막힘 원인 선택지 4종 응답 검증
  - [ ] "글이 너무 길어" → `TextMessage` (문장 분리)
  - [ ] "무슨 상황인지 모르겠어" → `ImageCardMessage` 포함
  - [ ] "주인공 마음을 모르겠어" → `ChoicesMessage` (선택지 좁히기)
  - [ ] "그냥 하기 싫어" → `TextMessage` (초소형 목표)
- [ ] `tests/test_tp4.py` 작성 — 케이스 2 수학: 막힘 원인 선택지 4종 응답 검증
  - [ ] "비율 뜻이 헷갈려" → `TextMessage` (비유 설명)
  - [ ] "어떤 수끼리 비교해야 할지 모르겠어" → `TextMessage` (기준량/비교량 유도)
  - [ ] "식을 어떻게 세우는지 모르겠어" → `HintCardMessage` 포함
  - [ ] "계산하다가 틀렸어" → `TextMessage` (검산 유도)
- [ ] `tp4.py` — 1단계: 막힘 원인 선택지 제공 (케이스별 4종)
- [ ] `tp4.py` — 2단계: 케이스 1 국어 원인별 분기 코칭
- [ ] `tp4.py` — 2단계: 케이스 2 수학 원인별 분기 코칭 (해설 데이터 참조)
- [ ] `tp4.py` — 3단계: teach-back 유도 (수학, 마지막 단계에서 학생 설명 요청)
- [ ] `tp4.py` — 내부 세그먼트명 노출 없이 `docs/SEGMENT_RESPONSE_POLICY.md`의 세그먼트별 출력 형태 반영
- [ ] **완료 기준**: `uv run pytest tests/test_tp4.py` 통과, `HintCardMessage`·`ImageCardMessage` 타입 포함 확인

---

### T7. TP2 + TP3 + TP5 노드 — 보조 터치포인트

> 단위 학습 완료(TP2), 이탈 방지(TP3), 학습 종료(TP5) 세 노드를 구현한다.

**브랜치**: `feature/T7-tp2-tp3-tp5-nodes`
**담당 파일**: `app/services/nodes/tp2.py`, `tp3.py`, `tp5.py`, `tests/test_tp2.py`, `tests/test_tp3.py`, `tests/test_tp5.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [ ] `tests/test_tp2.py` 작성 — 완료 태스크 수 기반 진행률 멘트 검증
- [ ] `tp2.py` — 완료 축하 + `completed_tasks` 수 활용 진행률 안내 + 다음 태스크 추천
- [ ] `tests/test_tp3.py` 작성 — `current_task` 기반 리텐션 메시지 검증
- [ ] `tp3.py` — "이 문제만 끝내고 가자" 리텐션 + 남은 양 최소화 표현
- [ ] `tests/test_tp5.py` 작성 — 오답 없음 분기 검증
- [ ] `tests/test_tp5.py` 작성 — 오답 있음 + 복습 완료 분기 검증
- [ ] `tests/test_tp5.py` 작성 — 오답 있음 + 복습 미완료 분기 검증
- [ ] `tp5.py` — 오답 없음 → "오늘 다 맞았어!" 구현
- [ ] `tp5.py` — 오답 있음 + 복습 완료 → "오답 N개 다 복습했어!" 구현
- [ ] `tp5.py` — 오답 있음 + 복습 미완료 → "오답 N개 중 M개 남았어!" 구현 (`wrong_content_total` / `wrong_content_done` 수치 활용)
- [ ] **완료 기준**: `uv run pytest tests/test_tp2.py tests/test_tp3.py tests/test_tp5.py` 통과

---

### T8. conftest + 공통 fixture

> 모든 노드 테스트가 공유하는 fixture를 정의한다.

**브랜치**: `feature/T8-conftest`
**담당 파일**: `tests/conftest.py`
**의존**: T1 (데이터 구조 확정 후) | **블로킹**: T4~T7 테스트 정상 실행

- [ ] 케이스 1 학생 fixture (못함+불성실, 1학년, 국어 태스크)
- [ ] 케이스 2 학생 fixture (못함+성실, 5학년, 수학 태스크)
- [ ] 잘함+성실 학생 fixture
- [ ] 잘함+불성실 학생 fixture
- [ ] `ChatState` 초기값 생성 헬퍼 함수
- [ ] `FastAPI TestClient` fixture
- [ ] Upstage LLM mock fixture (실제 API 호출 차단)
- [ ] **완료 기준**: T4~T7 테스트 파일에서 fixture import 정상, `uv run pytest` 전체 통과

---

## Phase 3 — 그래프 조립 (T4~T8 완료 후)

---

### T9. LangGraph StateGraph + 조건부 라우팅

> 모든 노드를 하나의 그래프로 조립하고 라우팅 로직을 연결한다.

**브랜치**: `feature/T9-langgraph-graph`
**담당 파일**: `app/services/graph.py`, `tests/test_graph.py`
**의존**: T4, T5, T6, T7, T8 | **블로킹**: T10

- [ ] `tests/test_graph.py` 작성 — 케이스 1: `use_case=talk, tp1` → TP1 노드 라우팅 검증
- [ ] `tests/test_graph.py` 작성 — 케이스 1: `use_case=learning, tp4` → TP4 노드 라우팅 검증
- [ ] `tests/test_graph.py` 작성 — 케이스 2: 동일 두 케이스
- [ ] `tests/test_graph.py` 작성 — `tp2`, `tp3`, `tp5` 라우팅 검증
- [ ] `tests/test_graph.py` 작성 — 잘못된 `touchpoint` 입력 예외 처리 검증
- [ ] `graph.py` — `StateGraph(ChatState)` 정의 및 노드 6개 등록 (classify + tp1~tp5)
- [ ] `graph.py` — `entry → classify` 항상 통과 설정
- [ ] `graph.py` — `use_case + current_touchpoint` 기준 조건부 라우팅 함수
- [ ] `graph.py` — `InMemorySaver` 연결 (thread_id 기반 세션 유지)
- [ ] `graph.py` — 그래프 컴파일 및 `stream()` 인터페이스 노출
- [ ] **완료 기준**: `uv run pytest tests/test_graph.py` 통과, 케이스 1·2 전체 흐름 수동 확인

---

## Phase 4 — API 연결 (T9 완료 후)

---

### T10. POST /chat 엔드포인트 + SSE 스트리밍

> 그래프를 FastAPI 엔드포인트에 연결하고 SSE로 응답을 스트리밍한다.

**브랜치**: `feature/T10-chat-api`
**담당 파일**: `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/api/routes/chat.py`, `app/main.py`, `tests/test_chat_api.py`
**의존**: T9 | **블로킹**: T11

- [ ] `tests/test_chat_api.py` 작성 — 케이스 1 홈화면 진입 API e2e 검증
- [ ] `tests/test_chat_api.py` 작성 — 케이스 2 학습 중 도움 API e2e 검증
- [ ] `tests/test_chat_api.py` 작성 — 존재하지 않는 `student_id` → 4xx 반환 검증
- [ ] `app/api/` 디렉토리 생성, `__init__.py` 및 `routes/__init__.py` 추가
- [ ] `app/api/routes/chat.py` — `POST /chat` 엔드포인트 구현
- [ ] `app/api/routes/chat.py` — `ChatRequest` 유효성 검증 → `graph.stream()` 호출
- [ ] `app/api/routes/chat.py` — `StreamingResponse(SSE)` 로 `ChatResponse` 반환
- [ ] `app/api/routes/chat.py` — 에러 핸들링 (student_id 미존재, LLM 오류)
- [ ] `app/main.py` 수정 — 라우터 등록
- [ ] **완료 기준**: `uv run pytest tests/test_chat_api.py` 통과, SSE 스트리밍 동작 브라우저 확인

---

## Phase 5 — 프론트엔드 (T10 완료 후, 스택 별도 논의)

---

### T11. 챗봇 UI

**브랜치**: `feature/T11-frontend`
**담당 파일**: 별도 결정 (Next.js App Router 또는 React+Vite)
**의존**: T10 | **블로킹**: 없음

- [ ] 스택 결정 (Next.js App Router 또는 React+Vite)
- [ ] 태블릿 비율 챗봇 UI 레이아웃 구현
- [ ] SSE 스트리밍 수신 및 메시지 순차 렌더링
- [ ] `text` 타입 — 말풍선 컴포넌트
- [ ] `choices` 타입 — 선택지 버튼 컴포넌트 (클릭 시 `POST /chat` 재호출)
- [ ] `image_card` 타입 — 이미지 카드 컴포넌트
- [ ] `hint_card` 타입 — 단계별 힌트 카드 컴포넌트 (스텝 순서 표시)
- [ ] 학생 선택 드롭다운 (student_id 전달용, mock 학생 목록)
- [ ] 케이스 1 / 케이스 2 전환 가능하게
- [ ] **완료 기준**: 케이스 1·2 전체 흐름 브라우저에서 처음부터 끝까지 동작 확인
