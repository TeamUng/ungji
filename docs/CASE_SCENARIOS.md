# 케이스 시나리오

> `docs/PRD.md` 섹션 2-5(케이스 1), 2-6(케이스 2)을 LangGraph 노드의 입력/출력 단위 시나리오로 옮긴 명세서.
> 이 문서가 mock 데이터(`mock_students.json` / `mock_problems.json`) 정의와 노드 테스트 (`@pytest.mark.parametrize`) 입력의 단일 소스다.
>
> 관련 문서: `docs/STATE_DESIGN.md`(State 구조), `docs/SEGMENT_RESPONSE_POLICY.md`(세그먼트 출력 정책), `TODO.md`(T5/T6 테스트 분기).

---

## 1. 공통 규칙

### 1-1. 응답 메시지 타입

응답은 `ChatResponse.messages` 배열에 다음 4종이 1개 이상 담긴다 (정의는 `app/schemas/chat.py`).

| type | 모델 | 용도 |
|------|------|------|
| `text` | `TextMessage` | 챗봇 발화 |
| `choices` | `ChoicesMessage` | 선택지 버튼 (id + label) |
| `image_card` | `ImageCardMessage` | 이미지 카드 (image_url + caption) |
| `hint_card` | `HintCardMessage` | 단계별 힌트 카드 (steps[]) |

### 1-2. 선택지 ID 규칙

- `id`: 영문 snake_case, 안정적, 코드/테스트 비교용
- `label`: 학생에게 노출되는 한글 문구
- 네임스페이스: `<tp>_<intent>` 또는 `home_<tp>_<intent>` 형태로 prefix를 둬 노드 간 ID 충돌 방지

### 1-3. 노출 금지 키워드

학생 화면에 다음 단어를 노출하지 않는다 (테스트로 강제):

`불성실`, `회피형`, `저성취`, `고성취`, `세그먼트`, `클러스터`, `유형`

### 1-4. 시나리오 표 컨벤션

각 턴은 `request.message → 기대 ChatResponse.messages` 매핑을 표 1행으로 표현한다. 테스트는 이 표의 행을 `parametrize` 입력으로 1:1 옮긴다.

---

## 2. 케이스 1 — 초등 2학년 / 국어 / 문단의 짜임, 근거 찾기

### 2-1. 요약

| 항목 | 값 |
|------|-----|
| 학년 | 2 (`grade_group = lower`) |
| 과목 | 국어 |
| 단원 | 문단의 짜임 — 근거 찾기 / 뒷받침 문장 |
| 학생 유형 | 못함 + 불성실 (`segment = 못함+불성실`) |
| 핵심 가치 | 학습 시작 장벽을 낮추고, 짧은 글에서 답을 찾는 단계를 선택지로 분해 |
| 출처 문제 | `reference/g3-korean-example-question-01.png` (종이컵), `reference/g3-korean-example-question-02.png` (바다 뒷받침 문장) |

### 2-2. 학생 프로필 (mock_students.json 후보)

**student_id**: `case-1-low-lazy-korean-g2`

```jsonc
{
  "student_id": "case-1-low-lazy-korean-g2",
  "profile": {
    "name": "민준",
    "grade": 2,
    "preferred_subject": "국어",
    "strong_subject": "국어",
    "recent_avg_score": 62,        // 잘함 임계 90 미달 → 못함
    "avg_completion_rate": 35      // 성실 임계 70 미달 → 불성실
  },
  "learning_history": {
    "subject_avg_scores": { "국어": 62 },
    "subject_completion_rates": { "국어": 35 }
  },
  "learning_pattern": {
    "wrong_content_rate": 20,
    "wrong_content_total": 2,
    "wrong_content_done": 0,
    "skipping_habit": true,
    "guessing_habit": false,
    "careless_habit": true
  },
  "wrong_answer_pattern": {
    "frequent_wrong_type": "문단의 중심 문장 찾기",
    "repeated_wrong_subjects": ["국어"],
    "wrong_cause": "개념 부족"
  },
  "today_tasks": [
    {
      "subject": "국어",
      "unit": "문단의 짜임 — 근거 찾기",
      "problem_count": 2,
      "estimated_time": 5,
      "difficulty": "하",
      "ai_predicted_score": 60
    }
  ]
}
```

**판별 결과 (classify 노드 기대 출력)**:

- `segment = 못함+불성실` (정답률 62 < 90, 완료율 35 < 70)
- `grade_group = lower` (grade 2 ≤ `LOWER_GRADE_MAX`)

> ⚠️ 현재 `tests/conftest.py` `case1_student` fixture는 `grade=1`, `unit="짧은 글 읽기"`로 박혀 있음. 이 시나리오 머지 후 별도 작업으로 fixture 갱신 필요.

### 2-3. 사용 문제 (mock_problems.json 후보)

#### Q1. `q-korean-g2-paper-cup-01` — 종이컵 글, 만들기 재료 찾기

