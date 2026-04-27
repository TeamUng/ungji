# 팀 협업 워크플로우

> 5인 병렬 개발 환경에서 충돌 없이 PRD 구현을 완료하기 위한 실전 규칙 모음.
> 이 문서를 먼저 읽고 작업을 시작한다.

---

## 1. 전체 흐름 한눈에 보기

```
TODO.md 확인
    ↓
GitHub Issue 등록 (작업 단위 1개 = 이슈 1개)
    ↓
origin/dev 최신화 → feature 브랜치 생성
    ↓
TDD: 테스트 먼저(Red) → 구현(Green)
    ↓
커밋 (규칙 준수)
    ↓
PR 생성 → dev 대상 (규칙 준수)
    ↓
리뷰 1명 이상 + pytest 통과 → 머지
    ↓
브랜치 삭제 + 이슈 close
    ↓
TODO.md 완료 체크박스 업데이트 + 워크로그 작성
```

---

## 2. 이슈 등록 규칙

**TODO.md에 정의된 작업 1개 = GitHub Issue 1개.**
작업 시작 전 반드시 이슈를 먼저 등록한다.

### 이슈 템플릿

```
## 작업 범위
### 담당 파일 (이 파일만 수정)
- app/services/nodes/tp4.py
- tests/test_tp4.py

### 건드리지 않는 파일 (다른 이슈 담당)
- app/services/graph.py  ← T9 이슈에서 담당
- app/services/nodes/tp1.py  ← T5 이슈에서 담당

## 선행 의존성
- blocked by #T1 (데이터 로더)
- blocked by #T2 (Upstage 클라이언트)
- blocked by #T3 (프롬프트)

## 완료 기준
- [ ] tests/test_tp4.py 작성 완료 (Red 단계)
- [ ] tp4.py 구현으로 테스트 통과 (Green 단계)
- [ ] uv run pytest 전체 통과
- [ ] PRD 케이스 1 국어 막힘 4종 분기 동작 확인
- [ ] PRD 케이스 2 수학 막힘 4종 분기 동작 확인

## 참고 문서
- PRD: docs/PRD.md 섹션 2-5, 2-6
- State 설계: docs/STATE_DESIGN.md
- 아키텍처: docs/ARCHITECTURE_REVIEW.md
- TODO: TODO.md T6
```

---

## 3. 브랜치 전략

### 원칙

- **이슈 1개 = 브랜치 1개** — 브랜치를 이슈와 1:1로 유지한다
- **시작점은 항상 origin/dev 최신** — 오래된 로컬 dev에서 파지 않는다
- **dev에 직접 push 금지** — PR을 통해서만 머지
- **이슈 완료 시 브랜치도 함께 삭제**

### 브랜치 생성 순서

```bash
# 1. 원격 dev 최신화
git fetch origin
git checkout dev
git pull origin dev

# 2. feature 브랜치 생성 (이슈 번호 포함)
git checkout -b feature/T6-tp4-node

# 3. 작업 후 push
git push -u origin feature/T6-tp4-node
```

### 브랜치 네이밍

`feature/T번호-간단설명`

예시:
- `feature/T1-data-loader`
- `feature/T4-classify-node`
- `feature/T6-tp4-node`
- `feature/T9-langgraph-graph`

### 이슈 완료 처리

PR 머지 후:
1. GitHub에서 브랜치 삭제 (PR 머지 화면의 "Delete branch" 클릭)
2. 이슈 close (PR에 `closes #이슈번호` 포함 시 자동 close)
3. 로컬 브랜치 정리: `git branch -d feature/T번호-설명`

---

## 4. 커밋 메시지 규칙

### 형식

```
<type>: <한 줄 요약>

<본문>
배경: 왜 이 변경이 필요했는지
방법: 어떻게 구현했는지, 대안 대비 선택 이유

주요 변경 파일:
- app/services/nodes/tp4.py  [신규] TP4 노드 구현 — 막힘 원인 4종 분기 로직
- tests/test_tp4.py          [신규] TP4 TDD 케이스 (PRD 케이스 1·2 기반)
```

### 커밋 type

| type | 언제 |
|------|------|
| `feat` | 새 기능·코드 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `chore` | 의존성·설정·빌드 |
| `refactor` | 동작 변경 없이 구조 개선 |
| `test` | 테스트 추가·수정 |

### 필수 원칙

- **한 커밋 = 한 가지 논리적 변경** (파일 수 기준이 아니라 의도 기준)
- **제목에 "무엇을 + 왜"** 가 함께 드러나야 한다
  - ❌ `feat: tp4 노드 추가`
  - ✅ `feat: TP4 막힘 원인 분기 코칭 노드 추가 — PRD 케이스 1·2 학습 중 도움 요청 구현`
