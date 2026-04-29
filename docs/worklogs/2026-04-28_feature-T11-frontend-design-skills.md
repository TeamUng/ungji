# 워크로그: 2026-04-28

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-28 |
| 담당자 | Codex |
| 브랜치 | feature/T11-frontend |
| TODO 항목 | 프론트 디자인 스킬 세팅 및 PRD 맞춤 보강 |
| PR 대상 | dev ← feature/T11-frontend |

---

## 한 줄 요약

> Galaxy Tab A8 기준 초등학생 학습코치 챗봇 UI를 안정적으로 설계하기 위해 Codex 디자인 스킬을 설치하고, 웅지 PRD에 맞춘 전용 프론트 디자인 스킬을 보강했습니다.

---

## 비개발자 요약 — 왜 했고 무엇을 바꿨는지

### 왜 했나요?

앞으로 프론트 화면을 만들 때마다 매번 디자인 기준을 다시 설명하면 작업 결과가 흔들릴 수 있습니다.
특히 이 프로젝트는 일반 채팅앱이나 랜딩페이지가 아니라, 초등학생이 태블릿에서 학습 중 도움을 받는 **학습코치 챗봇 UI**입니다.

그래서 Codex가 프론트 작업을 할 때 아래 기준을 계속 기억하도록 스킬을 세팅했습니다.

- Galaxy Tab A8 태블릿 화면을 먼저 고려합니다.
- 초등학생에게 맞는 짧고 따뜻한 한국어 문구를 사용합니다.
- PRD의 2개 MVP 케이스를 기준으로 챗봇 흐름을 설계합니다.
- 선택지 버튼, 이미지 카드, 단계별 힌트 카드처럼 PRD에서 허용한 UI 요소를 우선합니다.
- Supanova, gpt-taste 같은 디자인 스킬은 그대로 따라 하지 않고 웅지 서비스에 맞게 제한적으로 참고합니다.

### 무엇을 바꿨나요?

로컬 Codex 스킬 폴더에 디자인 스킬을 설치했습니다.

- `supanova-design-engine`
- `supanova-premium-aesthetic`
- `supanova-redesign-engine`
- `supanova-full-output`
- `gpt-taste`

그리고 웅지 전용 스킬인 `ungji-frontend-design`을 만들고 보강했습니다.

- PRD 기반 챗봇 UI 작업 기준을 한국어로 정리했습니다.
- MVP 케이스 1: 초등 1~2학년 국어 읽기 흐름을 UI 관점으로 정리했습니다.
- MVP 케이스 2: 초등 5~6학년 비율/비례식 흐름을 UI 관점으로 정리했습니다.
- 어떤 디자인 스킬을 언제 참고해야 하는지 매트릭스로 정리했습니다.
- OMD / Awesome DESIGN.md 계열 레퍼런스 중 웅지에 맞는 후보를 정리했습니다.

---

## 기술 상세

### 레포 변경 파일 목록

| 파일 | 구분 | 설명 |
|------|------|------|
| `docs/worklogs/2026-04-28_feature-T11-frontend-design-skills.md` | 신규 | 이번 Codex 프론트 디자인 스킬 세팅 작업 기록 |

### 로컬 Codex 스킬 변경 목록

아래 파일들은 Git 레포 안이 아니라 사용자 로컬 Codex 설정 경로에 있습니다.

| 파일 또는 폴더 | 구분 | 설명 |
|------|------|------|
| `C:\Users\sesac\.codex\skills\supanova-design-engine` | 설치 | 한국어 화면 완성도와 기본 디자인 엔진 참고 스킬 |
| `C:\Users\sesac\.codex\skills\supanova-premium-aesthetic` | 설치 | 여백, 카드, 버튼, 타이포그래피 품질 참고 스킬 |
| `C:\Users\sesac\.codex\skills\supanova-redesign-engine` | 설치 | 기존 화면 개선·리뷰 참고 스킬 |
| `C:\Users\sesac\.codex\skills\supanova-full-output` | 설치 | 단일 HTML 목업 출력이 필요할 때 참고할 스킬 |
| `C:\Users\sesac\.codex\skills\gpt-taste` | 설치 | 실험적인 고급 시각 콘셉트가 필요할 때만 참고할 보조 스킬 |
| `C:\Users\sesac\.codex\skills\ungji-frontend-design\SKILL.md` | 신규/수정 | 웅지 프론트 디자인의 기본 지휘 스킬, 한국어로 정리 |
| `C:\Users\sesac\.codex\skills\ungji-frontend-design\references\prd-chatbot-ui.md` | 신규 | PRD 터치포인트, 허용 UI 요소, MVP 케이스 1·2 흐름 정리 |
| `C:\Users\sesac\.codex\skills\ungji-frontend-design\references\skill-application-matrix.md` | 신규 | 설치된 디자인 스킬과 이후 후보 스킬의 적용 기준 정리 |
| `C:\Users\sesac\.codex\skills\ungji-frontend-design\references\omd-style-candidates.md` | 신규 | Intercom, Notion, Figma, Lovable 계열 OMD 참고 방향 정리 |