```jsonc
{
  "problem_id": "q-korean-g2-paper-cup-01",
  "subject": "국어",
  "unit": "문단의 짜임 — 근거 찾기",
  "passage": [
    {
      "label": "(가)",
      "text": "종이컵을 만들기 위해서는 여러 가지가 필요합니다. 먼저 종이의 원료가 되는 나무가 필요합니다. 또 물이 필요합니다. 종이컵을 만들기 위해서는 우리가 학교에서 마시는 우유 한 갑의 양만큼 물이 있어야 합니다. 종이컵을 많이 쓰면 쓸수록 나무와 물은 점점 많이 필요하게 됩니다."
    },
    {
      "label": "(나)",
      "text": "그러나 처음부터 종이컵이 나쁜 것은 아니었습니다. 종이컵은 깨지지 않는 컵을 대신하기 위하여 발명되었습니다. 종이컵은 유리컵과는 달리 쉽게 깨지지 않기 때문에 어린아이나 할아버지, 할머니께는 아주 편리한 물건이었습니다."
    },
    {
      "label": "(다)",
      "text": "종이컵을 바르게 사용하기 위해서는 어떻게 해야 할까요? 먼저 꼭 필요한지 생각하며 종이컵을 사용하여야 합니다. 둘째 사용한 종이컵은 반드시 재활용하여야 합니다. 사용한 종이컵을 재활용하기 위해서는 절대로 종이컵을 구겨서는 안 됩니다. 구겨진 종이컵은 재활용할 수 없기 때문입니다. 또, 사용한 종이컵은 반드시 종이컵 수거함에 넣어야 재활용할 수 있습니다."
    }
  ],
  "question": "위 글에서 종이컵을 만들기 위해서 필요한 것을 고르면?",
  "choices": [
    { "id": "1", "label": "물과 우유" },
    { "id": "2", "label": "나무와 물" },
    { "id": "3", "label": "종이와 우유" },
    { "id": "4", "label": "학교와 우유" },
    { "id": "5", "label": "학교와 나무" }
  ],
  "answer": "2",
  "evidence": {
    "paragraph": "(가)",
    "sentence": "먼저 종이의 원료가 되는 나무가 필요합니다. 또 물이 필요합니다."
  },
  "hints": [
    "종이컵을 '만드는' 부분이 어느 문단에 있을까?",
    "(가) 문단을 다시 읽고 '필요합니다'가 나오는 문장을 찾아보자",
    "그 문장에서 두 가지 재료가 같이 나와"
  ],
  "image_card": {
    "image_url": "/assets/mock/paper_cup_making.png",
    "caption": "종이컵은 나무와 물로 만들어요"
  }
}
```

#### Q2. `q-korean-g2-supporting-sentence-01` — 뒷받침 문장 알맞지 않은 것

```jsonc
{
  "problem_id": "q-korean-g2-supporting-sentence-01",
  "subject": "국어",
  "unit": "문단의 짜임 — 뒷받침 문장",
  "topic_sentence": "바다에는 우리에게 필요한 여러 가지가 있습니다.",
  "question": "보기에 제시된 중심 문장을 자세히 설명해주는 뒷받침 문장을 찾으려고 할 때, 알맞지 않은 것은?",
  "choices": [
    { "id": "1", "label": "바닷물을 이용하여 소금을 만들 수 있습니다." },
    { "id": "2", "label": "바닷속에는 석유와 같은 많은 자원이 있습니다." },
    { "id": "3", "label": "바다에서 여러 가지 물고기를 잡을 수 있습니다." },
    { "id": "4", "label": "바다는 태풍이 불어올 때 해일을 일으킬 수 있습니다." },
    { "id": "5", "label": "바다에서 미역, 다시마 등 해산물을 얻을 수 있습니다." }
  ],
  "answer": "4",
  "evidence": {
    "reasoning": "중심 문장이 '필요한 여러 가지'(긍정 자원)를 다루므로, 부정적 현상(태풍/해일)은 뒷받침으로 어울리지 않음"
  },
  "hints": [
    "중심 문장은 '바다에 좋은 것이 많다'는 뜻이야",
    "선택지 중에 '좋은 것'이 아닌 게 하나 있어",
    "태풍이나 해일은 좋은 일일까 나쁜 일일까?"
  ]
}
```

> 케이스 1 시나리오 본문은 **Q1(종이컵)** 을 기준으로 진행한다. Q2는 회귀 테스트용으로 같이 보유.

---

### 2-4. A. 홈화면 진입 (TP1)

`use_case = "talk"`, `current_touchpoint = "tp1"`

#### 턴 1 — 학생 첫 진입

| 항목 | 값 |
|------|-----|
| `request.message` | `{ "type": "init", "content": "" }` |
| classify 결과 | `segment = 못함+불성실`, `grade_group = lower` |
| 응답 메시지 수 | 3 |

**기대 응답** (순서 보장):

1. `text` — 환영 + 이름 호명. 짧고 다정.
   - 예: `"민준아 안녕! 오늘도 같이 해보자."`
2. `text` — 오늘 학습 한 줄 안내. 부담 없이.
   - 예: `"오늘은 국어 한 문제만 가볍게 봐도 충분해."`
3. `choices` — TP1 선택지 4개

**TP1 선택지** (`못함+불성실` × `lower` 정책):