- **본문에 파일 경로와 변경 내용** 을 명시한다 — 나중에 git log만 봐도 무슨 파일이 어떻게 바뀌었는지 알 수 있어야 한다
- **왜 이렇게 했는지** 를 남긴다 — "무엇을 했는지"는 diff로 알 수 있지만, 이유는 코드에 없다

---

## 5. PR 규칙

### PR 템플릿

```
## 배경 및 목적
왜 이 PR이 필요한지.
어떤 TODO 항목이고, 어떤 PRD 요구사항에서 출발했는지.

## 변경 내용
무엇을 구현하거나 변경했는지 요약.

## 주요 변경 파일
변경된 파일마다 한 줄씩, [신규] / [수정] / [삭제] 표시 후 설명.

예시:
- `app/services/nodes/tp4.py`  [신규] TP4 노드 — 막힘 원인 4종 분기 코칭 구현
- `tests/test_tp4.py`          [신규] TP4 TDD 케이스 (케이스 1 국어 / 케이스 2 수학)
- `app/services/prompts/coaching.py` [수정] 없음 (import만 추가)

## 설계 의도
핵심 결정과 그 이유.
다른 방법도 있었다면 왜 이 방향을 선택했는지.

## 결과 및 확인
테스트 결과, 동작 확인 내용.
uv run pytest 결과 붙여넣기.

## 관련 이슈
closes #이슈번호
```

### PR 머지 조건

- 최소 1명 리뷰 (본인 제외)
- `uv run pytest` 전체 통과
- 리뷰어는 **담당 파일 범위 침범 여부** 도 확인

### PR 대상 브랜치

항상 `dev` 브랜치로 PR을 보낸다.

---

## 6. TDD 진행 방식

각 TODO 항목의 구현은 다음 순서로 진행한다.

```
1. Red   — 테스트 파일 먼저 작성 (아직 구현 없으니 당연히 실패)
2. Green — 테스트가 통과하는 최소한의 구현
3. Clean — 리팩터 (동작은 그대로, 코드 정리)
```

**TDD 케이스 기준**: `docs/PRD.md` 섹션 2-5(케이스 1), 2-6(케이스 2)의 시나리오를 테스트로 변환한다.

**LLM 호출 처리**: 실제 Upstage API는 테스트에서 mock 처리한다. `tests/conftest.py`의 mock fixture를 사용한다.

---

## 7. AI 협업 가이드

AI(Claude Code 등)와 함께 작업할 때 어떻게 요청하면 효율적인지 정리한다.

### 세션 시작 시 — AI에게 줄 컨텍스트

새 대화를 시작할 때 아래 내용을 먼저 알려준다.

```
지금 [T번호] 이슈 작업합니다.
작업 내용: TODO.md의 T번호 항목 — [작업 제목]
담당 파일: [파일 경로 목록]
선행 완료된 작업: T1(데이터 로더), T2(Upstage 클라이언트), T3(프롬프트)
참고 문서: docs/PRD.md 섹션 [번호], docs/STATE_DESIGN.md
TDD 순서로 진행해주세요 (테스트 먼저).
```

예시:
```
지금 T6 이슈 작업합니다.
작업 내용: TP4 노드 구현 — 학습 중 막힘 원인 진단 + 분기 코칭
담당 파일: app/services/nodes/tp4.py, tests/test_tp4.py
선행 완료: T1(loader), T2(upstage client), T3(prompts) 머지 완료됨
참고: docs/PRD.md 섹션 2-5, 2-6 / docs/STATE_DESIGN.md
TDD 순서로, 테스트 파일 먼저 작성해주세요.
```

### AI에게 요청할 때 좋은 방식

| 상황 | 요청 방식 |
|------|----------|
| 구현 시작 | "T번호 작업입니다. TODO.md 내용 참고해서 테스트 먼저 작성해주세요" |
| 설계가 헷갈릴 때 | "STATE_DESIGN.md / PRD 섹션 몇 번 기준으로 어떻게 구현하면 좋을지 제안해주세요" |
| 커밋 메시지 작성 | "지금까지 변경된 파일 기준으로 커밋 메시지 작성해주세요 (TEAM_WORKFLOW.md C-2 형식)" |
| PR 작성 | "PR 메시지 작성해주세요. TEAM_WORKFLOW.md 템플릿 기준으로" |
| 코드 리뷰 요청 | "이 코드가 PRD 의도대로 구현됐는지, 담당 파일 범위를 벗어난 건 없는지 검토해주세요" |

