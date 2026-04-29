# TODO: Two-Agent Refactor + System Prompt Centralization

> **Purpose:** Replace the current 5 individual TP node files + general_chat with two
> persistent agents (Motivator, Helper) and centralize all system prompt assembly.
> Send this file to a coding agent to implement.

---

## Background & Motivation

### Problem with current architecture
1. Every TP file duplicates "당신은 스마트올 AI 학습 코치입니다..." — agent identity
   is scattered across 5 files instead of being defined once.
2. `general_chat.py` is an isolated free-chat node with no memory of which agent the
   student was already talking to. If a student replies after a TP1 message, the response
   feels disconnected.
3. Six separate node files (tp1–tp5 + general_chat) do not reflect the real logical
   grouping: there are only TWO agents.

### Target architecture
| Agent | Handles | Style |
|---|---|---|
| **Motivator** | TP1, TP2, TP3, TP5, CHAT (non-TP4) | Single LLM call, TextMessage only |
| **Helper** | TP4 / UseCase.LEARNING | Tool calling (send_causes / send_text / send_hint_card / send_image_card) |

Conversation continuity is provided by `InMemorySaver` — `chat_history` accumulates
across all turns and is passed to whichever agent fires next. A student can reply
freely at any point; the correct agent picks up the history and responds naturally.

---

## Files to CREATE

### 1. `app/services/prompts/agents.py` (new)

Centralizes agent identity and system prompt assembly. All TP logic must use
`build_system_prompt()` — never repeat persona/strategy/role inline.

```python
from app.core.enums import GradeGroup, Segment
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

# ── Agent role descriptions ───────────────────────────────────────────────────
# These are the ONLY place the "당신은 스마트올..." identity strings live.

MOTIVATOR_ROLE = (
    "당신은 스마트올 AI 학습 동기 코치입니다.\n"
    "학생이 홈화면에 진입하거나, 과제를 완료하거나, 이탈하려 하거나, "
    "학습을 마무리할 때 함께합니다.\n"
    "학생과 나눈 대화 맥락을 기억하고, 자연스럽게 이어서 응답하세요.\n"
    "응답은 항상 간결하게(2~4문장), 강요하지 않으며, 학생이 선택할 수 있게 해주세요."
)

HELPER_ROLE = (
    "당신은 스마트올 AI 학습 도우미입니다.\n"
    "학생이 문제를 풀다 막혔을 때 원인을 파악하고 단계별로 돕습니다.\n"
    "정답을 직접 알려주지 말고, 학생이 스스로 깨달을 수 있도록 유도하세요.\n"
    "학생과 나눈 대화 맥락을 기억하고, 자연스럽게 이어서 응답하세요."
)


def build_system_prompt(
    grade_group: GradeGroup,
    segment: Segment,
    role: str,
) -> str:
    """에이전트 시스템 프롬프트 조립.

    순서: 페르소나(말투) → 코칭 전략(학생 유형별 접근) → 에이전트 역할(정체성).
    모든 TP/에이전트 파일은 이 함수만 사용한다.
    """
    return (
        f"{get_persona(grade_group)}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        f"{role}"
    )
```

---

### 2. `app/services/nodes/motivator.py` (new — replaces tp1, tp2, tp3, tp5, general_chat)

One node, one agent identity. Dispatches situational context by `current_touchpoint`.
`chat_history` is always included so conversation is continuous.