| id | label |
|------|------|
| `home_tp1_one_minute` | 1분만 짧은 글 읽어보기 |
| `home_tp1_one_problem` | 아주 쉬운 문제 1개만 풀기 |
| `home_tp1_image_first` | 그림 보고 문단 내용 골라보기 |
| `home_tp1_ai_pick` | AI가 오늘 할 것 골라주기 |

**검증 포인트**:

| # | 항목 |
|---|------|
| V-TP1-1 | 응답에 `TextMessage` ≥ 1개, `ChoicesMessage` 정확히 1개 |
| V-TP1-2 | `ChoicesMessage.items` 길이 == 4 |
| V-TP1-3 | id 집합 == 위 4개 (snake_case) |
| V-TP1-4 | 첫 텍스트 메시지에 학생 이름 `"민준"` 포함 |
| V-TP1-5 | 어떤 메시지에도 노출 금지 키워드(§1-3) 미포함 |
| V-TP1-6 | 각 텍스트 메시지 길이 ≤ 60자 (lower 가이드) |

> 턴 2(선택지 클릭 후 동작)는 본 시나리오 문서 v1 범위 외 — TP1 노드의 책임은 1턴 응답까지로 본다. 이후 use_case 전환은 라우팅 이슈.

---

### 2-5. B. 학습 중 도움 요청 (TP4)

`use_case = "learning"`, `current_touchpoint = "tp4"`

학생이 Q1(종이컵)을 푸는 중 막힘 → 도움 버튼 클릭 → 챗봇이 막힘 원인 선택지 제공 → 선택에 따라 분기 코칭.

#### 턴 1 — 도움 버튼 클릭 (1단계: 막힘 원인 진단)

| 항목 | 값 |
|------|-----|
| state.current_task | 단원 "문단의 짜임 — 근거 찾기" |
| state.current_problem (가정) | Q1 (`q-korean-g2-paper-cup-01`) |
| `request.message` | `{ "type": "init", "content": "" }` |
| 응답 메시지 수 | 2 |

**기대 응답**:

1. `text` — 부담 낮춘 한 줄. 예: `"어디가 어려워? 같이 보자."`
2. `choices` — 막힘 원인 4개

**TP4 1단계 선택지**:

| id | label | 분기 의도 |
|------|------|-----------|
| `tp4_text_too_long` | 글이 너무 길어 | 글 단위 분해 |
| `tp4_where_to_look` | 어디서 답을 찾아야 할지 모르겠어 | 정답 단서 문단 강조 (이미지 카드 동반) |
| `tp4_choices_similar` | 답이 다 비슷해 보여 | 선택지 좁히기 |
| `tp4_dont_want` | 그냥 하기 싫어 | 초소형 목표 제안 |

#### 턴 2 — 분기별 응답 (2단계: 원인별 코칭)

| 분기 id | request.message | 기대 메시지 타입(set) | 핵심 컨텐츠 |
|---------|-----------------|----------------------|-------------|
| `tp4_text_too_long` | `{ "type": "choice", "content": "tp4_text_too_long" }` | `{text}` (1~2개) | (가) 문단만 짧게 끊어서 다시 보여주기. 마지막 문장: `"이번엔 (가) 문단만 같이 읽어보자."` |
| `tp4_where_to_look` | `{ "type": "choice", "content": "tp4_where_to_look" }` | `{text, image_card}` | image_card: `paper_cup_making.png` + caption `"종이컵은 나무와 물로 만들어요"`. text: `"(가) 문단에서 답을 찾을 수 있어."` |
| `tp4_choices_similar` | `{ "type": "choice", "content": "tp4_choices_similar" }` | `{text, choices}` | text: `"이 중에서 두 개만 보고 골라보자."` choices: 정답 ②번 + 헷갈리기 쉬운 ⑤번을 포함한 2~3개로 좁힌 후보 |
| `tp4_dont_want` | `{ "type": "choice", "content": "tp4_dont_want" }` | `{text}` (1개) | `"한 문제만 같이 해볼까? 진짜 한 개만!"` 초소형 목표 |

**공통 검증** (분기별):

| # | 항목 |
|---|------|
| V-TP4-1 | 4개 분기의 응답 메시지 타입 set이 위 표와 일치 |
| V-TP4-2 | 어떤 분기도 정답 키워드(`"나무와 물"`, `"②"`, `"2번"`) 미포함 |
| V-TP4-3 | 4개 분기 응답 텍스트가 서로 다름 (단순 분기 누락 방지) |
| V-TP4-4 | 노출 금지 키워드(§1-3) 미포함 |
| V-TP4-5 | 각 텍스트 메시지 길이 ≤ 80자 (lower 가이드) |
| V-TP4-6 (`tp4_choices_similar`) | `ChoicesMessage.items` 길이 ∈ {2, 3} |
| V-TP4-7 (`tp4_choices_similar`) | 좁힌 후보 안에 정답 ②번이 포함됨 |
| V-TP4-8 (`tp4_where_to_look`) | `ImageCardMessage.image_url`에 `"paper_cup"` 또는 Q1의 image_card url과 일치 |

#### 턴 3 — 정답 시도 (3단계: 결과 응답)

본 시나리오 문서 v1에서는 검증 대상 외 (T6 1차 PR 범위는 1·2단계). 추후 추가:

- 정답 ② 선택 → `text` 즉시 칭찬 + "다음 1문제만 가볼까?"
- 오답 선택 → `text` 격려 + Q1.hints[0] 1개만 제시

---

### 2-6. 응답 메시지 타입 매핑 (요약)

| 턴 | 분기 키 | text | choices | image_card | hint_card |
|----|---------|------|---------|------------|-----------|
| TP1 turn1 | (init) | ≥1 | 1 | 0 | 0 |
| TP4 turn1 | (init) | 1 | 1 | 0 | 0 |
| TP4 turn2 | `tp4_text_too_long` | 1~2 | 0 | 0 | 0 |
| TP4 turn2 | `tp4_where_to_look` | 1 | 0 | 1 | 0 |
| TP4 turn2 | `tp4_choices_similar` | 1 | 1 | 0 | 0 |
| TP4 turn2 | `tp4_dont_want` | 1 | 0 | 0 | 0 |

> 케이스 1에서 `hint_card`는 사용하지 않는다 (`못함+불성실` 정책: 한 번에 한 행동만 제안). 단계별 힌트는 케이스 2에서 사용.

---

### 2-7. 테스트 케이스 명세 (`parametrize` 입력)

#### `tests/test_tp1.py` — 케이스 1 홈화면

```python
def test_tp1_case1_home_response(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.TALK,
        touchpoint=Touchpoint.TP1,
    )
    response = run_tp1(state)  # 노드 함수 가정

    # V-TP1-1
    assert sum(m.type == "text" for m in response.messages) >= 1
    assert sum(m.type == "choices" for m in response.messages) == 1

    # V-TP1-2,3
    choices = next(m for m in response.messages if m.type == "choices")
    assert len(choices.items) == 4
    assert {item.id for item in choices.items} == {
        "home_tp1_one_minute",
        "home_tp1_one_problem",
        "home_tp1_image_first",
        "home_tp1_ai_pick",
    }

    # V-TP1-4
    first_text = next(m for m in response.messages if m.type == "text")
    assert "민준" in first_text.content

    # V-TP1-5
    full_text = " ".join(m.content for m in response.messages if m.type == "text")
    for forbidden in ["불성실", "회피", "저성취", "고성취", "세그먼트"]:
        assert forbidden not in full_text

    # V-TP1-6
    for m in response.messages:
        if m.type == "text":
            assert len(m.content) <= 60
```

#### `tests/test_tp4.py` — 케이스 1 학습 중 도움 요청 (4분기)

```python
@pytest.mark.parametrize(
    "choice_id, expected_types, extra",
    [
        ("tp4_text_too_long",    {"text"},               {}),
        ("tp4_where_to_look",    {"text", "image_card"}, {}),
        ("tp4_choices_similar",  {"text", "choices"},    {"narrow_min": 2, "narrow_max": 3, "must_include": "2"}),
        ("tp4_dont_want",        {"text"},               {}),
    ],
)
def test_tp4_case1_branch(
    choice_id, expected_types, extra,
    case1_student, make_chat_state, mock_llm,
):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    response = run_tp4(state, choice_id=choice_id)

    # V-TP4-1
    assert {m.type for m in response.messages} == expected_types

    # V-TP4-2
    full_text = " ".join(m.content for m in response.messages if m.type == "text")
    for leak in ["나무와 물", "②", "2번"]:
        assert leak not in full_text

    # V-TP4-4,5
    for forbidden in ["불성실", "회피", "저성취", "고성취"]:
        assert forbidden not in full_text
    for m in response.messages:
        if m.type == "text":
            assert len(m.content) <= 80

    # V-TP4-6,7 (선택지 좁히기 분기 한정)
    if "narrow_min" in extra:
        choices = next(m for m in response.messages if m.type == "choices")
        assert extra["narrow_min"] <= len(choices.items) <= extra["narrow_max"]
        assert any(item.id == extra["must_include"] for item in choices.items)
```

V-TP4-3(분기 응답 텍스트가 서로 다름)는 `parametrize` 로 한 번에 검증하기 어려우므로 별도 회귀 테스트로 분리:

```python
def test_tp4_case1_branches_diverge(case1_student, make_chat_state, mock_llm):
    state_factory = lambda: make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    texts = []
    for cid in ["tp4_text_too_long", "tp4_where_to_look",
                "tp4_choices_similar", "tp4_dont_want"]:
        resp = run_tp4(state_factory(), choice_id=cid)
        texts.append(" ".join(m.content for m in resp.messages if m.type == "text"))
    assert len(set(texts)) == 4  # 모든 분기 텍스트가 서로 다름
```

> **mock_llm fixture 한계**: `tests/conftest.py`의 `FakeLLM`은 모든 호출에 동일 문자열을 반환한다. 따라서 위 테스트가 LLM 분기를 의미 있게 검증하려면, TP4 노드 측에서 분기별 시스템 프롬프트와 메시지 타입 결정을 **LLM 응답이 아니라 노드 코드(분기 로직)** 에서 하도록 짜야 한다. `FakeLLM`은 텍스트 채움용으로만 사용. T6 구현 시 이 점을 주의.

---

## 3. 케이스 2 — 초등 6학년 / 수학 / 비율·비례식

### 3-1. 요약