### 구현 메모

- `AGENTS.md`는 수정하지 않았습니다.
- 프로젝트 코드와 백엔드 파일도 수정하지 않았습니다.
- `ungji-frontend-design` 스킬은 처음에는 영어 중심으로 작성되었지만, 사용자가 직접 확인하기 쉽도록 한국어 중심으로 다시 작성했습니다.
- 스킬의 `name`과 기술 키워드(`Galaxy Tab A8`, `supanova-*`, `gpt-taste`, `Pretendard`, `PRD`)는 식별을 위해 그대로 유지했습니다.
- PRD 세부 흐름은 `SKILL.md`에 모두 넣지 않고 `references/`로 분리했습니다. 그래야 Codex가 필요한 참고자료만 읽을 수 있습니다.

### 결과 및 확인

```powershell
$env:PYTHONUTF8 = '1'
$python = "C:\Users\sesac\Desktop\ungji\.venv\Scripts\python.exe"
$validator = "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py"
& $python $validator "$env:USERPROFILE\.codex\skills\ungji-frontend-design"

# Skill is valid!
```

설치한 외부 스킬도 모두 검증을 통과했습니다.

```text
supanova-design-engine: Skill is valid!
supanova-premium-aesthetic: Skill is valid!
supanova-redesign-engine: Skill is valid!
supanova-full-output: Skill is valid!
gpt-taste: Skill is valid!
ungji-frontend-design: Skill is valid!
```

### 다음 작업에 주는 영향

- 이후 프론트 작업에서 `ungji-frontend-design`을 기준 스킬로 사용할 수 있습니다.
- PRD 기반 화면을 만들 때 Codex는 먼저 `prd-chatbot-ui.md`를 참고하게 됩니다.
- Supanova 계열은 화면 완성도와 한국어 타이포그래피 참고용으로만 사용합니다.
- `gpt-taste`는 기본 PRD 구현에는 사용하지 않고, 별도 고급 시각 콘셉트 요청이 있을 때만 참고합니다.
- 실제 프론트 기술 스택 선택, Next/Vite 결정, shadcn, Rive, Lottie 적용은 이후 단계에서 별도로 논의합니다.

### 주의 사항

- 새 스킬을 Codex가 완전히 인식하려면 Codex를 한 번 재시작하는 것이 좋습니다.
- 이번 작업 중 기존에 있던 미추적 `.vscode/` 폴더는 건드리지 않았습니다.

---

## 추가 작업: T11 비주얼 탐색용 HTML 목업 3종

### 한 줄 요약

> `FRONTEND_USER_FLOW.md` 기준으로 스마트올 홈 화면 위에 AI 학습코치 레이어가 얹히는 정적 HTML 시안 3종을 만들고, 태블릿 가로·세로 화면에서 전환과 드래그 동작을 검증했습니다.

---

## 비개발자 요약 — 왜 다시 만들었나요?

초기 시안은 스마트올 홈 UI의 색감과 카드 구조는 참고했지만, 실제 기획 문서가 의도한 **AI 코치 노출 방식**과는 차이가 있었습니다.

`docs/FRONTEND_USER_FLOW.md`에서 확정한 방향은 아래와 같습니다.

- 프론트는 별도 챗봇 앱이 아니라 스마트올 화면 위에 붙는 **AI 학습코치 레이어**입니다.
- 홈 화면과 학습 완료 시점에는 전체 채팅창이 아니라 **오른쪽 하단 플로팅 말풍선**으로 짧게 추천합니다.
- 학습 중 도움 요청 시에는 학생이 오른쪽 하단 캐릭터를 눌렀을 때 **오른쪽 채팅창**이 열립니다.
- A/B 시안의 차이는 기능 흐름이 아니라 **디자인 방향**이어야 합니다.
- 스마트올 홈 화면은 기업연계 프로젝트 특성상 최대한 실제 화면과 비슷하게 구성합니다.

그래서 기존 시안을 `FRONTEND_USER_FLOW.md` 기준으로 다시 정리했습니다.

