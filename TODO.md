# TODO

## T11-MVP. 스마트올 홈 + 챗봇 오버레이

> 기존 1차 UI 구현은 참고하되, 최종 구조는 스마트올 홈 정적 UI + 드래그형 챗봇 오버레이 + InteractionZone 감지 구조를 우선한다.

- [x] `/` 루트를 스마트올 홈 + 챗봇 오버레이 단일 화면으로 정리
- [x] 기존 `SmartAllCoachApp` 데모를 `/tp-demo`에 보존
- [x] `1280x800` 기준의 스크롤 없는 태블릿 캔버스 구현
- [x] TopHeader, DateSelector, SubjectRail, MainLearningCard, RightSidebar 구조 정리
- [x] 깨진 한글 문자열을 기준 문서의 자연스러운 한국어 문구로 교체
- [x] InteractionZoneProvider / InteractionZone / useInteractionZones 구조 추가
- [x] 10개 감지 대상 zone 등록: learning-card, learning-start, subject-math, subject-korean, subject-literacy, subject-hanja, recommended-book, challenge-card, attendance, study-record, wrong-note
- [x] 챗봇 오버레이를 별도 레이어로 분리하고 기존 UI 클릭을 막지 않도록 처리
- [x] 챗봇 드래그를 Pointer Events + `transform: translate3d()` 기반으로 구현
- [x] 드래그 종료 위치를 localStorage에 저장하고 새로고침 후 복원
- [x] 드래그 중 zone rect 캐싱 및 activeZone 변경 시에만 React state 갱신
- [x] 감지된 섹션별 말풍선 문구 변경 및 highlight 표시
- [x] `/`와 `/tp-demo` 오버레이를 `PorongOverlay` 단일 구현으로 통합
- [x] `PorongOverlay`에서 InteractionZone 감지와 홈 좌표 위치 저장/복원 연결
- [x] Galaxy Tab A8 기준 성능 조건 점검
- [x] `npx tsc --noEmit`, `npm run build`, `npm run lint` 결과 확인
- [x] 브라우저에서 `/` 화면, 드래그, 위치 복원, zone 감지 확인

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
- [x] `tests/test_upstage_client.py` 작성 — 클라이언트 초기화 검증 (실제 API 호출은 mock)
- [x] **완료 기준**: `from app.clients.upstage import llm` import 정상, `uv run pytest tests/test_upstage_client.py` 통과

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
- [x] `tests/test_prompts.py` 작성 — 3개 학년 그룹 × 4개 세그먼트 반환값 존재 검증
- [x] `tests/test_prompts.py` — 케이스 1 (lower + 못함+불성실) 프롬프트 내용 검증
- [x] `tests/test_prompts.py` — 케이스 2 (upper + 못함+성실) 프롬프트 내용 검증
- [x] **완료 기준**: `uv run pytest tests/test_prompts.py` 통과

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

- [x] `app/services/nodes/` 디렉토리 생성 및 `__init__.py` 추가
- [x] `tests/test_classify.py` 작성 — 케이스 1 학생 → `segment=못함+불성실`, `grade_group=lower` 검증
- [x] `tests/test_classify.py` 작성 — 케이스 2 학생 → `segment=못함+성실`, `grade_group=upper` 검증
- [x] `tests/test_classify.py` — 오답 없는 학생(wrong_content_rate=None) → 성실도 불이익 없음 검증
- [x] `tests/test_classify.py` — 학년 경계값 (2→lower, 3→middle, 4→middle, 5→upper)
- [x] `classify.py` — `load_student()`로 데이터 로드 후 `ChatState` 초기화
- [x] `classify.py` — `constants.py` 임계값 기준 `segment` 판별 로직
- [x] `classify.py` — `grade` → `grade_group` 변환 로직
- [x] **완료 기준**: `uv run pytest tests/test_classify.py` 통과

---

### T5. TP1 노드 — 홈화면 진입

> 세그먼트·학년 그룹에 맞는 환영 메시지와 선택지를 생성한다. 케이스 1·2의 시작점.