| 항목 | 값 |
|------|-----|
| 학년 | 6 (`grade_group = upper`) |
| 과목 | 수학 |
| 단원 | 비율과 비례식 |
| 학생 유형 | 못함 + 성실 (`segment = 못함+성실`) |
| 핵심 가치 | 막힘 원인을 진단하고, 개념을 쉬운 설명 + 단계별 풀이 + teach-back 으로 보정 |
| 출처 문제 | `reference/g6-math-example-question-01.png` (소금물 비율) |

### 3-2. 학생 프로필 (mock_students.json 후보)

**student_id**: `case-2-low-diligent-math-g6`

```jsonc
{
  "student_id": "case-2-low-diligent-math-g6",
  "profile": {
    "name": "서연",
    "grade": 6,
    "preferred_subject": "수학",
    "strong_subject": "과학",
    "recent_avg_score": 72,        // 잘함 임계 90 미달 → 못함
    "avg_completion_rate": 88      // 성실 임계 70 이상 → 성실 1차 통과
  },
  "learning_history": {
    "subject_avg_scores": { "수학": 68, "과학": 86 },
    "subject_completion_rates": { "수학": 90, "과학": 88 }
  },
  "learning_pattern": {
    "wrong_content_rate": 75,      // 오답 진행률 50 이상 → 성실 2차 통과
    "wrong_content_total": 3,
    "wrong_content_done": 1,
    "skipping_habit": false,
    "guessing_habit": false,
    "careless_habit": false
  },
  "wrong_answer_pattern": {
    "frequent_wrong_type": "비율과 비례식",
    "repeated_wrong_subjects": ["수학"],
    "wrong_cause": "개념 부족"
  },
  "today_tasks": [
    {
      "subject": "수학",
      "unit": "비율과 비례식",
      "problem_count": 4,
      "estimated_time": 12,
      "difficulty": "중",
      "ai_predicted_score": 74
    }
  ]
}
```

**판별 결과 (classify 노드 기대 출력)**:

- `segment = 못함+성실` (정답률 72 < 90, 완료율 88 ≥ 70 + 오답 진행률 75 ≥ 50)
- `grade_group = upper` (grade 6 > `MIDDLE_GRADE_MAX`)

> ⚠️ 현재 `tests/conftest.py` `case2_student` fixture는 `grade=5`로 박혀 있음. 케이스 1과 동일하게 머지 후 fixture 갱신 필요.

### 3-3. 사용 문제 (mock_problems.json 후보)

#### Q1. `q-math-g6-ratio-saltwater-01` — 소금물의 양에 대한 소금의 양의 비율

```jsonc
{
  "problem_id": "q-math-g6-ratio-saltwater-01",
  "subject": "수학",
  "unit": "비율과 비례식",
  "context": [
    { "label": "(가)", "text": "비커에 소금 37g을 녹여 소금물 148g을 만들었습니다." },
    { "label": "(나)", "text": "비커에 소금 76g을 녹여 소금물 380g을 만들었습니다." }
  ],
  "question": "(가) 비커와 (나) 비커의 소금물의 양에 대한 소금의 양의 비율을 각각 소수로 나타내어 보세요.",
  "answer": { "가": 0.25, "나": 0.2 },
  "concept": {
    "ratio_definition": "비율 = 비교량 ÷ 기준량 = 비교량 / 기준량",
    "for_this_problem": {
      "기준량": "소금물의 양",
      "비교량": "소금의 양"
    }
  },
  "solution_steps": [
    { "step": 1, "content": "'~에 대한 ~의 비율' 구조에서 '에 대한' 앞이 기준량, 뒤가 비교량" },
    { "step": 2, "content": "이 문제에서 기준량은 '소금물의 양', 비교량은 '소금의 양'" },
    { "step": 3, "content": "(가) 비 = 37:148 → 비율 = 37/148 = 1/4 = 0.25" },
    { "step": 4, "content": "(나) 비 = 76:380 → 비율 = 76/380 = 1/5 = 0.2" }
  ],
  "hints": [
    "'에 대한' 앞이 기준량(분모), 뒤가 비교량(분자)이에요",
    "(가)에서 소금물 양과 소금 양은 각각 몇 g인지 다시 짚어볼까요?",
    "분수를 약분해서 0.~ 형태로 바꾸면 깔끔해져요"
  ]
}
```

> 케이스 2 시나리오 본문은 **Q1(소금물)** 을 기준으로 진행한다. 추후 비례식 문제(`a:b = c:d` 형태)를 1개 더 추가하면 회귀 테스트 폭이 넓어진다.

---

### 3-4. A. 홈화면 진입 (TP1)

`use_case = "talk"`, `current_touchpoint = "tp1"`

#### 턴 1 — 학생 첫 진입

| 항목 | 값 |
|------|-----|
| `request.message` | `{ "type": "init", "content": "" }` |
| classify 결과 | `segment = 못함+성실`, `grade_group = upper` |
| 응답 메시지 수 | 3 |

**기대 응답** (순서 보장):

1. `text` — 환영 + 이름 호명. 차분한 코치형 (존댓말 혼합 허용).
   - 예: `"서연아, 오늘도 와줘서 고마워."`
