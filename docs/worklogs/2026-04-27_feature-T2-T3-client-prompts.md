# 워크로그: 2026-04-27

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-27 |
| 담당자 | ayeonlee99 |
| 브랜치 | feature/T2-T3-client-prompts |
| TODO 항목 | T2 (Upstage 클라이언트), T3 (프롬프트), docs (ARCHITECTURE_REVIEW 동기화) |
| PR 대상 | dev ← feature/T2-T3-client-prompts |

---

## 한 줄 요약

> 챗봇이 AI 서비스(Upstage)와 연결되는 설정을 만들고, 학생 유형별 말투·코칭 전략 대본을 작성했습니다. 또한 팀 설계 문서를 최신 결정 내용으로 동기화했습니다.

---

## 비개발자 요약 — 왜 했고 무엇을 바꿨는지

### T2 — AI 서비스 연결 설정 (Upstage 클라이언트)

**왜 했나요?**
이 챗봇은 Upstage라는 AI 회사의 언어 모델(Solar Pro)을 사용해 학생에게 맞춤 대답을 생성합니다.
코드에서 "Upstage에 연결해서 이 학생에게 어떻게 대답하면 좋을지 물어봐"라고 지시하려면,
먼저 연결 설정을 한 곳에 만들어두어야 합니다.
또한 LangSmith라는 도구를 연결해 챗봇이 AI에게 어떤 질문을 보내고 어떤 답을 받았는지 추적·모니터링할 수 있게 했습니다.

**무엇을 바꿨나요?**
- `.env.example`: AI 서비스 연결에 필요한 설정 항목(`LANGSMITH_PROJECT`) 추가
- `app/core/config.py`: 서버 시작 시 `.env` 파일에서 LangSmith 키를 읽어오도록 항목 추가
- `app/clients/upstage.py`: Upstage AI에 연결하는 코드 작성 — 이 파일을 가져다 쓰기만 하면 어디서든 AI를 호출할 수 있음

### T3 — 학생 유형별 말투·코칭 전략 대본 작성 (프롬프트)

**왜 했나요?**
이 챗봇의 핵심은 학생 유형(학년, 성취도, 성실도)에 따라 **다른 말투**와 **다른 전략**으로 대화하는 것입니다.
1~2학년 아이에게는 짧고 다정하게, 5~6학년 학생에게는 논리적·차분하게 말해야 합니다.
이 "말투 지침"과 "코칭 전략"을 미리 텍스트로 정의해두는 작업입니다.

**무엇을 바꿨나요?**
- `app/services/prompts/personas.py`: 학년 그룹(1~2학년 / 3~4학년 / 5~6학년)별 말투 지침 작성
- `app/services/prompts/coaching.py`: 학생 유형 4가지별 코칭 전략 작성
  - 못함+불성실: 아주 작은 목표 하나, 즉시 성공 경험, 짧은 대화
  - 못함+성실: 막힌 원인 진단 후 단계별 설명, 격려 중심
  - 잘함+불성실: 짧고 도전적인 시작점 제시
  - 잘함+성실: 칭찬 + 심화 문제 + 사고 확장

### docs — 설계 문서 최신화

**왜 했나요?**
`ARCHITECTURE_REVIEW.md`에 구버전 노드 이름(`home_coach.py`, `diagnose.py`)과 구버전 API 필드(`entry_point`)가 남아있어 팀원이 헷갈릴 수 있었습니다.
`STATE_DESIGN.md`와 `TODO.md`에서 확정된 최신 내용(`tp1~tp5`, `use_case + current_touchpoint`)으로 정리했습니다.

---

## 기술 상세

### 변경 파일 목록

| 파일 | 구분 | 설명 |
|------|------|------|
| `app/core/config.py` | 수정 | `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` 필드 추가 |
| `.env.example` | 수정 | `LANGSMITH_PROJECT=ungji` 항목 추가 |
| `app/clients/__init__.py` | 신규 | clients 패키지 |
| `app/clients/upstage.py` | 신규 | `ChatUpstage(llm)` 인스턴스 생성, LangSmith 트레이싱 활성화 |
| `app/services/__init__.py` | 신규 | services 패키지 |
| `app/services/prompts/__init__.py` | 신규 | prompts 패키지 |
| `app/services/prompts/personas.py` | 신규 | `get_persona(grade_group)` — lower/middle/upper 3종 |
| `app/services/prompts/coaching.py` | 신규 | `get_coaching_strategy(segment)` — 4개 세그먼트 전략 |
| `docs/ARCHITECTURE_REVIEW.md` | 수정 | 디렉토리·그래프·API 구조 동기화, 미결→결정 반영 |
| `docs/ay.md` | 삭제 | 개인 메모 파일 정리 |

### 커밋 히스토리

| 커밋 해시 | 메시지 |
|-----------|--------|
| bfea7b9 | docs: ARCHITECTURE_REVIEW — STATE_DESIGN·TODO 기반 구조 전면 반영 |
| d3f08cd | feat: T2 Upstage 클라이언트 초기화 및 LangSmith 트레이싱 설정 추가 |
| fcb10be | feat: T3 학년별 페르소나·세그먼트별 코칭 전략 프롬프트 구현 |

### 미완료 항목 (테스트 시나리오 확정 후 별도 진행)

- `tests/test_upstage_client.py` — T2 완료 기준 테스트
- `tests/test_prompts.py` — T3 완료 기준 테스트
