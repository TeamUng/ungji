# 팀 협업 워크플로우 및 세팅 계획

> 여러 명의 작업자가 병렬로 TDD 기반 개발을 진행하기 위한 세팅 작업 리스트

---

## 개발 방식 요약

- **결과물 먼저 구조화** → 학생 유형별 채팅 흐름 예제를 먼저 정의
- **TDD** → 테스트를 먼저 작성하고, 테스트를 통과시키는 방향으로 구현
- **병렬 개발** → 작업자마다 독립된 영역을 담당, 의존성 충돌 없이 진행
- **GitHub Issues + PR** → 작업 범위 명시, 1명 이상 리뷰 필수, 테스트 통과 시에만 머지
- **자연어 기록** → 각 작업의 이유, 방법, 결과를 사람이 바로 읽고 이해할 수 있게 기록

---

## A. 결과물 구조화 (개발 전 선행 작업)

### A-1. 학생 유형별 채팅 흐름 시나리오 문서화

- 유형 4개 x 진입 시점 3개 = 조합별 예상 대화 흐름을 자연어로 작성
- 각 흐름에서 기대하는 입력/출력을 구체적으로 정의
- PRD 케이스 1, 2를 기반으로 "이런 입력이 들어오면 이런 응답이 나와야 한다"를 예제로 작성

### A-2. 테스트 케이스 사전 정의

- 위 시나리오를 pytest 테스트로 변환 가능한 형태로 정리
- 각 노드/모듈별 입력 → 기대 출력 명세
- 이것이 곧 TDD의 "Red" 단계 테스트가 됨

---

## B. 작업 분할 및 이슈 구조화

### B-1. 작업 영역 분리 (큰 단위)

| 영역 | 담당 범위 | 파일 경로 |
| --- | --- | --- |
| 스키마 | 요청/응답 모델, 학생/문제 타입 정의 | `app/schemas/` |
| 에이전트 노드 | LangGraph 노드별 로직 구현 | `app/services/nodes/` |
| 프롬프트 | 학년별 페르소나, 유형별 코칭 프롬프트 | `app/services/prompts/` |
| 그래프 | LangGraph StateGraph 조합/라우팅 | `app/services/graph.py` |
| API | FastAPI 엔드포인트, SSE 스트리밍 | `app/api/routes/` |
| 목업 데이터 | 학생 프로필, 문제/해설 JSON | `app/data/` |
| 클라이언트 | Upstage LLM 연결 | `app/clients/` |
| 테스트 | 각 모듈별 테스트 | `tests/` |
| 프론트엔드 | 챗봇 UI 구현 | (별도 결정 필요) |

### B-2. 전체 TODO 리스트 작성

- 큰 작업 → 하위 작업으로 계층적 분해
- 각 작업의 의존성 명시 (어떤 작업이 선행되어야 하는지)
- 독립적으로 병렬 진행 가능한 작업 표시

### B-3. GitHub Issues 생성

각 TODO 항목을 이슈로 등록. 이슈에 포함할 내용:

```
## 작업 범위
- 수정 가능한 파일/경로: (예: app/services/nodes/classify.py, tests/test_classify.py)
- 건드리면 안 되는 파일/경로: (예: app/services/graph.py는 #12 이슈에서 담당)

## 선행 의존성
- blocked by #이슈번호 (있는 경우)

## 완료 기준
- [ ] 어떤 테스트가 통과해야 하는지
- [ ] 어떤 동작이 확인되어야 하는지

## 참고
- PRD 섹션: (예: 2-5, 케이스 1)
- 관련 시나리오: (예: 저성취+불성실 학생 홈화면 진입)
```

---

## C. 개발 규칙 및 브랜치 전략

### C-1. 브랜치 규칙

- 네이밍: `feature/이슈번호-간단설명` (예: `feature/5-classify-node`)
- `dev` 브랜치에 직접 push 금지
- PR을 통해서만 머지

### C-2. 커밋 메시지 규칙

**형식**

```
<type>: <한 줄 요약> (무엇을, 왜)

<본문 — 선택, 길어질 때만>
- 변경한 이유 (배경/문제)
- 선택한 방법과 대안 대비 이유
- 주요 변경 파일 및 내용:
  - app/core/enums.py: Segment, GradeGroup 등 Enum 타입 신규 추가
  - app/schemas/chat.py: LangGraph ChatState TypedDict 정의
```