2. `text` — 약점 인지 + 오늘 보정 학습 안내. 평가가 아니라 함께 보자는 톤.
   - 예: `"오늘은 비율 부분을 한 번 같이 짚어볼까? 어렵지 않게 단계로 나눠서 보면 돼."`
3. `choices` — TP1 선택지 4개

**TP1 선택지** (`못함+성실` × `upper` 정책):

| id | label |
|------|------|
| `home_tp1_concept_review` | 비율 개념 쉽게 다시 보기 |
| `home_tp1_retry_wrong` | 어제 틀린 비례식 문제 다시 풀기 |
| `home_tp1_step_by_step` | 한 문제를 단계별로 같이 풀기 |
| `home_tp1_diagnose_stuck` | 내가 어디서 헷갈렸는지 확인하기 |

**검증 포인트**:

| # | 항목 |
|---|------|
| V-TP1-1 | 응답에 `TextMessage` ≥ 1개, `ChoicesMessage` 정확히 1개 |
| V-TP1-2 | `ChoicesMessage.items` 길이 == 4 |
| V-TP1-3 | id 집합 == 위 4개 |
| V-TP1-4 | 첫 텍스트 메시지에 학생 이름 `"서연"` 포함 |
| V-TP1-5 | 어떤 메시지에도 노출 금지 키워드(§1-3) 미포함 |
| V-TP1-6 | 텍스트 메시지에 정답 직접 노출(`0.25`, `0.2`, `1/4`, `1/5`) 미포함 |
| V-TP1-7 | upper 톤 가이드: 텍스트 길이 60~150자 권장 (lower의 ≤ 60과 다름) |

> 케이스 1 lower와 다르게 upper는 한 줄이 너무 짧으면 오히려 어색하다. 짧은 위로 + 학습 의도 + 선택지의 3박자가 자연스러움.

---

### 3-5. B. 학습 중 도움 요청 (TP4)

`use_case = "learning"`, `current_touchpoint = "tp4"`

학생이 Q1(소금물 비율)을 푸는 중 막힘 → 도움 버튼 클릭 → 챗봇이 막힘 원인 선택지 제공 → 선택에 따라 분기 코칭. 마지막에 **teach-back**으로 마무리.

#### 턴 1 — 도움 버튼 클릭 (1단계: 막힘 원인 진단)

| 항목 | 값 |
|------|-----|
| state.current_task | 단원 "비율과 비례식" |
| state.current_problem (가정) | Q1 (`q-math-g6-ratio-saltwater-01`) |
| `request.message` | `{ "type": "init", "content": "" }` |
| 응답 메시지 수 | 2 |

**기대 응답**:

1. `text` — 부담을 낮추는 한 줄. 평가 아닌 진단 톤.
   - 예: `"어떤 부분이 헷갈렸어? 같이 짚어보자."`
2. `choices` — 막힘 원인 4개

**TP4 1단계 선택지**:

| id | label | 분기 의도 |
|------|------|-----------|
| `tp4_ratio_meaning` | 비율 뜻이 헷갈려 | 비유 기반 개념 재설명 |
| `tp4_compare_target` | 어떤 수끼리 비교해야 할지 모르겠어 | 기준량 / 비교량 식별 유도 (선택지 좁히기) |
| `tp4_setup_equation` | 식을 어떻게 세우는지 모르겠어 | 단계별 힌트 카드 |
| `tp4_calc_error` | 계산하다가 틀렸어 | 검산 유도 |

#### 턴 2 — 분기별 응답 (2단계: 원인별 코칭)

| 분기 id | request.message | 기대 메시지 타입(set) | 핵심 컨텐츠 |
|---------|-----------------|----------------------|-------------|
| `tp4_ratio_meaning` | `{ "type": "choice", "content": "tp4_ratio_meaning" }` | `{text}` (1~2개) | 일상 비유로 비율 재설명. 예: "비율은 '전체 중에 얼마'야. 1L 우유에 100mL 시럽을 넣었으면, 우유가 기준량이고 시럽이 비교량인 거지." 정답값(0.25 등) 미포함. |
| `tp4_compare_target` | `{ "type": "choice", "content": "tp4_compare_target" }` | `{text, choices}` | text: `"이 문제에서 기준량이 뭘까? 한번 골라볼래?"`. choices: 기준량 후보 3개 (`option_saltwater`, `option_salt`, `option_water`). |
| `tp4_setup_equation` | `{ "type": "choice", "content": "tp4_setup_equation" }` | `{text, hint_card}` | text: 단계별로 보자는 안내. hint_card.steps 3개로 식 세우기 분해 (아래 참조). |
| `tp4_calc_error` | `{ "type": "choice", "content": "tp4_calc_error" }` | `{text}` (1~2개) | 검산 유도. 예: `"식은 잘 세웠어. 분수를 약분할 때 어떤 수로 나눴는지 다시 한 번 짚어볼까?"`. 정답값(0.25 등) 미포함. |

**`tp4_setup_equation` 분기의 hint_card.steps 예시**:

```jsonc
{
  "type": "hint_card",
  "steps": [
    { "step": 1, "content": "'에 대한' 앞이 기준량, 뒤가 비교량이에요" },
    { "step": 2, "content": "(가) 비커에서 기준량(소금물)과 비교량(소금)을 g 단위로 적어보세요" },
    { "step": 3, "content": "비율 = 비교량 ÷ 기준량 으로 식을 세우면 돼요" }
  ]
}
```

