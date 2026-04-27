# TODO

## 구현 목표

PRD의 2개 MVP 케이스가 처음부터 끝까지 작동하는 것.

| 케이스 | 대상 | 세그먼트 | 핵심 흐름 |
|--------|------|---------|----------|
| 케이스 1 | 초1~2 / 국어 / 짧은 글 읽기 | 못함+불성실 | 홈화면 진입 → 쉬운 국어 활동 제안 → 학습 중 막혔을 때 선택지+쉬운 설명 |
| 케이스 2 | 초5~6 / 수학 / 비율·비례식 | 못함+성실 | 홈화면 진입 → 비율 약점 보완 제안 → 학습 중 막혔을 때 단계별 코칭+teach-back |

---

## 진행 원칙

- **TDD**: 각 작업은 테스트 먼저(Red) → 구현(Green) 순서
- **병렬**: 같은 Phase 내 작업은 동시 진행 가능, 담당 파일이 겹치지 않음
- **Phase 순서**: Phase N+1은 아래 명시된 블로킹 작업 완료 후 시작
- **브랜치**: `feature/T번호-간단설명` (예: `feature/T5-classify-node`)
- **Mock 데이터 / 시나리오**: 별도 제공 예정 → 해당 파일 구조만 먼저 정의

---

## Phase 0 — 완료 ✅

- [x] `app/core/enums.py` — Segment, GradeGroup, UseCase, Touchpoint 등
- [x] `app/core/constants.py` — 세그먼트 판별 임계값, 학년 그룹 경계
- [x] `app/schemas/student.py` — StudentProfile, LearningHistory, LearningPattern, WrongAnswerPattern
- [x] `app/schemas/chat.py` — Task, ChatState, ChatRequest, ChatResponse
- [x] `pyproject.toml` — langgraph, langchain-upstage, langsmith 추가

---

## Phase 1 — 기반 세팅 (3개 병렬, 지금 바로 시작 가능)

---

### T1. 데이터 로더

```
담당 파일
  app/data/__init__.py
  app/data/loader.py

작업 내용
  - mock_students.json / mock_problems.json 의 JSON 구조 정의
    (실제 데이터는 별도 제공 예정 — 구조만 먼저 확정)
  - load_student(student_id: str) → StudentProfile + 관련 데이터 반환
  - load_problem(problem_id: str) → 문제 + 해설 + 힌트 데이터 반환
  - student_id 없을 때 명확한 예외 처리

테스트
  tests/test_loader.py
  - 정상 조회, 존재하지 않는 ID 케이스

의존: 없음
블로킹: T4(classify), T5~T8(TP 노드), T9(conftest)
```

---

### T2. Upstage 클라이언트 + config 보완

```
담당 파일
  app/clients/__init__.py
  app/clients/upstage.py
  app/core/config.py       (키 2개 추가)
  .env.example             (항목 추가)

작업 내용
  upstage.py
  - ChatUpstage 인스턴스 생성 및 export
  - settings에서 UPSTAGE_API_KEY, UPSTAGE_BASE_URL 읽기
  - LangSmith 트레이싱 설정 (LANGSMITH_API_KEY, LANGSMITH_PROJECT)
  config.py 추가
  - LANGSMITH_API_KEY: str = ""
  - LANGSMITH_PROJECT: str = ""

테스트
  tests/test_upstage_client.py
  - 클라이언트 초기화 검증 (실제 API 호출은 mock 처리)

의존: 없음
블로킹: T5~T8(TP 노드)
```

---

### T3. 페르소나 + 코칭 프롬프트