**type 목록**

| type | 언제 쓰는가 |
|------|------------|
| `feat` | 새 기능/코드 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `chore` | 의존성, 설정, 빌드 관련 |
| `refactor` | 동작 변경 없이 코드 구조 개선 |
| `test` | 테스트 추가/수정 |

**원칙**
- 한 커밋 = 한 가지 논리적 변경 (파일 수가 아니라 의도 기준)
- 제목은 "무엇을 + 왜" 가 함께 드러나도록 작성
- 파일 경로 변경이 있을 경우 본문에 명시

### C-3. PR 규칙

PR 메시지에 반드시 포함할 내용:

```
## 배경 및 목적
왜 이 PR이 필요한지, 어떤 문제 또는 설계 결정에서 출발했는지

## 변경 내용
무엇을 만들었거나 바꿨는지 요약

## 주요 변경 파일
- `app/core/enums.py` — [신규] Segment, GradeGroup 등 Enum 정의
- `app/schemas/chat.py` — [신규] LangGraph ChatState, ChatRequest, ChatResponse
- `pyproject.toml` — [수정] langgraph, langchain-upstage, langsmith 추가

## 설계 의도
핵심 설계 결정과 그 이유 (대안이 있었다면 왜 이 방향을 선택했는지)

## 결과 및 확인
테스트 결과, import 검증, 동작 확인 내용

## 관련 이슈
closes #이슈번호
```

- 최소 1명 리뷰 필수 (본인 외)
- `uv run pytest` 통과 필수
- 리뷰어는 작업 범위 침범 여부도 확인

### C-4. 작업 기록 규칙

- 각 이슈/PR에 자연어로 기록
- "어떤 이유로, 어떻게 구현했고, 결과는 어떤지, 현재 작업 흐름과 일치하는지"
- 다른 사람이 바로 읽고 이해할 수 있는 수준으로 작성
- 기술 용어보다 의도와 맥락 중심으로 기록

---

## D. CI/테스트 인프라

### D-1. pytest 구조 설정

```
tests/
  conftest.py               # 공통 fixture (mock 학생, mock 문제, test client 등)
  test_health.py            # (기존) 헬스체크 테스트
  test_schemas.py           # 스키마 유효성 테스트
  test_classify.py          # 학생 유형 판단 노드 테스트
  test_home_coach.py        # 홈화면 코칭 노드 테스트
  test_learning_coach.py    # 학습 중 코칭 노드 테스트
  test_diagnose.py          # 막힘 진단 노드 테스트
  test_graph.py             # 그래프 통합 테스트
  test_chat_api.py          # API 엔드포인트 테스트
```

- TDD 순서: 테스트 파일 먼저 작성 (Red) → 구현 (Green) → 리팩터
- 공통 fixture로 mock 데이터 공유, 각 테스트는 독립적으로 실행 가능

### D-2. GitHub Actions CI

```yaml
# .github/workflows/test.yml
# PR 시 자동으로 pytest 실행
# 테스트 실패 시 머지 차단
```

- `uv run pytest` 실행
- 테스트 실패 시 PR 머지 불가
- (선택) 추후 lint/type check 추가 가능

---

## E. 문서 체계

### E-1. CONTRIBUTING.md

작업자 온보딩용 문서:
1. 이슈 확인 → 브랜치 생성
2. 테스트 먼저 작성 (TDD Red)
3. 구현 (TDD Green)
4. 리팩터
5. `uv run pytest` 통과 확인
6. PR 작성 (템플릿 준수)
7. 리뷰 요청 (1명 이상)
8. 리뷰 통과 + 테스트 통과 → 머지

### E-2. 진행 상황 추적

- GitHub Projects (칸반 보드) 또는 docs/ 내 체크리스트
- 전체 작업 목록에서 누가 어디까지 했는지 한눈에 확인 가능

---

## 작업 순서

```
1. A (결과물 구조화) ← 가장 먼저, 이게 있어야 나머지가 가능
2. B (작업 분할 + 이슈 생성)
3. C + D + E (규칙/인프라/문서) ← 병렬 가능
4. 실제 개발 시작 (TDD: 테스트 먼저 → 구현)
```