### AI에게 주지 않아도 되는 것

- 전체 코드베이스 설명 — AI가 파일을 직접 읽을 수 있다
- 이미 완료된 Phase 0 작업 재설명 — `app/core/`, `app/schemas/` 는 완료됨

### AI가 하면 안 되는 것 (사람이 확인 후 실행)

- `git push` — 권한 문제 발생 가능, 직접 실행
- PR 생성 — 내용 확인 후 직접 생성
- 다른 이슈 담당 파일 수정 — AI에게 범위를 명확히 알려줄 것

---

## 8. 문서 체계

| 문서 | 위치 | 용도 |
|------|------|------|
| PRD | `docs/PRD.md` | 기획 요구사항, 케이스 1·2 시나리오 |
| 아키텍처 | `docs/ARCHITECTURE_REVIEW.md` | 기술 스택, API 구조, 설계 결정 |
| State 설계 | `docs/STATE_DESIGN.md` | ChatState 구조, 세그먼트 판별 로직, TP 정의 |
| TODO | `TODO.md` | 전체 작업 목록, 의존성, 담당 파일 |
| 워크플로우 | `docs/TEAM_WORKFLOW.md` | 협업 규칙 (이 문서) |
| 코드 규칙 | `AGENTS.md` | 로깅, 설정, 커밋, 테스트 코딩 규칙 |
| 워크로그 | `docs/worklogs/` | PR 단위 작업 기록 (기술 + 비개발자 요약) |

---

## 9. 작업 체크리스트 (매 이슈마다)

```
작업 시작 전
  [ ] TODO.md에서 이슈 내용 확인
  [ ] GitHub Issue 등록
  [ ] origin/dev pull 후 feature 브랜치 생성

작업 중
  [ ] 테스트 파일 먼저 작성 (TDD Red)
  [ ] 구현 (TDD Green)
  [ ] uv run pytest 전체 통과 확인

작업 완료 (PR 생성 전, feature 브랜치에 커밋)
  [ ] TODO.md 완료 항목 체크박스 업데이트 후 커밋
  [ ] docs/worklogs/YYYY-MM-DD_브랜치명.md 작성 후 커밋
  [ ] 커밋 메시지 규칙 확인 (왜/무엇을/어느 파일)
  [ ] PR 생성 (템플릿 준수, closes #이슈번호, 워크로그 체크박스 확인)
  [ ] 리뷰어 지정 (1명 이상)

머지 후
  [ ] GitHub에서 브랜치 삭제 (PR 머지 화면 "Delete branch" 클릭)
  [ ] 이슈 close 확인 (closes # 자동 close 여부 확인)
  [ ] 로컬 feature 브랜치 정리: git branch -d feature/T번호-설명
  [ ] CLAUDE.md 현재 상태 섹션 업데이트 (완료된 T번호 반영)
```

---

## 10. 워크로그 작성 규칙

**PR 머지 완료 후 반드시 작성한다.**

### 파일 위치 및 네이밍

```
docs/worklogs/YYYY-MM-DD_브랜치명.md
예시: docs/worklogs/2026-04-27_feature-T2-T3-client-prompts.md
```

### 필수 포함 항목

```
## 기본 정보
날짜, 담당자, 브랜치, TODO 항목, PR 링크

## 한 줄 요약
누가 읽어도 이해할 수 있는 한 문장

## 비개발자 요약
- 왜 이 작업이 필요했는지
- 어떤 파일을 왜 바꿨는지 (기술 용어 없이 설명)

## 기술 상세
- 변경 파일 목록 ([신규]/[수정]/[삭제])
- 커밋 히스토리
- 미완료 항목 (있는 경우)
```

### 작성 원칙

- **비개발자도 읽을 수 있게**: "클라이언트를 인스턴스화했다" 대신 "AI 서비스에 연결하는 설정을 만들었다"
- **왜를 반드시 적는다**: 무엇을 했는지보다 왜 했는지가 중요
- **미완료도 기록한다**: 테스트 미작성 등 남은 작업을 명시

### GitHub 강제 장치

PR 템플릿(`.github/pull_request_template.md`)에 워크로그 체크박스가 포함되어 있어,
PR 생성 시 자동으로 체크 여부를 확인하게 된다.

추가로 **GitHub Branch Protection** 설정 권장:
> GitHub 저장소 Settings → Branches → Branch protection rules → `dev`
> - ✅ Require pull request before merging
> - ✅ Require approvals (1명 이상)
> - ✅ Require status checks (pytest CI 연결 시)
> 이 설정을 켜면 `dev`에 직접 push가 불가능하고, 반드시 PR을 통해야만 머지할 수 있다.
