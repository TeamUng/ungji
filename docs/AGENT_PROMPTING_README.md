# Agent And Prompting README / 에이전트 및 프롬프트 README

## 한국어

이 문서는 학습 코치 LangGraph 에이전트 구조와 프롬프트를 어디서 수정해야 하는지 설명합니다.

### 전체 흐름

1. `classify` 노드가 `student_id`로 목업 학생 데이터를 로드하고 학년 그룹과 세그먼트를 계산합니다.
2. `graph`가 `use_case`와 `current_touchpoint`에 따라 에이전트를 라우팅합니다.
3. `motivator`는 TP1, TP2, TP3, TP5 및 일반 채팅을 담당합니다.
4. `helper`는 TP4 문제 풀이 도움을 담당합니다.
5. `graph`는 코치 응답을 `AIMessage`로 `chat_history`에 추가하여 다음 턴의 LLM 컨텍스트에 포함시킵니다.

### 프롬프트를 수정하는 위치

- 공통 시스템 프롬프트 조립: `app/services/prompts/agents.py`
  - `build_system_prompt(...)`가 학년별 페르소나, 세그먼트별 전략, 에이전트 역할을 합칩니다.
  - `MOTIVATOR_ROLE`, `HELPER_ROLE`은 각 에이전트의 기본 역할 정의입니다.

- 학년별 말투와 캐릭터: `app/services/prompts/personas.py`
  - 저학년, 중학년, 고학년별 문장 길이, 말투, 설명 밀도를 조정합니다.
  - 브로핑 캐릭터의 금지 표현과 말버릇도 여기서 관리합니다.

- 세그먼트별 코칭 전략: `app/services/prompts/coaching.py`
  - `잘함/못함`과 `성실/불성실` 조합별 코칭 강도를 조정합니다.

- TP1, TP2, TP3, TP5 상황 프롬프트: `app/services/nodes/motivator.py`
  - `_situation_tp1(...)`: 홈 화면의 4개 단원 카드 컨텍스트를 전달하고, 하나만 추천하도록 지시합니다.
  - `_situation_tp2(...)`: 단원 완료 후 다음 단원 추천.
  - `_situation_tp3(...)`: 이탈 방지.
  - `_situation_tp5(...)`: 학습 종료 및 오답 복습 유도.

- TP4 문제 도움 프롬프트와 도구 지시: `app/services/nodes/helper.py`
  - `_coach_tp4(...)`가 TP4의 핵심 agentic 코칭 프롬프트입니다.
  - 선택지는 백엔드 분류값이 아니라 아이가 막힌 지점을 말하기 쉽게 만드는 UX 보조 수단입니다.
  - LLM은 전체 `chat_history`를 보고 다음 행동을 스스로 결정합니다.

### 에이전트별 도구 사용

| 단계 | 노드/에이전트 | LLM 사용 | 도구 | 설명 |
|---|---|---:|---|---|
| 분류 | `classify` | 아니오 | `load_student(...)` | 학생 목업 데이터를 로드하고 `GradeGroup`, `Segment`를 계산합니다. |
| 라우팅 | `graph` | 아니오 | 없음 | `use_case`와 `touchpoint`로 `motivator` 또는 `helper`를 선택합니다. |
| TP1/TP2/TP3/TP5 | `motivator` | 예 | 없음 | 일반 텍스트 응답만 생성합니다. |
| TP4 | `helper` | 예 | `send_causes` | 아이가 어디서 막혔는지 직접 말하기 어려울 때 선택지를 만듭니다. |
| TP4 | `helper` | 예 | `send_text` | 일반 코칭 텍스트를 보냅니다. |
| TP4 | `helper` | 예 | `send_hint_card` | 단계별 힌트 카드가 적합할 때 사용합니다. |
| TP4 | `helper` | 예 | `send_image_card` | 시각 자료 설명이 필요할 때 사용합니다. |
| 응답 저장 | `graph` | 아니오 | 없음 | 응답을 `AIMessage`로 `chat_history`에 추가합니다. |

### 프롬프트 엔지니어링 원칙

- 먼저 `personas.py`, `coaching.py`, `agents.py`에서 공통 행동을 조정하세요.
- 특정 터치포인트에서만 필요한 맥락은 `motivator.py` 또는 `helper.py`의 상황 프롬프트에 넣으세요.
- TP4에서는 새 규칙 기반 상태를 추가하기 전에, LLM이 대화 기록과 도구를 통해 해결할 수 있는지 먼저 확인하세요.
- `send_causes` 선택지는 아이를 돕는 UI일 뿐입니다. 선택지를 백엔드에서 고정 분류로 해석하지 마세요.
- 새 프롬프트는 가능하면 테스트로 고정하세요. 관련 테스트:
  - `tests/test_prompts.py`
  - `tests/test_motivator_tp1.py`
  - `tests/test_helper.py`
  - `tests/test_graph.py`