```
담당 파일
  app/services/__init__.py
  app/services/prompts/__init__.py
  app/services/prompts/personas.py
  app/services/prompts/coaching.py

작업 내용
  personas.py
  - get_persona(grade_group: GradeGroup) → str
    lower  : 짧은 문장, 쉬운 단어, 이모처럼 다정하게, 한 번에 하나만
    middle : 친근한 친구/형, 선택지로 이유 말하게 유도
    upper  : 존댓말 혼합, 차분한 코치형, 논리·존중 중심

  coaching.py
  - get_coaching_strategy(segment: Segment) → str
    못함+불성실 : 초소형 목표, 즉시 성공 경험, 짧은 대화, 흥미 기반
    못함+성실   : 막힘 원인 진단, 단계별 설명, 격려, 쉬운 표현
    잘함+불성실 : 짧고 명확한 시작점, 도전형 선택지
    잘함+성실   : 칭찬+심화 문제, 사고 확장 질문

테스트
  tests/test_prompts.py
  - 학년 그룹 3종 × 세그먼트 4종 반환값 존재 검증
  - 케이스 1 학생(lower + 못함+불성실) 프롬프트 내용 검증
  - 케이스 2 학생(upper + 못함+성실) 프롬프트 내용 검증

의존: 없음 (app/core/enums.py 사용)
블로킹: T5~T8(TP 노드)
```

---

## Phase 2 — 노드 구현 (T1·T2·T3 완료 후 병렬)

> T4~T8은 서로 간 의존 없음. 동시 진행 가능.

---

### T4. classify 노드

```
담당 파일
  app/services/nodes/__init__.py
  app/services/nodes/classify.py
  tests/test_classify.py

작업 내용
  입력: student_id
  처리:
  - loader로 학생 데이터 로드 → ChatState 초기화
  - constants.py 임계값 기준 segment 판별
    정답률 >= 90           → 잘함, 미만 → 못함
    완료율 >= 70
    + 오답콘텐츠 None 또는 >= 50 → 성실, 아니면 불성실
  - grade → grade_group 변환 (1~2: lower / 3~4: middle / 5~6: upper)
  - 결과 State에 저장
  출력: segment, grade_group이 채워진 ChatState

TDD 케이스 (PRD 기반)
  - 케이스 1 학생 → segment=못함+불성실, grade_group=lower
  - 케이스 2 학생 → segment=못함+성실, grade_group=upper
  - 오답 없는 학생 → None 처리로 성실도 불이익 없음
  - 학년 경계값 (2학년→lower, 3학년→middle, 4학년→middle, 5학년→upper)

의존: T1(데이터 로더)
블로킹: T9(graph)
```

---

### T5. TP1 노드 — 홈화면 진입 (케이스 1·2 공통 시작점)

```
담당 파일
  app/services/nodes/tp1.py
  tests/test_tp1.py

작업 내용
  입력: ChatState (segment, grade_group, today_tasks, student_profile 등)
  처리:
  - get_persona(grade_group) + get_coaching_strategy(segment) 조합으로
    시스템 프롬프트 구성
  - 학생 이름, 선호 과목, AI 예상점수, 오늘의 태스크 컨텍스트 주입
  - 세그먼트별 선택지 생성:
    못함+불성실 → "3분만 가볍게 시작하기", "아주 쉬운 문제 1개만 풀기",
                  "그림 보고 주인공 마음 골라보기", "AI가 오늘 할 것 골라주기"
    못함+성실   → "비율 개념 쉽게 다시 보기", "어제 틀린 비례식 문제 다시 풀기",
                  "한 문제를 단계별로 같이 풀기", "내가 어디서 헷갈렸는지 확인하기"
    잘함+불성실 → "5분만 도전 문제 풀기", "오늘 할 것 AI가 골라주기", "어제 하던 학습 이어하기"
    잘함+성실   → "오늘의 심화 문제 도전하기", "실생활 적용 문제 풀기", "내가 약한 단원 확인하기"
  출력: TextMessage(환영) + ChoicesMessage(선택지)

TDD 케이스 (PRD 기반)
  - 케이스 1: lower+못함+불성실 → 응답에 choices 포함, 짧고 쉬운 말투
  - 케이스 2: upper+못함+성실  → 응답에 choices 포함, 차분한 코치형 말투
  - 두 케이스의 선택지 내용이 다른지 검증

의존: T1(데이터), T2(LLM 클라이언트), T3(프롬프트)
블로킹: T9(graph)
```

---