```python
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import Touchpoint
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.agents import MOTIVATOR_ROLE, build_system_prompt

logger = get_logger(__name__)

# Maximum number of prior chat turns passed to the LLM for continuity.
_HISTORY_WINDOW = 20


def motivator(state: ChatState) -> ChatResponse:
    """Motivator agent — handles TP1, TP2, TP3, TP5, and free CHAT turns."""
    from app.clients.upstage import llm

    grade_group = state["grade_group"]
    segment = state["segment"]
    touchpoint = state["current_touchpoint"]
    chat_history = state.get("chat_history", [])

    system_prompt = build_system_prompt(grade_group, segment, MOTIVATOR_ROLE)
    situation = _get_situation(state)

    # Recent chat history provides continuity across all prior turns.
    recent = chat_history[-_HISTORY_WINDOW:] if len(chat_history) > _HISTORY_WINDOW else chat_history

    messages = [SystemMessage(content=system_prompt)]
    if recent:
        messages += list(recent)
    if situation:
        # Situational context is injected as a system-level addendum so it does
        # not appear as a student message in the chat history.
        messages.append(SystemMessage(content=f"[현재 상황]\n{situation}"))

    logger.info(
        "motivator 노드 호출",
        extra={
            "student_id": state["student_id"],
            "touchpoint": touchpoint.value if touchpoint else "chat",
            "segment": segment.value,
        },
    )

    response = llm.invoke(messages)

    logger.info("motivator 노드 완료", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(response.content)])


# ── Situational context per touchpoint ───────────────────────────────────────
# These are SHORT, factual descriptions of what is happening RIGHT NOW.
# Agent identity, tone, and strategy live in build_system_prompt — NOT here.

def _get_situation(state: ChatState) -> str:
    touchpoint = state.get("current_touchpoint")

    if touchpoint == Touchpoint.TP1:
        return _situation_tp1(state)
    if touchpoint == Touchpoint.TP2:
        return _situation_tp2(state)
    if touchpoint == Touchpoint.TP3:
        return _situation_tp3(state)
    if touchpoint == Touchpoint.TP5:
        return _situation_tp5(state)
    # UseCase.CHAT — no extra situation needed, history is enough.
    return ""


def _situation_tp1(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    pattern = state["learning_pattern"]

    task_lines = []
    for i, task in enumerate(today_tasks, 1):
        score_info = f", AI 예상점수 {task['ai_predicted_score']}점" if task.get("ai_predicted_score") else ""
        task_lines.append(
            f"{i}. {task['subject']} - {task['unit']} (난이도: {task['difficulty']}{score_info})"
        )

    habits = [k for k, v in {
        "건너뛰는 습관": pattern.get("skipping_habit"),
        "찍는 습관": pattern.get("guessing_habit"),
        "대충 푸는 습관": pattern.get("careless_habit"),
    }.items() if v]

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)이 홈화면에 진입했습니다.\n"
        f"최근 평균 점수: {profile['recent_avg_score']}점 / "
        f"선호 과목: {profile['preferred_subject']} / 잘하는 과목: {profile['strong_subject']}\n"
        + (f"학습 습관: {', '.join(habits)}\n" if habits else "")
        + f"오늘의 과제:\n" + "\n".join(task_lines) + "\n\n"
        "인사하고, 오늘 과제 중 이 학생에게 가장 적합한 한 가지를 구체적인 이유와 함께 추천하세요."
    )


def _situation_tp2(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = [t for t in today_tasks if t not in completed_tasks]

    completed_str = ", ".join(t["subject"] for t in completed_tasks) or "없음"
    remaining_lines = [
        f"- {t['subject']}: {t['unit']} (난이도: {t['difficulty']})" for t in remaining
    ]

    if remaining:
        situation = (
            f"완료: {completed_str} ({len(completed_tasks)}/{len(today_tasks)}개)\n"
            f"남은 과제:\n" + "\n".join(remaining_lines) + "\n\n"
            "방금 과제를 완료한 학생을 격려하고, 다음으로 할 과제 하나를 추천하세요."
        )
    else:
        situation = (
            f"모든 과제 완료! ({len(today_tasks)}/{len(today_tasks)}개)\n\n"
            "모든 과제를 마친 학생을 크게 칭찬하고 북클럽(독서 코너)으로 안내하세요: "
            "'오늘 모든 학습을 마쳤어! 이제 북클럽에서 짧은 이야기 하나 읽어볼까?'"
        )
    return f"학생: {profile['name']} ({profile['grade']}학년)\n{situation}"


def _situation_tp3(state: ChatState) -> str:
    profile = state["student_profile"]
    current_task = state.get("current_task")
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining_count = len(today_tasks) - len(completed_tasks)

    task_info = ""
    if current_task:
        task_info = f"현재 과제: {current_task['subject']} - {current_task['unit']}\n"

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)이 학습 중에 이탈하려 합니다.\n"
        f"{task_info}"
        f"남은 과제: {remaining_count}개\n\n"
        "강요하지 말고 공감하며, 잠깐 쉬고 돌아오도록 부드럽게 유도하세요. "
        "응답은 2~3문장, 선택지를 주세요."
    )


def _situation_tp5(state: ChatState) -> str:
    profile = state["student_profile"]
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]

    wrong_total = pattern.get("wrong_content_total", 0)
    wrong_done = pattern.get("wrong_content_done", 0)

    if not has_wrong:
        wrong_summary = "오늘 틀린 문제가 없어요!"
    elif wrong_done_today:
        wrong_summary = f"오늘 오답 {wrong_total}개를 다 복습했어요."
    else:
        remaining = wrong_total - wrong_done
        wrong_summary = f"오답 {wrong_total}개 중 {remaining}개가 남아있어요."

    completed_str = ", ".join(t["subject"] for t in completed_tasks) or "없음"

    return (
        f"학생 {profile['name']} ({profile['grade']}학년)의 오늘 학습이 끝났습니다.\n"
        f"완료한 과제: {completed_str} ({len(completed_tasks)}/{len(today_tasks)}개)\n"
        f"오답 현황: {wrong_summary}\n"
        f"오늘 평균 점수: {state['today_score']}점\n\n"
        "오늘 학습을 진심으로 마무리해주세요. "
        "오답이 남았으면 부드럽게 복습을 권유하고, 없으면 크게 칭찬하세요."
    )
```