> hint_card.steps의 마지막 단계에서도 정답 수치(0.25, 0.2)는 노출하지 않는다. 학생이 직접 계산하도록 유도.

#### `tp4_compare_target` 분기 선택지 상세

| id | label |
|------|------|
| `option_saltwater` | 소금물의 양 (정답: 기준량) |
| `option_salt` | 소금의 양 (비교량) |
| `option_water` | 물의 양 (오답) |

#### 공통 검증 (분기별)

| # | 항목 |
|---|------|
| V-TP4-1 | 4개 분기의 응답 메시지 타입 set이 위 표와 일치 |
| V-TP4-2 | 어떤 분기도 정답 키워드(`"0.25"`, `"0.2"`, `"1/4"`, `"1/5"`) 미포함 |
| V-TP4-3 | 4개 분기 응답 텍스트가 서로 다름 |
| V-TP4-4 | 노출 금지 키워드(§1-3) 미포함 |
| V-TP4-5 | 텍스트 메시지 길이 60~150자 권장 (upper) |
| V-TP4-6 (`tp4_compare_target`) | `ChoicesMessage.items` 길이 == 3, id 집합 == {`option_saltwater`, `option_salt`, `option_water`} |
| V-TP4-7 (`tp4_setup_equation`) | `HintCardMessage.steps` 길이 ≥ 2, 각 step에 정답 수치 미포함 |

#### 턴 3 — teach-back (3단계, v1 범위 외)

본 시나리오 문서 v1에서는 검증 대상 외. 추후 추가 예정:

- 학생이 정답 도달 → 챗봇이 `text` 로 `"이걸 너의 말로 다시 한 번 설명해줄 수 있어?"` 질문
- 학생이 텍스트 입력으로 자기 설명 → LLM 판정:
  - 충분 → `text` 칭찬 + 다음 문제 안내
  - 부족 → `text` 부족한 부분 보충 + 격려

teach-back은 케이스 2의 핵심 차별점 (개념 부족형 보정에 가장 효과적). T6 후속 PR 또는 별도 이슈로 분리.

---

### 3-6. 응답 메시지 타입 매핑 (요약)

| 턴 | 분기 키 | text | choices | image_card | hint_card |
|----|---------|------|---------|------------|-----------|
| TP1 turn1 | (init) | ≥1 | 1 | 0 | 0 |
| TP4 turn1 | (init) | 1 | 1 | 0 | 0 |
| TP4 turn2 | `tp4_ratio_meaning` | 1~2 | 0 | 0 | 0 |
| TP4 turn2 | `tp4_compare_target` | 1 | 1 | 0 | 0 |
| TP4 turn2 | `tp4_setup_equation` | 1 | 0 | 0 | 1 |
| TP4 turn2 | `tp4_calc_error` | 1~2 | 0 | 0 | 0 |

> 케이스 2에서 `image_card`는 사용하지 않는다 (`못함+성실` × `upper` 정책: 텍스트와 단계별 힌트 카드 우선). 이미지 카드는 케이스 1에서 사용.

---

### 3-7. 테스트 케이스 명세 (`parametrize` 입력)

#### `tests/test_tp1.py` — 케이스 2 홈화면

```python
def test_tp1_case2_home_response(case2_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.TALK,
        touchpoint=Touchpoint.TP1,
    )
    response = run_tp1(state)

    # V-TP1-1
    assert sum(m.type == "text" for m in response.messages) >= 1
    assert sum(m.type == "choices" for m in response.messages) == 1

    # V-TP1-2,3
    choices = next(m for m in response.messages if m.type == "choices")
    assert len(choices.items) == 4
    assert {item.id for item in choices.items} == {
        "home_tp1_concept_review",
        "home_tp1_retry_wrong",
        "home_tp1_step_by_step",
        "home_tp1_diagnose_stuck",
    }

    # V-TP1-4
    first_text = next(m for m in response.messages if m.type == "text")
    assert "서연" in first_text.content

    # V-TP1-5,6
    full_text = " ".join(m.content for m in response.messages if m.type == "text")
    for forbidden in ["불성실", "회피", "저성취", "고성취", "세그먼트"]:
        assert forbidden not in full_text
    for leak in ["0.25", "0.2", "1/4", "1/5"]:
        assert leak not in full_text
```

#### `tests/test_tp4.py` — 케이스 2 학습 중 도움 요청 (4분기)