**브랜치**: `feature/T5-tp1-node`
**담당 파일**: `app/services/nodes/tp1.py`, `tests/test_tp1.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [x] `tests/test_tp1.py` 작성 — 케이스 1 (lower + 못함+불성실) → 응답에 `choices` 포함, 짧고 쉬운 말투 검증
- [x] `tests/test_tp1.py` 작성 — 케이스 2 (upper + 못함+성실) → 응답에 `choices` 포함, 코치형 말투 검증
- [x] `tests/test_tp1.py` — 케이스 1과 케이스 2의 선택지 내용이 다른지 검증
- [x] `tp1.py` — `get_persona()` + `get_coaching_strategy()` 조합으로 시스템 프롬프트 구성
- [x] `tp1.py` — 학생 이름·선호 과목·AI 예상점수·오늘 태스크 컨텍스트 주입
- [x] `tp1.py` — 세그먼트별 선택지 생성 (PRD 1-5 + `docs/SEGMENT_RESPONSE_POLICY.md` 기준 4개 세그먼트 × 선택지)
- [x] **완료 기준**: `uv run pytest tests/test_tp1.py` 통과, 응답에 `TextMessage` + `ChoicesMessage` 포함 확인

---

### T6. TP4 노드 — 학습 중 도움 요청

> 막힘 원인을 선택지로 진단하고 원인에 따라 분기 코칭한다. 케이스 1·2의 핵심 기능.

**브랜치**: `feature/T6-tp4-node`
**담당 파일**: `app/services/nodes/tp4.py`, `tests/test_tp4.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [x] `tests/test_tp4.py` 작성 — 케이스 1 국어: 막힘 원인 선택지 4종 응답 검증
  - [x] "글이 너무 길어" → `TextMessage` (문장 분리)
  - [x] "무슨 상황인지 모르겠어" → `ImageCardMessage` 포함
  - [x] "주인공 마음을 모르겠어" → `ChoicesMessage` (선택지 좁히기)
  - [x] "그냥 하기 싫어" → `TextMessage` (초소형 목표)
- [x] `tests/test_tp4.py` 작성 — 케이스 2 수학: 막힘 원인 선택지 4종 응답 검증
  - [x] "비율 뜻이 헷갈려" → `TextMessage` (비유 설명)
  - [x] "어떤 수끼리 비교해야 할지 모르겠어" → `TextMessage` (기준량/비교량 유도)
  - [x] "식을 어떻게 세우는지 모르겠어" → `HintCardMessage` 포함
  - [x] "계산하다가 틀렸어" → `TextMessage` (검산 유도)
- [x] `tp4.py` — 1단계: 막힘 원인 선택지 제공 (케이스별 4종)
- [x] `tp4.py` — 2단계: 케이스 1 국어 원인별 분기 코칭
- [x] `tp4.py` — 2단계: 케이스 2 수학 원인별 분기 코칭 (해설 데이터 참조)
- [x] `tp4.py` — 3단계: teach-back 유도 (수학, 마지막 단계에서 학생 설명 요청)
- [x] `tp4.py` — 내부 세그먼트명 노출 없이 `docs/SEGMENT_RESPONSE_POLICY.md`의 세그먼트별 출력 형태 반영
- [x] **완료 기준**: `uv run pytest tests/test_tp4.py` 통과, `HintCardMessage`·`ImageCardMessage` 타입 포함 확인

---

### T7. TP2 + TP3 + TP5 노드 — 보조 터치포인트

> 단위 학습 완료(TP2), 이탈 방지(TP3), 학습 종료(TP5) 세 노드를 구현한다.

**브랜치**: `feature/T7-tp2-tp3-tp5-nodes`
**담당 파일**: `app/services/nodes/tp2.py`, `tp3.py`, `tp5.py`, `tests/test_tp2.py`, `tests/test_tp3.py`, `tests/test_tp5.py`
**의존**: T1, T2, T3 | **블로킹**: T9