---

### 3. `app/services/nodes/helper.py` (new — replaces tp4.py)

Same tool-calling logic as the current `tp4.py`, but uses `build_system_prompt` with
`HELPER_ROLE` instead of inline identity strings. The internal turn detection and tool
definitions stay the same.

```python
# Rename tp4.py → helper.py and make these changes:

# CHANGE 1: import
from app.services.prompts.agents import HELPER_ROLE, build_system_prompt

# CHANGE 2: _generate_causes — replace the system_prompt construction
system_prompt = build_system_prompt(grade_group, segment, HELPER_ROLE) + (
    "\n\n학생이 문제를 풀다가 막혀서 도움을 요청했습니다.\n"
    "주어진 문제와 학생 정보를 바탕으로, 이 학생이 막혔을 만한 원인 3~4가지를 "
    "선택지로 제시해주세요.\n"
    "반드시 send_causes 도구를 호출해 선택지를 전달하세요.\n"
    "각 선택지 id는 영문 snake_case로, label은 학생이 클릭하기 쉬운 짧은 한국어 문장으로 작성하세요."
)

# CHANGE 3: _build_coaching — replace the system_prompt construction
system_prompt = build_system_prompt(grade_group, segment, HELPER_ROLE) + (
    "\n\n학생이 막힌 원인을 선택했습니다. 이 원인에 맞게 학생을 도와주세요.\n"
    "적절한 도구를 골라 응답하세요:\n"
    "- send_text: 일반 코칭 텍스트\n"
    "- send_hint_card: 단계별 힌트가 효과적일 때\n"
    "- send_image_card: 그림/시각 자료로 설명할 때\n"
    "하나 또는 두 개의 도구를 사용하세요."
)

# CHANGE 4: public function rename — tp4() → helper()
# All internal helpers (_try_load_problem, _generate_causes, etc.) keep their names.
```

The `helper()` function signature and return value stay identical to the current `tp4()`.

---

## Files to MODIFY

### 4. `app/services/graph.py`

Update imports and routing. The routing logic changes are:

```python
# Old imports (remove):
from app.services.nodes.tp1 import tp1
from app.services.nodes.tp2 import tp2
from app.services.nodes.tp3 import tp3
from app.services.nodes.tp4 import tp4
from app.services.nodes.tp5 import tp5
from app.services.nodes.general_chat import general_chat

# New imports (add):
from app.services.nodes.motivator import motivator
from app.services.nodes.helper import helper

# Old node wrappers (remove):
# _tp1_node, _tp2_node, _tp3_node, _tp4_node, _tp5_node, _general_chat_node

# New node wrappers:

def _motivator_node(state: ChatState) -> dict:
    return {"response": motivator(state)}


def _helper_node(state: ChatState) -> dict:
    result = helper(state)
    messages = result["helper_response"]   # note: rename tp4_response → helper_response
    extra = {"response": make_chat_response(state["thread_id"], messages)}
    if "current_problem" in result:
        extra["current_problem"] = result["current_problem"]
    return extra


# New _route():
def _route(state: ChatState) -> str:
    use_case = state["use_case"]
    touchpoint = state["current_touchpoint"]

    if use_case == UseCase.LEARNING:
        if touchpoint != Touchpoint.TP4:
            raise ValueError(f"use_case=learning은 tp4만 허용됩니다. 받은 값: {touchpoint}")
        return "helper"

    if use_case == UseCase.CHAT:
        # Route free chat to whichever agent the student was last talking to.
        if touchpoint == Touchpoint.TP4:
            return "helper"
        return "motivator"

    # UseCase.TALK
    if touchpoint == Touchpoint.TP4:
        raise ValueError(f"use_case=talk에서 tp4는 허용되지 않습니다.")
    if touchpoint in (Touchpoint.TP1, Touchpoint.TP2, Touchpoint.TP3, Touchpoint.TP5):
        return "motivator"
    raise ValueError(f"지원하지 않는 touchpoint: {touchpoint}")


# Graph assembly — replace old nodes with new ones:
_builder.add_node("classify", classify)
_builder.add_node("motivator", _motivator_node)
_builder.add_node("helper", _helper_node)
```

---

### 5. `app/services/nodes/helper.py` — internal return key rename

In the current `tp4.py`, the result dict uses key `"tp4_response"`. Rename to
`"helper_response"` everywhere inside `helper.py` for clarity:
- `return {"helper_response": messages, "current_problem": ...}` (Turn 1)
- `return {"helper_response": messages}` (Turn 2)

Also update `_helper_node` in `graph.py` accordingly (already shown above).

---

### 6. `app/services/nodes/tp5.py` — remove `_build_wrong_answer_summary`

Once TP5 logic moves into `motivator.py` (`_situation_tp5`), the standalone
`_build_wrong_answer_summary` function in tp5.py is no longer needed as a public
export. It will live as an inline helper inside `_situation_tp5`.

---

## Files to DELETE

Once the above files are created and tests pass, delete:

```
app/services/nodes/tp1.py
app/services/nodes/tp2.py
app/services/nodes/tp3.py
app/services/nodes/tp4.py
app/services/nodes/tp5.py
app/services/nodes/general_chat.py
```

Delete them only after all tests pass to avoid breaking the test suite mid-refactor.

---

## Tests to UPDATE

### `tests/conftest.py`
- `make_chat_state` fixture: no changes needed (ChatState fields unchanged).
- `FakeLLM` fixture: already has `bind_tools()` support — no changes needed.

### `tests/test_tp1.py` → `tests/test_motivator_tp1.py` (rename + rewrite)
Test the `motivator()` function directly with `current_touchpoint=Touchpoint.TP1`.
Assertions:
- Returns `ChatResponse` with at least one `TextMessage`.
- System prompt passed to LLM contains persona keywords (e.g. "이모" for LOWER).
- User message / situation context contains student name and task info.
- Does NOT contain internal segment names (LOW_LAZY etc.) in response content.

### `tests/test_tp2.py` → merge into `tests/test_motivator_tp2.py`
Test `motivator()` with `current_touchpoint=Touchpoint.TP2`.
Assertions:
- Returns `ChatResponse` with `TextMessage`.
- Situation context includes completed/remaining task counts.