### T6. TP4 노드 — 학습 중 도움 요청 (케이스 1·2 핵심)

```
담당 파일
  app/services/nodes/tp4.py
  tests/test_tp4.py

작업 내용
  입력: ChatState (current_task, segment, grade_group, chat_history)
  처리:
  1단계 — 막힘 원인 선택지 제공
    케이스 1(국어): "글이 너무 길어", "무슨 상황인지 모르겠어",
                    "주인공 마음을 모르겠어", "그냥 하기 싫어"
    케이스 2(수학): "비율 뜻이 헷갈려", "어떤 수끼리 비교해야 할지 모르겠어",
                    "식을 어떻게 세우는지 모르겠어", "계산하다가 틀렸어"
  2단계 — 선택에 따른 분기 코칭
    국어 "글이 너무 길어"       → 문장 한 줄씩 나눠서 TextMessage
    국어 "무슨 상황인지 모르겠어" → 쉬운 말 재설명 + ImageCardMessage
    국어 "주인공 마음을 모르겠어" → 표정/행동 단서 + 선택지 좁히기
    국어 "그냥 하기 싫어"       → "한 문제만 같이 해보자" 초소형 목표
    수학 "비율 뜻이 헷갈려"     → 일상 비유 재설명 (해설 데이터 기반)
    수학 "어떤 수끼리 비교"     → 기준량/비교량 찾기 유도
    수학 "식을 어떻게 세우는지" → HintCardMessage (단계별 비례식 안내)
    수학 "계산하다가 틀렸어"    → 검산 유도 (개념 설명 없이)
  3단계 — teach-back (수학 케이스)
    마지막 단계에서 학생이 이해한 내용 설명하도록 유도
    설명 맞으면 칭찬, 부족하면 칭찬 + 추가 설명
  - mock_problems.json 해설 데이터 참조
  출력: 상황에 따라 TextMessage / ChoicesMessage / ImageCardMessage / HintCardMessage

TDD 케이스 (PRD 2-5, 2-6 기반)
  - 케이스 1 국어: 선택지 4종 각각 올바른 응답 타입 반환 검증
  - 케이스 2 수학: 선택지 4종 각각 올바른 응답 타입 반환 검증
  - "식을 어떻게 세우는지" → hint_card 타입 포함 검증
  - "무슨 상황인지 모르겠어" → image_card 타입 포함 검증

의존: T1(데이터+해설), T2(LLM 클라이언트), T3(프롬프트)
블로킹: T9(graph)
```

---

### T7. TP2 + TP3 + TP5 노드 — 보조 터치포인트

```
담당 파일
  app/services/nodes/tp2.py
  app/services/nodes/tp3.py
  app/services/nodes/tp5.py
  tests/test_tp2.py
  tests/test_tp3.py
  tests/test_tp5.py

작업 내용
  tp2.py — 단위 학습 완료 후
  - 완료 축하 멘트 (completed_tasks 수 활용)
  - 남은 today_tasks 기반 다음 학습 추천

  tp3.py — 이탈 방지
  - current_task 기반 "이 문제만 끝내고 가자" 리텐션 메시지
  - 남은 양 최소화 표현

  tp5.py — 학습 종료
  - 오답 상태 3분기:
    has_wrong_answers=False                     → "오늘 다 맞았어!"
    has_wrong_answers=True + wrong_content_done → "오답 {total}개 다 복습했어!"
    has_wrong_answers=True + 미완료             → "오답 {total}개 중 {done}개 남았어!"
  - wrong_content_total / wrong_content_done 수치 멘트 활용

TDD 케이스
  tp5: 3개 오답 분기 각각 응답 내용 검증

의존: T1(데이터), T2(LLM), T3(프롬프트)
블로킹: T9(graph)
```

---

### T8. conftest + 공통 fixture