- [x] `tests/test_tp2.py` 작성 — 완료 태스크 수 기반 진행률 멘트 검증
- [x] `tp2.py` — 완료 축하 + `completed_tasks` 수 활용 진행률 안내 + 다음 태스크 추천
- [x] `tests/test_tp3.py` 작성 — `current_task` 기반 리텐션 메시지 검증
- [x] `tp3.py` — "이 문제만 끝내고 가자" 리텐션 + 남은 양 최소화 표현
- [x] `tests/test_tp5.py` 작성 — 오답 없음 분기 검증
- [x] `tests/test_tp5.py` 작성 — 오답 있음 + 복습 완료 분기 검증
- [x] `tests/test_tp5.py` 작성 — 오답 있음 + 복습 미완료 분기 검증
- [x] `tp5.py` — 오답 없음 → "오늘 다 맞았어!" 구현
- [x] `tp5.py` — 오답 있음 + 복습 완료 → "오답 N개 다 복습했어!" 구현
- [x] `tp5.py` — 오답 있음 + 복습 미완료 → "오답 N개 중 M개 남았어!" 구현 (`wrong_content_total` / `wrong_content_done` 수치 활용)
- [x] **완료 기준**: `uv run pytest tests/test_tp2.py tests/test_tp3.py tests/test_tp5.py` 통과

---

### T8. conftest + 공통 fixture

> 모든 노드 테스트가 공유하는 fixture를 정의한다.

**브랜치**: `feature/T8-conftest`
**담당 파일**: `tests/conftest.py`
**의존**: T1 (데이터 구조 확정 후) | **블로킹**: T4~T7 테스트 정상 실행

- [x] 케이스 1 학생 fixture (못함+불성실, 1학년, 국어 태스크)
- [x] 케이스 2 학생 fixture (못함+성실, 5학년, 수학 태스크)
- [x] 잘함+성실 학생 fixture
- [x] 잘함+불성실 학생 fixture
- [x] `ChatState` 초기값 생성 헬퍼 함수
- [x] `FastAPI TestClient` fixture
- [x] Upstage LLM mock fixture (실제 API 호출 차단)
- [x] **완료 기준**: T4~T7 테스트 파일에서 fixture import 정상, `uv run pytest` 전체 통과

---

## Phase 3 — 그래프 조립 (T4~T8 완료 후)

---

### T9. LangGraph StateGraph + 조건부 라우팅

> 모든 노드를 하나의 그래프로 조립하고 라우팅 로직을 연결한다.

**브랜치**: `feature/T9-langgraph-graph`
**담당 파일**: `app/services/graph.py`, `tests/test_graph.py`
**의존**: T4, T5, T6, T7, T8 | **블로킹**: T10

- [x] `tests/test_graph.py` 작성 — 케이스 1: `use_case=talk, tp1` → TP1 노드 라우팅 검증
- [x] `tests/test_graph.py` 작성 — 케이스 1: `use_case=learning, tp4` → TP4 노드 라우팅 검증
- [x] `tests/test_graph.py` 작성 — 케이스 2: 동일 두 케이스
- [x] `tests/test_graph.py` 작성 — `tp2`, `tp3`, `tp5` 라우팅 검증
- [x] `tests/test_graph.py` 작성 — 잘못된 `touchpoint` 입력 예외 처리 검증
- [x] `graph.py` — `StateGraph(ChatState)` 정의 및 노드 6개 등록 (classify + tp1~tp5)
- [x] `graph.py` — `entry → classify` 항상 통과 설정
- [x] `graph.py` — `use_case + current_touchpoint` 기준 조건부 라우팅 함수
- [x] `graph.py` — `InMemorySaver` 연결 (thread_id 기반 세션 유지)
- [x] `graph.py` — 그래프 컴파일 및 `stream()` 인터페이스 노출
- [x] **완료 기준**: `uv run pytest tests/test_graph.py` 통과, 케이스 1·2 전체 흐름 수동 확인

---

## Phase 4 — API 연결 (T9 완료 후)

---