---

## 최종 반영된 시안 구조

### 시안 A — 저학년 국어 디자인 방향

- 스마트올 1~2학년 홈 화면을 참고했습니다.
- 노란 배경, 왼쪽 과목 순서, 중앙 큰 단일 학습 카드, 오른쪽 추천/올도전/빠른 메뉴 구조를 사용했습니다.
- 케이스 1인 `초등 1~2학년 / 국어 / 짧은 글 읽기`에 어울리도록 문장을 짧고 쉽게 구성했습니다.
- AI 코치는 홈 화면 위에 말풍선으로 먼저 말을 겁니다.

### 시안 B — 고학년 수학 디자인 방향

- 스마트올 3~6학년 홈 화면을 참고했습니다.
- 파란 배경, 2x2 과목 카드, 오른쪽 추천/올도전/빠른 메뉴 구조를 사용했습니다.
- 케이스 2인 `초등 5~6학년 / 수학 / 비율·비례식`에 어울리도록 차분한 코치형 문구와 단계별 힌트를 사용했습니다.
- A와 같은 플로우를 따르되, 화면 밀도와 카드 배치만 고학년형으로 다르게 구성했습니다.

### 시안 C — 통합 TP 레이어 방향

- `TP1 홈`, `학습 기본`, `TP4 도움`, `TP3 이탈`, `TP5 종료`를 한 파일에서 비교할 수 있게 구성했습니다.
- 실제 서비스에서 AI 코치가 모든 화면 위에 동일한 레이어로 얹히는 방식을 확인하기 위한 중립안입니다.
- TP3에서는 큰 채팅창을 바로 열지 않고 작은 말풍선으로 먼저 붙잡는 흐름을 보여줍니다.
- TP5에서는 오답 복습 안내가 필요한 상황을 플로팅 말풍선으로 보여줍니다.

---

## 확정된 플로우

A/B 시안은 모두 아래 플로우를 따릅니다.

```text
TP1 홈 화면 진입
  → 스마트올 홈 화면 위에 AI 코치 플로팅 말풍선 노출
  → 학생이 AI 추천 버튼 또는 기존 학습 카드를 선택
  → 학습 화면 진입
  → 학습 중에는 AI 코치 얼굴만 오른쪽 하단에 표시
  → 학생이 코치 얼굴을 누르면 TP4 오른쪽 채팅창 열림
  → 막힘 원인을 선택지로 진단
  → 힌트 카드 / 이미지 카드 / 짧은 설명 제공
  → 단위 학습 완료
  → TP2 플로팅 말풍선으로 다음 행동 제안
```

C 시안은 아래 TP를 함께 보여줍니다.

```text
TP1 홈 추천
학습 기본
TP4 도움 요청
TP3 이탈 시도
TP5 오늘 학습 종료
```

---

## 사용자 논의로 확정된 결정

| 항목 | 결정 |
|------|------|
| A/B 플로우 | 반드시 `FRONTEND_USER_FLOW.md` 기준으로 동일하게 맞춘다 |
| A/B 차이 | 기능 차이가 아니라 디자인 차이만 둔다 |
| C 방향 | 통합 TP 레이어 시안으로 유지한다 |
| 홈 화면 | 스마트올 UI를 최대한 비슷하게 만든다 |
| AI 코치 겹침 | 스마트올 UI 위에 얹힌 오버레이이므로 겹침을 허용한다 |
| AI 코치 위치 | 사용자가 드래그로 옮길 수 있는 캐릭터로 설정한다 |
| 드래그 시각 장치 | 별도 핸들은 두지 않는다 |
| 드래그 피드백 | 홀드/드래그 중에 코치가 손가락에 매달려 있는 느낌의 애니메이션을 준다 |
| 로고 | 상단에 `웅진씽크빅 smartAll` 느낌을 CSS로 강화한다 |

---

## 변경 파일 목록

| 파일 | 구분 | 설명 |
|------|------|------|
| `docs/design/t11-concepts/index.html` | 신규 | 시안 3종 비교용 인덱스 |
| `docs/design/t11-concepts/concept-a-lower-play-coach.html` | 신규 | 저학년 국어 디자인 방향 시안 |
| `docs/design/t11-concepts/concept-b-upper-study-board.html` | 신규 | 고학년 수학 디자인 방향 시안 |
| `docs/design/t11-concepts/concept-c-overlay-coach.html` | 신규 | 통합 TP 레이어 시안 |
| `docs/design/t11-concepts/assets/t11-concepts.css` | 신규 | 공통 레이아웃, 스마트올 홈 스타일, 코치 오버레이, 드래그 애니메이션 |
| `docs/design/t11-concepts/assets/t11-concepts.js` | 신규 | 상태 전환 및 AI 코치 드래그 상호작용 |
| `docs/worklogs/2026-04-28_feature-T11-frontend-design-skills.md` | 수정 | 이번 T11 목업 작업 내용 추가 |