```python
@pytest.mark.parametrize(
    "choice_id, expected_types, extra",
    [
        ("tp4_ratio_meaning",   {"text"},               {}),
        ("tp4_compare_target",  {"text", "choices"},    {
            "narrow_size": 3,
            "expected_ids": {"option_saltwater", "option_salt", "option_water"},
        }),
        ("tp4_setup_equation",  {"text", "hint_card"},  {"min_steps": 2}),
        ("tp4_calc_error",      {"text"},               {}),
    ],
)
def test_tp4_case2_branch(
    choice_id, expected_types, extra,
    case2_student, make_chat_state, mock_llm,
):
    state = make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    response = run_tp4(state, choice_id=choice_id)

    # V-TP4-1
    assert {m.type for m in response.messages} == expected_types

    # V-TP4-2 — 정답 수치 노출 금지
    full_text = " ".join(
        m.content for m in response.messages if m.type == "text"
    )
    for leak in ["0.25", "0.2", "1/4", "1/5"]:
        assert leak not in full_text

    # V-TP4-4
    for forbidden in ["불성실", "회피", "저성취", "고성취"]:
        assert forbidden not in full_text

    # V-TP4-6 — 비교 대상 좁히기 분기 한정
    if "narrow_size" in extra:
        choices = next(m for m in response.messages if m.type == "choices")
        assert len(choices.items) == extra["narrow_size"]
        assert {item.id for item in choices.items} == extra["expected_ids"]

    # V-TP4-7 — 식 세우기 분기 한정
    if "min_steps" in extra:
        hint = next(m for m in response.messages if m.type == "hint_card")
        assert len(hint.steps) >= extra["min_steps"]
        for step in hint.steps:
            for leak in ["0.25", "0.2", "1/4", "1/5"]:
                assert leak not in step.content
```

V-TP4-3(분기별 텍스트 다름)는 케이스 1과 동일하게 별도 회귀 테스트로 분리:

```python
def test_tp4_case2_branches_diverge(case2_student, make_chat_state, mock_llm):
    state_factory = lambda: make_chat_state(
        case2_student,
        segment=Segment.LOW_DILIGENT,
        grade_group=GradeGroup.UPPER,
        use_case=UseCase.LEARNING,
        touchpoint=Touchpoint.TP4,
    )
    texts = []
    for cid in ["tp4_ratio_meaning", "tp4_compare_target",
                "tp4_setup_equation", "tp4_calc_error"]:
        resp = run_tp4(state_factory(), choice_id=cid)
        texts.append(" ".join(m.content for m in resp.messages if m.type == "text"))
    assert len(set(texts)) == 4
```

> **mock_llm 한계 (재확인)**: 케이스 1과 동일하게 `FakeLLM`이 동일 문자열을 반환하므로, 분기별 메시지 타입(특히 `hint_card`, `choices` 부속) 결정은 **TP4 노드 코드의 분기 로직**에서 deterministic하게 처리해야 함. LLM은 `text` 메시지의 자연어 부분만 채우는 역할.

---

## 4. 케이스 1·2 비교 (요약)

두 케이스의 핵심 차이점을 빠르게 잡고 싶을 때 보는 표. 상세는 §2(케이스 1), §3(케이스 2) 본문 참조.

| 항목 | 케이스 1 | 케이스 2 |
|------|---------|---------|
| 학년 / `grade_group` | 초2 / `lower` | 초6 / `upper` |
| 과목 / 단원 | 국어 / 문단 짜임·근거 찾기 | 수학 / 비율과 비례식 |
| 학생 유형 (`segment`) | `못함+불성실` | `못함+성실` |
| 핵심 시연 가치 | 진입장벽 낮추기, 한 번에 하나만 | 단계별 개념 보정, teach-back |
| 페르소나 톤 | 짧고 다정, 한 번에 한 행동 | 차분한 코치형, 존댓말 혼합 |
| 텍스트 길이 가이드 | ≤ 60자 | 60~150자 |
| 사용하는 메시지 타입 | `text` / `choices` / **`image_card`** | `text` / `choices` / **`hint_card`** |
| 사용하지 않는 타입 | `hint_card` | `image_card` |
| TP1 선택지 컨셉 | 1분 / 1문제 / 그림 / AI가 골라줌 | 개념 복습 / 어제 오답 / 단계별 / 헷갈린 곳 진단 |
| TP4 4분기 | 글 길어 / 어디 봐야 / 답 비슷 / 하기 싫어 | 비율 뜻 / 비교 대상 / 식 세우기 / 계산 오류 |
| TP4 `image_card` 사용 분기 | `tp4_where_to_look` (정답 단서 문단 강조) | — |
| TP4 `hint_card` 사용 분기 | — | `tp4_setup_equation` (3-step 분해) |
| TP4 선택지 좁히기 분기 | `tp4_choices_similar` (정답 후보 2~3개) | `tp4_compare_target` (기준량 후보 3개) |
| 정답 누설 금지 키워드 | `"나무와 물"`, `"②"`, `"2번"` | `"0.25"`, `"0.2"`, `"1/4"`, `"1/5"` |
| 마지막 단계 | 칭찬 + 다음 1문제 (간단) | **teach-back** (v1 범위 외) |
| 출처 이미지 | `reference/g2-korean-*.png` × 2 | `reference/g6-math-*.png` × 1 |
| 학생 fixture id | `case-1-low-lazy-korean-g2` | `case-2-low-diligent-math-g6` |

---

## 5. 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-04-28 | 케이스 1 (초2 국어, 문단의 짜임·근거 찾기) 시나리오 v1 작성. 케이스 2 placeholder. |
| 2026-04-28 | 케이스 2 (초6 수학, 비율과 비례식 — 소금물 문제) 시나리오 v1 작성. |
| 2026-04-28 | 케이스 1·2 비교 요약표(§4) 추가. |