### T10. POST /chat 엔드포인트 + SSE 스트리밍

> 그래프를 FastAPI 엔드포인트에 연결하고 SSE로 응답을 스트리밍한다.

**브랜치**: `feature/T10-chat-api`
**담당 파일**: `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/api/routes/chat.py`, `app/main.py`, `tests/test_chat_api.py`
**의존**: T9 | **블로킹**: T11

- [x] `tests/test_chat_api.py` 작성 — 케이스 1 홈화면 진입 API e2e 검증
- [x] `tests/test_chat_api.py` 작성 — 케이스 2 학습 중 도움 API e2e 검증
- [x] `tests/test_chat_api.py` 작성 — 존재하지 않는 `student_id` → 4xx 반환 검증
- [x] `app/api/` 디렉토리 생성, `__init__.py` 및 `routes/__init__.py` 추가
- [x] `app/api/routes/chat.py` — `POST /chat` 엔드포인트 구현
- [x] `app/api/routes/chat.py` — `ChatRequest` 유효성 검증 → `graph.stream()` 호출
- [x] `app/api/routes/chat.py` — `StreamingResponse(SSE)` 로 `ChatResponse` 반환
- [x] `app/api/routes/chat.py` — 에러 핸들링 (student_id 미존재, LLM 오류)
- [x] `app/main.py` 수정 — 라우터 등록
- [x] **완료 기준**: `uv run pytest tests/test_chat_api.py` 통과, SSE 스트리밍 동작 브라우저 확인

---

## Phase 4.5 — TP4 문제/해설 기반 동적 코칭 고도화

> 현재 TP4는 막힘 원인 선택지와 일부 힌트 스텝이 고정되어 있다.
> 해설지가 제공된다는 가정하에, 문제·해설·학생 유형을 LLM이 함께 보고 해당 문제에 맞는 선택지와 힌트 스텝을 생성하도록 고도화한다.

### T12. TP4 문제/해설 기반 동적 코칭

**GitHub Issue**: #19
**브랜치**: `feature/T12-tp4-dynamic-coaching`
**담당 파일**: `app/services/nodes/tp4.py`, `app/data/mock_problems.json`, `app/data/loader.py`, `tests/test_tp4.py`, `tests/test_tp4_problem_examples.py`, `docs/experiments/tp4_problem_examples.md`
**의존**: T1, T2, T3, T6, T10 | **블로킹**: TP4 실제 품질 검증, 프론트 API 연동 시나리오 고도화

- [x] `mock_problems.json`에 문제·정답·해설 중심의 실험용 문제 데이터를 추가한다.
- [x] TP4가 `problem_id` 또는 현재 태스크 컨텍스트로 문제 데이터를 참조할 수 있게 한다.
- [x] LLM 프롬프트에 `question`, `answer`, `explanation`, `grade_group`, `segment`, `selected_cause`를 전달한다.
- [x] 첫 진입 시 문제/해설 기반 막힘 원인 선택지를 동적으로 생성한다.
- [x] 선택지 클릭 후, 선택한 막힘 원인에 맞는 `TextMessage`와 `HintCardMessage` 스텝을 동적으로 생성한다.
- [x] 저학년은 타이핑보다 선택지 중심으로, 고학년은 단계별 설명과 teach-back 중심으로 응답한다.
- [x] 정답을 바로 노출하지 않고, 해설지를 근거로 작은 단위 힌트 → 풀이 유도 → 최종 확인 순서로 진행한다.
- [x] LLM 응답이 깨질 경우 사용할 안전한 fallback 선택지·힌트 스텝을 둔다.
- [x] `tests/test_tp4_problem_examples.py` 작성 — 소금물 비율 문제에서 문제/해설 기반 선택지와 힌트 스텝 생성 검증
- [x] `docs/experiments/tp4_problem_examples.md` 작성 — 케이스별 모의 대화와 관찰 결과 기록
- [x] **완료 기준**: `uv run pytest tests/test_tp4.py tests/test_tp4_problem_examples.py` 통과, 케이스 1·2 TP4 모의 대화가 문제/해설 기반으로 설명 가능