### `tests/test_tp3.py` → merge into `tests/test_motivator_tp3.py`
Test `motivator()` with `current_touchpoint=Touchpoint.TP3`.
Assertions:
- Returns `ChatResponse` with `TextMessage`.
- Situation context mentions current task and remaining count.

### `tests/test_tp5.py` → merge into `tests/test_motivator_tp5.py`
Test `motivator()` with `current_touchpoint=Touchpoint.TP5`.
Assertions (replacing old `_build_wrong_answer_summary` import tests):
- Returns `ChatResponse` with `TextMessage`.
- Situation context passed to LLM contains wrong answer summary text.
- "남아있어요" or "다 복습했어요" or "없어요" appears in the situation string
  depending on state flags.

### `tests/test_tp4.py` → `tests/test_helper.py` (rename + minimal update)
- Change all `from app.services.nodes.tp4 import tp4` → `from app.services.nodes.helper import helper`
- Change all `tp4(state)` → `helper(state)`
- Change all `result["tp4_response"]` → `result["helper_response"]`
- Test logic (Turn 1/Turn 2, tool calls) stays the same.

### `tests/test_tp4_problem_examples.py` → `tests/test_helper_problem_examples.py` (rename + minimal update)
Same renames as above.

### `tests/test_graph.py`
- `_invoke` helper: no changes needed.
- Any test that calls TP1/TP2/TP3/TP5 now routes to `motivator` — assertions stay
  the same (returns `response` with `TextMessage`).
- Any test that calls TP4 / LEARNING now routes to `helper`.
- Add test: `UseCase.CHAT + Touchpoint.TP1 → motivator node fires`.
- Add test: `UseCase.CHAT + Touchpoint.TP4 → helper node fires`.

### `tests/test_chat_api.py`
- No changes needed to test structure; routing changes are transparent to the API.

### DELETE these test files once their replacements pass:
```
tests/test_tp1.py
tests/test_tp2.py
tests/test_tp3.py
tests/test_tp4.py
tests/test_tp4_problem_examples.py
tests/test_tp5.py
```

---

## Implementation order (to avoid broken state mid-refactor)

1. Fix LangGraph `chat_history` accumulation first:
   - Add the `add_messages` reducer to `ChatState.chat_history`.
   - Stop `classify()` from resetting `chat_history`.
   - Add/keep tests proving first-turn input and later turns are preserved.
2. Create `app/services/prompts/agents.py`
3. Create `app/services/nodes/helper.py` (from tp4.py + agents.py)
4. Create `app/services/nodes/motivator.py` (from tp1–tp5 + general_chat + agents.py)
5. Update `app/services/graph.py`
6. Write new tests (`test_motivator_*.py`, `test_helper.py`, `test_helper_problem_examples.py`)
7. Run `uv run pytest tests/` — all tests must pass before proceeding
8. Delete old test files, then old node files (tp1–tp5, general_chat)
9. Run `uv run pytest tests/` again — must still pass

---

## Constraints & rules for the implementing agent

- **Do not change** `app/core/enums.py`, `app/data/`,
  `app/clients/`, `app/api/`, or `app/core/` — only the files listed above.
  Exception: `app/schemas/chat.py` may be changed only to add the `add_messages`
  reducer to `chat_history`.
- **Do not add** `"당신은 스마트올..."` anywhere except inside `MOTIVATOR_ROLE` and
  `HELPER_ROLE` in `agents.py`.
- **Do not duplicate** `get_persona()` or `get_coaching_strategy()` calls —
  always go through `build_system_prompt()`.
- `motivator()` must pass `chat_history` to the LLM so conversation is continuous.
- `helper()` tool-calling logic (Turn 1 / Turn 2 detection via `current_problem`)
  must remain exactly as in the current `tp4.py`.
- All 127 existing tests must pass before the refactor starts.
- After routing is switched, the replacement tests must pass before deleting old files.
- Delete old files only after confirming the replacement test suite is green.
