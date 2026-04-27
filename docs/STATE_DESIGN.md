# LangGraph State 설계 문서

> 이 문서는 ay 브랜치 논의에서 확정된 ChatState 구조, 데이터 모델, 세그먼트 판별 로직을 정리합니다.
> 처음 합류하는 팀원도 이 문서 하나로 전체 설계 의도를 파악할 수 있도록 작성했습니다.

---

## 1. 배경 — 왜 이 구조인가?

### 핵심 설계 결정 요약

| # | 결정 | 선택 | 이유 |
|---|------|------|------|
| 1 | TP(터치포인트) 구조 | TP별 독립 LangGraph 노드 | 노드마다 프롬프트/로직 분리, 독립 테스트 가능 |
| 2 | 응답 생성 방식 | LLM 동적 생성 | 학생마다 다른 말투·맥락을 프롬프트로 제어 |
| 3 | 개인화 수준 | 중간 개인화 (확장) | 이름·유형·선호과목·오늘 태스크·학습 이력·패턴·오답 패턴 주입 |
| 4 | 학년별 말투 적용 | 전체 TP 적용, 3개 학년 그룹 | 일관된 캐릭터 경험; 1~2 / 3~4 / 5~6 그룹으로 관리 부담 최소화 |
| 5 | State 구조 | 아래 ChatState 참고 | 세션 시작 시 1회 로드 후 모든 노드가 공유 |

---

## 2. 5개 터치포인트 (TP) 정의

| TP | 진입 시점 | 역할 |
|----|----------|------|
| TP1 | 홈화면 진입 | 챗봇이 먼저 말 걸고 오늘의 첫 학습 유도 |
| TP2 | 단위 학습 완료 | 다음 학습 제안, 진행률 축하 |
| TP3 | 이탈 시도 감지 | 리텐션 — "이 문제만 끝내고 가자" |
| TP4 | 학습 중 도움 요청 | 막힘 원인 진단 → 단계별 코칭 |
| TP5 | 오늘 학습 종료 | 오답 복습 유도, 오늘 학습 요약 |

### use_case ↔ TP 매핑

프론트는 API 호출 시 `use_case` + `current_touchpoint` 둘 다 전송합니다.

```
use_case = "talk"
  ├── current_touchpoint = "tp1"  →  홈 진입
  ├── current_touchpoint = "tp2"  →  과목 완료 후
  ├── current_touchpoint = "tp3"  →  이탈 시도
  └── current_touchpoint = "tp5"  →  학습 종료

use_case = "learning"
  └── current_touchpoint = "tp4"  →  학습 중 도움 요청
```

---

## 3. 학년 그룹 (grade_group)

| 그룹 | 대상 | 말투 방향 |
|------|------|----------|
| `lower` | 1~2학년 | 짧은 문장, 쉬운 단어, 이모 느낌, 한 번에 하나만 |
| `middle` | 3~4학년 | 친근한 친구/형 느낌, 선택지로 이유 말하게 유도 |
| `upper` | 5~6학년 | 존댓말 혼합, 차분한 코치형, 논리·존중 중심 |

---

## 4. 세그먼트 (4개 유형)

### 판별 기준

```python
recent_period = 7  # 모든 평균값은 최근 7일 기준

# 잘함/못함
is_high_achiever = student_profile.최근_평균정답률 >= 90

# 성실/불성실
is_diligent = (
    student_profile.평균완료율 >= 70
    and (
        learning_pattern.오답_콘텐츠_진행률 is None   # 오답 없음 → 불이익 없음
        or learning_pattern.오답_콘텐츠_진행률 >= 50  # 오답 있으면 절반 이상 진행
    )
)
```

### 세그먼트 → 코칭 전략

| segment | 판별 조건 | 홈화면 전략 | 코칭 전략 |
|---------|----------|------------|----------|
| `잘함+성실` | 정답률≥90 + 성실 | 심화·사고확장 선택지 | 칭찬 + 도전 제공 |
| `잘함+불성실` | 정답률≥90 + 불성실 | 짧은 목표, 도전형 | 루틴 형성 유도 |
| `못함+성실` | 정답률<90 + 성실 | 개념 보정, 단계별 | 막힘 원인 진단 + 격려 |
| `못함+불성실` | 정답률<90 + 불성실 | 초소형 진입, 쉬운 문제 | 즉시 성공 경험 제공 |

---

## 5. ChatState 전체 구조