---

## Phase 5 — 프론트엔드 (T10 완료 후, 스택 별도 논의)

---

### T11. 챗봇 UI

**브랜치**: `feature/T11-frontend`
**담당 파일**: `frontend/` (Next.js App Router)
**의존**: T10 | **블로킹**: 없음

- [x] 스택 결정 — Next.js App Router + TypeScript + Tailwind CSS
- [x] 태블릿 비율 챗봇 UI 레이아웃 구현
  - [x] 스마트올 `오늘의 학습` 홈 화면 기반 레이아웃
  - [x] 학습 화면 위 AI 코치 레이어 구조
  - [x] 학습 완료/마무리 화면 흐름
  - [x] AI 코치 캐릭터 드래그 동작
- [ ] SSE 스트리밍 수신 및 메시지 순차 렌더링
- [x] mock/live adapter 기반 메시지 순차 렌더링 구조
- [x] `text` 타입 — 말풍선 컴포넌트
- [x] `choices` 타입 — 선택지 버튼 컴포넌트
- [x] mock 기준 `choices` 클릭 시 학생 선택 말풍선 + 다음 코치 응답 누적 렌더링
- [ ] `choices` 클릭 시 실제 `POST /chat` 재호출 (T10 이후)
- [x] `image_card` 타입 — 이미지 카드 컴포넌트
- [x] `hint_card` 타입 — 단계별 힌트 카드 컴포넌트 (스텝 순서 표시)
- [x] TP4 케이스별 선택지 분기 mock 응답
- [x] 수학 케이스 teach-back 텍스트 입력
- [x] TP3 상세 도움 채팅창 전환
- [x] TP5 오답 복습 채팅창 전환
- [x] 학생 선택 드롭다운 (student_id 전달용, mock 학생 목록)
- [x] `/` 학생 화면과 `/tp-demo` 내부 검수 화면 분리
- [x] `/`를 `FRONTEND_USER_FLOW.md` 기반 자연 흐름 진입점으로 연결
- [x] mock/live chat adapter 인터페이스 분리
- [x] 케이스 1 / 케이스 2 전환 가능하게
- [x] 백엔드 `ChatRequest` / `ChatResponse`와 맞춘 프론트 타입 정의
- [x] `/chat` 연동 전까지 사용할 mock chat adapter 구현
- [x] 뽀롱쌤 투명 PNG 원본 수령 및 기준 asset 보관
  - [x] `frontend/public/assets/porong/brand/porong-logo-full-original.png` 원본 보관
  - [x] `frontend/public/assets/porong/brand/porong-logo-full.webp` WebP 변환본 생성
- [x] 뽀롱쌤 asset 폴더 구조 구축
  - [x] `frontend/public/assets/porong/brand/`
  - [x] `frontend/public/assets/porong/mascot/`
  - [x] `frontend/public/assets/porong/ui/`
  - [x] `frontend/public/assets/porong/motion/`
- [x] 1차 mascot 상태별 WebP asset 구성
  - [x] `porong-overlay-idle.webp`
  - [x] `porong-overlay-welcome.webp`
  - [x] `porong-overlay-thinking.webp`
  - [x] `porong-overlay-speaking.webp`
  - [x] `porong-overlay-hint.webp`
  - [x] `porong-overlay-cheer.webp`
  - [x] `porong-overlay-comfort.webp`
  - [x] `porong-overlay-confused.webp`
  - [x] `porong-overlay-touched.webp`
  - [x] `porong-overlay-dragging.webp`
  - [x] `porong-overlay-hanging.webp`
  - [x] `porong-overlay-snapping.webp`
  - [x] `porong-overlay-edge.webp`
  - [x] `porong-head.webp`
- [x] UI 장식 SVG asset 구성
  - [x] `star.svg`
  - [x] `sparkle.svg`
  - [x] `speech-tail.svg`
  - [x] `wand.svg`