---

## 구현 상세

### 상태 전환

정적 HTML만으로 여러 화면 상태를 확인하기 위해 `data-state-panel`, `data-state-target` 속성을 사용했습니다.

- A/B: `TP1 홈`, `학습 화면`, `TP4 도움`, `TP2 완료`
- C: `TP1 홈`, `학습 기본`, `TP4 도움`, `TP3 이탈`, `TP5 종료`

각 시안 하단의 전환 버튼을 누르면 한 파일 안에서 상태가 바뀝니다.

### AI 코치 드래그

AI 코치 캐릭터는 실제 앱에서 화면 위에 떠 있는 레이어처럼 느껴지도록 드래그 가능하게 만들었습니다.

- 홈/완료 상태: 코치 얼굴을 드래그하면 말풍선 묶음이 함께 이동합니다.
- 학습 화면 기본 상태: 코치 얼굴만 오른쪽 하단에 떠 있고, 얼굴만 드래그됩니다.
- 드래그 가능한 것을 표시하는 별도 점이나 핸들은 제거했습니다.
- 대신 드래그 중에는 `is-dragging` 클래스가 붙어 캐릭터가 살짝 눌리고 말풍선이 따라오는 느낌을 줍니다.

### 스마트올 홈 UI 참고

제공된 홈 화면 이미지를 기준으로 아래 요소를 반영했습니다.

- 검은색 상단 내비게이션
- 오늘의 학습 탭 강조
- 날짜/요일 pill 구조
- 저학년형: 노란 배경, 왼쪽 과목 순서, 큰 단일 학습 카드
- 고학년형: 파란 배경, 2x2 학습 카드
- 오른쪽 추천 도서 카드
- 올도전 카드
- 출석/기록/노트 빠른 메뉴

---

## 검증 결과

Playwright로 정적 HTML을 열어 아래 항목을 확인했습니다.

| 검증 항목 | 결과 |
|------|------|
| `1280x800` 가로 태블릿 | 통과 |
| `800x1280` 세로 태블릿 | 통과 |
| A/B/C 상태 전환 | 통과 |
| AI 코치 드래그 이동 | 통과 |
| 드래그 중 `is-dragging` 적용/해제 | 통과 |
| 콘솔 오류 | 0개 |
| 48px 미만 버튼 | 0개 |
| 가로 스크롤 | 없음 |
| 주요 버튼/카드 텍스트 넘침 | 없음 |
| 내부 분류명 화면 노출 | 없음 |

검증에 사용한 핵심 기준:

```text
1280x800:
- index.html
- concept-a-lower-play-coach.html
- concept-b-upper-study-board.html
- concept-c-overlay-coach.html

800x1280:
- index.html
- concept-a-lower-play-coach.html
- concept-b-upper-study-board.html
- concept-c-overlay-coach.html
```

---

## 현재 완료 범위

이번 작업은 실제 프론트 앱 구현이 아니라 **T11 디자인/플로우 탐색용 정적 HTML 목업**입니다.

완료된 범위:

- 스마트올 홈 UI 기반 목업 화면
- `FRONTEND_USER_FLOW.md` 기준 AI 코치 노출 방식
- A/B/C 시안 비교 구조
- AI 코치 드래그 상호작용
- 드래그 중 애니메이션 상태
- 태블릿 가로/세로 기본 검증

아직 하지 않은 범위:

- Next.js 또는 Vite 같은 실제 프론트 스택 선택
- FastAPI `/chat` 연동
- 실제 학생 데이터 연동
- 실제 스마트올 에셋 사용
- 실제 로고 이미지 파일 적용
- Lottie/Rive 같은 정교한 캐릭터 애니메이션 적용

---

## 다음 단계 제안

1. A/B/C 중 실제 프론트 구현에 가까운 방향을 고릅니다.
2. 선택한 방향을 기준으로 하나의 통합 시안을 다시 정리합니다.
3. 그 다음에 Next.js 또는 Vite 중 실제 프론트 스택을 논의합니다.
4. API 연결 전에는 목업 데이터로 `TP1`, `TP2`, `TP3`, `TP4`, `TP5` 화면 상태를 컴포넌트화합니다.