### 데이터와 프롬프트의 관계

- `app/data/mock_students.json`
  - 학생 프로필과 홈 화면에 보이는 4개 curriculum unit을 정의합니다.
  - 각 unit은 TP4 시뮬레이션에 사용할 `problem_ids`를 가질 수 있습니다.

- `app/data/mock_problems.json`
  - TP4에서 문제 도움을 시뮬레이션하기 위한 작은 문제 단위 목업입니다.
  - 홈 화면 단원 목록의 원천이 아닙니다.

## English

This document explains the LangGraph agent structure and where to edit prompts.

### Overall Flow

1. The `classify` node loads mock student data by `student_id` and computes grade group and segment.
2. `graph` routes by `use_case` and `current_touchpoint`.
3. `motivator` handles TP1, TP2, TP3, TP5, and regular chat turns.
4. `helper` handles TP4 problem-help coaching.
5. `graph` appends coach responses into `chat_history` as `AIMessage`s so later turns include the full conversation.

### Where To Edit Prompts

- Shared system prompt assembly: `app/services/prompts/agents.py`
  - `build_system_prompt(...)` combines grade persona, segment strategy, and agent role.
  - `MOTIVATOR_ROLE` and `HELPER_ROLE` define each agent's base role.

- Grade-specific tone and character: `app/services/prompts/personas.py`
  - Controls sentence length, tone, explanation density, and character rules for lower/middle/upper grades.

- Segment-specific coaching strategy: `app/services/prompts/coaching.py`
  - Controls coaching style for high/low ability and diligent/lazy combinations.

- TP1, TP2, TP3, TP5 situation prompts: `app/services/nodes/motivator.py`
  - `_situation_tp1(...)`: passes the 4 home-screen curriculum units and asks the coach to recommend exactly one.
  - `_situation_tp2(...)`: after a unit is completed, recommends the next unit.
  - `_situation_tp3(...)`: exit prevention.
  - `_situation_tp5(...)`: end-of-study wrap-up and wrong-answer review nudge.

- TP4 problem-help prompt and tool instructions: `app/services/nodes/helper.py`
  - `_coach_tp4(...)` is the main agentic TP4 coaching prompt.
  - Choices are not backend categories. They are a child-friendly scaffold for naming confusion.
  - The LLM reads the full `chat_history` and decides the next action.

### Tools By Agent And Workflow Stage

| Stage | Node/Agent | Uses LLM | Tools | Purpose |
|---|---|---:|---|---|
| Classification | `classify` | No | `load_student(...)` | Loads mock student data and computes `GradeGroup` and `Segment`. |
| Routing | `graph` | No | None | Routes to `motivator` or `helper`. |
| TP1/TP2/TP3/TP5 | `motivator` | Yes | None | Generates text-only coaching responses. |
| TP4 | `helper` | Yes | `send_causes` | Offers stuck-reason choices when a child may not know how to explain the difficulty. |
| TP4 | `helper` | Yes | `send_text` | Sends ordinary coaching text. |
| TP4 | `helper` | Yes | `send_hint_card` | Sends step-by-step hints. |
| TP4 | `helper` | Yes | `send_image_card` | Requests/represents visual support. |
| Memory | `graph` | No | None | Appends coach output to `chat_history` as `AIMessage`. |

### Prompt Engineering Principles

- Start with `personas.py`, `coaching.py`, and `agents.py` for global behavior changes.
- Put touchpoint-specific context into `motivator.py` or `helper.py`.
- For TP4, prefer agentic prompt/tool behavior over adding rule-based state.
- `send_causes` is a UI scaffold for children, not a fixed backend classifier.
- Add or update tests when changing prompt behavior. Useful tests:
  - `tests/test_prompts.py`
  - `tests/test_motivator_tp1.py`
  - `tests/test_helper.py`
  - `tests/test_graph.py`

### Data And Prompt Relationship

- `app/data/mock_students.json`
  - Defines student profiles and the 4 home-screen curriculum units.
  - Each unit may contain `problem_ids` for TP4 simulation.

- `app/data/mock_problems.json`
  - Defines small problem-level fixtures for TP4 help.
  - It is not the source of the home-screen unit list.