- [x] 기존 CSS 얼굴형 코치를 실제 뽀롱쌤 이미지 기반 `PorongOverlay`로 교체
  - [x] `PorongMascot` — 상태별 뽀롱쌤 이미지 렌더링
  - [x] `PorongSpeechBubble` — TP별 짧은 말풍선과 CTA 렌더링
  - [x] `PorongOverlay` — 캐릭터, 말풍선, 탭/드래그 상태 통합 제어
  - [x] `usePorongDrag` — 탭과 드래그 구분
  - [x] `usePorongSnap` — 초기 위치와 화면 안 safe 위치 계산
  - [x] `porongTypes` / `porongAssets` — 상태 타입과 asset 경로 분리
- [x] 뽀롱쌤 드래그 인터랙션 1차 구현
  - [x] 짧게 탭하면 채팅창 또는 말풍선 열기
  - [x] 8px 이상 움직이면 드래그 상태로 전환
  - [x] 드래그 중 살짝 확대, 기울기, 매달림 느낌 적용
  - [x] 손을 떼면 사이드로 밀리지 않고 놓은 좌표에 유지
  - [x] 채팅창이 열렸을 때 캐릭터와 패널이 겹치지 않도록 위치 보정
  - [x] 세로형 태블릿 화면에서 오버레이가 화면 밖으로 나가지 않도록 보정
- [x] TP1~TP5 흐름과 뽀롱쌤 상태 연결
  - [x] TP1 홈 진입/추천: `welcome`
  - [x] TP2 학습 완료: `cheer`
  - [x] TP3 이탈 시도: `comfort`
  - [x] TP4 학습 중 도움 요청: `idle` / `hint` / `speaking`
  - [x] TP5 오늘 학습 종료/오답 복습: `cheer` / `comfort`
  - [x] 답변 생성 중: `thinking`
- [x] CSS + Motion 기반 뽀롱쌤 모션 구현
  - [x] idle/welcome 둥실둥실 모션
  - [x] touched 터치 반응 모션
  - [x] dragging 매달림 느낌 모션
  - [x] snapping 착지 bounce 모션
  - [x] thinking/hint 반짝임 모션
  - [x] speaking 말하는 느낌 모션
  - [x] cheer 칭찬 팝 모션
  - [x] comfort 부드러운 흔들림 모션
  - [x] confused 갸웃 모션
  - [x] `prefers-reduced-motion` 접근성 대응
  - [x] `motion` 패키지 도입 및 `motion/react` 기반 위치/상태 모션 적용
  - [x] `useMotionValue` / `useSpring` 기반 드래그 follow와 놓은 위치 유지 구현
  - [x] `PorongCoachPanel`로 오른쪽 채팅창 컴포넌트 분리
  - [x] `useDizzyShake`로 빠른 좌우 흔들기 감지 및 2초 cooldown 구현
  - [x] `dizzy` 상태, 말풍선, star/sparkle 반응 연결
  - [x] `dizzy` 발동 후 2초 동안 섹션별 말풍선보다 어지러움 메시지를 우선 표시
  - [x] 초기 위치가 spring으로 미끄러져 들어오지 않도록 MotionValue와 spring 값을 함께 초기화
  - [x] 초기 stage/overlay 측정 실패 시 `requestAnimationFrame` 재시도로 ready 상태 보강
  - [x] 드래그 시작 시 실제 렌더링 좌표를 다시 측정해 stage offset으로 인한 위치 어긋남 방지
- [x] 기존 섹션 감지 챗봇 레이어와 Motion 기반 `PorongOverlay` 통합
  - [x] `/` 홈 화면에서 `ChatbotOverlayLayer` 대신 `PorongOverlay` 사용
  - [x] `PorongOverlay` 내부에서 `InteractionZone` 감지 문맥을 읽도록 통합
  - [x] `/tp-demo`를 `InteractionZoneProvider`로 감싸고 주요 섹션 zone 등록
  - [x] 말풍선 우선순위 정리: dizzy → 섹션별 제안 → TP 말풍선
  - [x] `/`, `/tp-demo` 모두 같은 `PorongOverlay` 경로에서 섹션별 제안 코멘트 표시 확인
  - [x] 사용하지 않는 구형 `ChatbotOverlayLayer` / `useDraggableChatbot` 계열 파일 정리