```
담당 파일
  tests/conftest.py

작업 내용
  - 케이스 1 학생 fixture (못함+불성실, 1학년, 국어 태스크)
  - 케이스 2 학생 fixture (못함+성실, 5학년, 수학 태스크)
  - 나머지 2개 세그먼트 학생 fixture
  - ChatState 초기값 생성 헬퍼
  - FastAPI TestClient fixture
  - Upstage LLM mock fixture (실제 API 호출 차단)
  참고: mock_students.json 제공 후 실제 데이터로 교체 예정

의존: T1(데이터 구조 확정)
블로킹: T4~T7 테스트 정상 실행
```

---

## Phase 3 — 그래프 조립 (T4~T8 완료 후)

---

### T9. LangGraph StateGraph + 조건부 라우팅

```
담당 파일
  app/services/graph.py
  tests/test_graph.py

작업 내용
  - StateGraph(ChatState) 정의
  - 노드 등록: classify, tp1, tp2, tp3, tp4, tp5
  - 라우팅 로직:
    진입 → classify 항상 통과
    classify 이후 → use_case + current_touchpoint 기준 분기
      talk   + tp1 → TP1 노드
      talk   + tp2 → TP2 노드
      talk   + tp3 → TP3 노드
      learning + tp4 → TP4 노드
      talk   + tp5 → TP5 노드
  - InMemorySaver (thread_id 기반 세션 유지)
  - 그래프 컴파일 및 stream 인터페이스

TDD 케이스 (PRD 케이스 1·2 전체 흐름)
  - 케이스 1 홈화면 진입 → classify → TP1 라우팅 검증
  - 케이스 1 학습 중 막힘 → classify → TP4 라우팅 검증
  - 케이스 2 동일
  - 잘못된 touchpoint 입력 시 예외 처리 검증

의존: T4(classify), T5(TP1), T6(TP4), T7(TP2·3·5), T8(conftest)
블로킹: T10(API)
```

---

## Phase 4 — API 연결 (T9 완료 후)

---

### T10. POST /chat 엔드포인트 + SSE 스트리밍

```
담당 파일
  app/api/__init__.py
  app/api/routes/__init__.py
  app/api/routes/chat.py
  app/main.py              (라우터 등록)
  tests/test_chat_api.py

작업 내용
  - POST /chat 구현
  - ChatRequest 유효성 검증 → graph.stream() 호출
  - StreamingResponse(SSE)로 ChatResponse 반환
  - thread_id 기반 세션 연속성
  - 에러 핸들링 (student_id 미존재, LLM 오류)

TDD 케이스
  - 케이스 1 홈화면 진입 API 호출 → SSE 응답 검증
  - 케이스 2 학습 중 도움 API 호출 → SSE 응답 검증
  - 존재하지 않는 student_id → 4xx 반환 검증

의존: T9(graph)
블로킹: T11(프론트엔드)
```

---

## Phase 5 — 프론트엔드 (T10 완료 후, 스택 별도 논의)

---

### T11. 챗봇 UI

```
스택: Next.js App Router 또는 React+Vite (미확정)
담당 파일: 별도 결정

작업 내용
  - 태블릿 비율 챗봇 UI 레이아웃
  - SSE 스트리밍 수신 및 메시지 렌더링
  - 메시지 타입별 컴포넌트:
      text       → 말풍선
      choices    → 선택지 버튼 (클릭 시 POST /chat 재호출)
      image_card → 이미지 카드
      hint_card  → 단계별 힌트 카드 (스텝 순서 표시)
  - 학생 선택 드롭다운 (student_id 전달용)
  - 케이스 1 / 케이스 2 전환 가능하게

의존: T10(API 계약 확정)
```

---

## 의존성 한눈에 보기

```
Phase 1 (병렬)
  T1 ──────────────► T4, T5, T6, T7, T8
  T2 ──────────────► T5, T6, T7
  T3 ──────────────► T5, T6, T7

Phase 2 (병렬)
  T4 ──────────────► T9
  T5 ──────────────► T9
  T6 ──────────────► T9   ← PRD 케이스 1·2 핵심
  T7 ──────────────► T9
  T8 ──────────────► T4~T7 테스트 실행

Phase 3
  T9 ──────────────► T10

Phase 4
  T10 ─────────────► T11
```