```python
from typing import Literal
from langgraph.graph import MessagesState
from langchain_core.messages import BaseMessage

class StudentProfile(TypedDict):
    name: str                           # 학생 이름
    grade: Literal[1, 2, 3, 4, 5, 6]  # 학년
    preferred_subject: str              # 선호 과목 (1개)
    strong_subject: str                 # 잘하는 과목 (1개)
    recent_avg_score: int               # 최근 7일 평균 정답률 (0~100)
    avg_completion_rate: int            # 최근 7일 평균 완료율 (0~100)

class LearningHistory(TypedDict):
    # 과목명을 key로, 최근 7일 평균값을 value로
    subject_avg_scores: dict[str, int]       # 예: {"수학": 72, "국어": 88}
    subject_completion_rates: dict[str, int] # 예: {"수학": 80, "국어": 60}

class LearningPattern(TypedDict):
    # 오답 콘텐츠 (None = 오답 자체가 없음)
    wrong_content_rate: int | None      # 최근 7일 오답 콘텐츠 진행률 (0~100, None=오답없음)
    wrong_content_total: int            # 오늘 전체 오답 콘텐츠 수 (0이면 오답 없음)
    wrong_content_done: int             # 오늘 완료한 오답 콘텐츠 수
    # 학습 습관 (최근 7일 기준)
    skipping_habit: bool                # 건너뛰는 습관
    guessing_habit: bool                # 찍는 습관
    careless_habit: bool                # 대충 푸는 습관

class WrongAnswerPattern(TypedDict):
    frequent_wrong_type: str            # 자주 틀리는 유형 (예: "분수 계산")
    repeated_wrong_subjects: list[str]  # 반복 오답 과목 (예: ["수학", "사회"])
    wrong_cause: str                    # 오답 원인 (예: "개념 부족" | "실수" | "찍기")

class Task(TypedDict):
    subject: str            # 과목명 (예: "수학")
    unit: str               # 단원명 (예: "비율과 비례식")
    problem_count: int      # 문제 수
    estimated_time: int     # 예상 소요시간 (분)
    difficulty: str         # 난이도 ("상" | "중" | "하")
    ai_predicted_score: int # AI 예상점수 (0~100)

class ChatState(TypedDict):
    # ─── 세션 식별 ───
    thread_id: str      # 프론트에서 UUID 생성, LangGraph InMemorySaver thread 키
    student_id: str     # mock_students.json 조회 키

    # ─── 학생 정보 (세션 시작 시 1회 로드, 이후 불변) ───
    student_profile: StudentProfile
    learning_history: LearningHistory
    learning_pattern: LearningPattern
    wrong_answer_pattern: WrongAnswerPattern

    # ─── 오늘의 학습 상태 ───
    today_tasks: list[Task]         # 오늘 배정된 전체 태스크
    completed_tasks: list[Task]     # 오늘 완료한 태스크
    current_task: Task | None       # 현재 진행 중인 태스크 (TP4용)
    has_wrong_answers: bool         # 오늘 틀린 문제 있는지
    wrong_content_done_today: bool  # 오늘 오답 콘텐츠 진행했는지
    today_score: int                # 오늘의 학습 문항 평균 점수 (0~100)

    # ─── 대화 상태 ───
    use_case: Literal["talk", "learning"]
    grade_group: Literal["lower", "middle", "upper"]
    segment: Literal["잘함+성실", "잘함+불성실", "못함+성실", "못함+불성실"]
    chat_history: list[BaseMessage]  # LangGraph add_messages reducer로 자동 누적

    # ─── 노드 라우팅용 ───
    current_touchpoint: Literal["tp1", "tp2", "tp3", "tp4", "tp5"]
```

---

## 6. 데이터 흐름

```
[프론트] POST /chat
  { thread_id, student_id, use_case, current_touchpoint, message }
        ↓
[classify 노드]
  · student_id로 mock_students.json 조회
  · StudentProfile / LearningHistory / LearningPattern / WrongAnswerPattern 로드
  · 정답률·완료율 기준으로 segment 판별
  · 학년으로 grade_group 결정
  · 결과를 State에 저장 (세션 내 재조회 없음)
        ↓
[라우팅] use_case + current_touchpoint 기준 분기
        ↓
[TP 노드] State 전체를 읽어 LLM 프롬프트 구성
  · grade_group → 페르소나/말투 시스템 프롬프트 (personas.py)
  · segment → 코칭 전략 프롬프트 (coaching.py)
  · student_profile, today_tasks 등 → 개인화 컨텍스트 주입
  · chat_history → 대화 맥락 유지
        ↓
[응답] SSE 스트림으로 messages 배열 반환
  [ { type: "text", content }, { type: "choices", items }, ... ]
```

---

## 7. 오답 콘텐츠 처리 로직

TP5(종료) 노드에서 복습 유도 분기:

```python
if not state["has_wrong_answers"]:
    # 오늘 다 맞음
    → "오늘 다 맞았어! 완벽해!"

elif state["wrong_content_done_today"]:
    # 오답 있고 복습까지 완료
    → "복습까지 다 했네! 대단해!"
    # 구체적 멘트: wrong_content_total / wrong_content_done 수치 활용
    # 예: "오답 콘텐츠 3개 다 끝냈어!"

else:
    # 오답 있고 복습 미진행
    → "틀린 문제 다시 풀어보자!"
    # 예: "오답 콘텐츠 3개 중 1개 남았어!"
```

---

## 8. 미결 사항

| # | 내용 | 우선순위 |
|---|------|---------|
| 8-1 | `mock_students.json` 구체적 데이터 작성 (2개 MVP 케이스 학생) | 높음 |
| 8-2 | `mock_problems.json` 형태 확정 (케이스 1: 국어, 케이스 2: 수학) | 높음 |
| 8-3 | TP 코칭 레이어 4개(막힘진단/동기유지/자기조절/개념보완)를 노드 분리 vs 프롬프트 분기로 처리할지 | 중간 |
| 8-4 | 두 케이스 간 공유 로직 범위 (공통 classify vs 과목별 특화 노드) | 중간 |