- [x] 뽀롱쌤 작업 워크로그 작성
  - [x] `docs/worklogs/2026-04-29_feature-T11-porong-asset-system.md`
  - [x] `docs/worklogs/2026-04-30_feature-T11-porong-motion-zone-integration.md`
- [x] `1280x800`, `800x1280` 태블릿 화면 검증
- [x] `/`, `/tp-demo`에서 뽀롱쌤 오버레이 표시 확인
- [x] `npm run lint` 통과
- [x] `npm run build` 통과
- [x] **mock 기준 완료 기준**: 케이스 1·2 전체 흐름 브라우저에서 처음부터 끝까지 동작 확인
- [x] `/tp-demo` 브라우저 smoke test: 화면 렌더, `PorongOverlay` ready, TP1 말풍선 확인
- [x] `/tp-demo` 브라우저 smoke test: 뽀롱쌤 탭 시 `PorongCoachPanel` 열림 확인
- [x] `/tp-demo` 브라우저 smoke test: 드래그 후 놓은 좌표에 유지 확인
- [x] `/tp-demo` 브라우저 smoke test: dizzy shake 상태와 어지러움 말풍선 확인
- [x] `/` 브라우저 smoke test: 뽀롱쌤을 `오답노트` zone으로 드래그하면 섹션별 제안 말풍선 표시 확인
- [x] `/tp-demo` 브라우저 smoke test: 뽀롱쌤을 `오답노트` zone으로 드래그하면 섹션별 제안 말풍선 표시 확인
- [ ] 실기기에서 dizzy shake cooldown 포함 수동 QA
- [ ] 뽀롱쌤 캐릭터와 하단 `뽀롱쌤` 로고 텍스트를 완전히 분리한 원본 asset 확보
- [ ] 실제 프레임/포즈 기반 뽀롱쌤 애니메이션 고도화
  - [ ] `porong-hanging-left.webp` / `porong-hanging-right.webp` 제작 및 드래그 방향별 적용
  - [ ] `porong-speaking-1.webp` / `porong-speaking-2.webp` 제작 및 말하는 중 프레임 전환
  - [ ] `porong-blink.webp` 제작 및 idle 눈 깜빡임 적용
  - [ ] `porong-cheer-1.webp` / `porong-cheer-2.webp` 제작 및 칭찬 모션 고도화
  - [ ] `porong-comfort.webp` / `porong-confused.webp` 별도 표정 asset 제작
  - [ ] snap 착지 전용 포즈 asset 제작
- [ ] 레이어 분리형 뽀롱쌤 asset 검토
  - [ ] 몸통, 눈, 입, 팔, 안경, 학사모, 리본, 책, 마법봉, 그림자 분리
  - [ ] 입만 움직이는 speaking 모션 구현
  - [ ] 눈만 깜빡이는 blink 모션 구현
  - [ ] 팔/마법봉이 반응하는 cheer/hint 모션 구현
- [ ] Rive 또는 Lottie 기반 캐릭터 리깅 도입 여부 검토
  - [ ] 보급형 태블릿 성능 검토
  - [ ] 상태 제어 API 설계 유지 가능성 검토
  - [ ] 디자이너/Figma 원본 제공 가능 여부 확인
- [ ] 실제 터치 디바이스에서 뽀롱쌤 드래그 수동 QA
  - [ ] 탭과 드래그 오작동 여부 확인
  - [ ] 채팅창 열림 상태에서 겹침 여부 확인
  - [ ] 학습 문제/선택지/CTA 가림 여부 확인
  - [ ] 모션이 학습을 방해하지 않는지 확인
- [ ] **최종 완료 기준**: T10 `/chat` 연결 후 SSE 스트리밍으로 케이스 1·2 전체 흐름 확인
