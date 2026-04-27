# Guardrail Middleware

---

## English

### Approach

The core problem is that elementary school kids need to be shielded from two directions: what they send in (inappropriate language, jailbreak attempts, off-topic requests) and what the LLM sends back (wrong tone, too complex, too direct). The guardrail sits between the student and the LLM as two explicit steps in every route handler — not as invisible HTTP middleware — so it is easy to add, remove, or inspect per endpoint.

**Input (pre-LLM):** A two-stage `SafetyCheck` runs first.

- **Stage 1 — Rule-based pre-screen (~0 ms, no API call):** Regex patterns catch known profanity and prompt injection immediately. If nothing fires, a TF-IDF topic classifier checks whether the message resembles known off-topic content (games, YouTube, idols, etc.). The classifier uses character n-gram cosine similarity against 21 curated off-topic example sentences, which generalises over spelling variants and new platform names without needing an explicit keyword list. Messages that contain a study-domain signal alongside an off-topic signal are flagged `unknown` and deferred to the LLM rather than blocked (conflict detection). Short greetings and affirmations (`안녕`, `응`, `hi`) are passed immediately as `on_topic`.

- **Stage 2 — LLM evaluation (one Solar Pro call):** Checks content safety, prompt injection, and topic relevance in a single structured call. `response_format: {"type": "json_object"}` is set on the payload so the model is forced to return valid JSON — no markdown fence stripping needed. Any failure blocks the message and returns an age-appropriate Korean refusal.

**Output (post-LLM):** A `ResponseEvaluator` sends the LLM response to Solar Pro in one call checking age-appropriateness, tone, and quality. Failures are WARN-only — the response is always delivered to the student. When any output dimension fails, the pipeline logs at `ERROR` level with full context (session, touchpoint, grade group, segment, failed dimensions, reasons, response excerpt), which the existing `DiscordWebhookHandler` forwards to the team's Discord channel automatically.

Two touchpoint profiles adjust how strictly topic relevance is enforced: **lighthearted** (`home_screen`, `after_all_tasks`, `exit`) allows casual conversation; **study-focused** (`during_study`, `after_task`) requires messages to relate to studying. `use_case` takes priority over touchpoint when both are present.

Blocked messages are grade-group-aware: lower grades get a friendly emoji-decorated message, upper grades get a plain, respectful one. An unknown or unexpected `grade_group` value falls back to the `middle` message.

The shared `LLMJudge` and guard instances are initialised lazily on the first call to `build_pipeline()` — not at import time — so importing the module never crashes in environments where the Upstage API key is not set (e.g. CI, tests).

---

### Where to change things

| What you want to change | File | What to edit |
|---|---|---|
| Message shown to student when blocked | `app/guardrails/pipeline.py` | `_BLOCKED_MESSAGES` dict — one entry per grade group (`lower`, `middle`, `upper`) |
| Profanity word/pattern list | `app/guardrails/strategies/rule_based.py` | `_PROFANITY_PATTERNS` list |
| Prompt injection patterns | `app/guardrails/strategies/rule_based.py` | `_INJECTION_PATTERNS` list |
| Off-topic classifier examples | `app/guardrails/strategies/rule_based.py` | `_OFF_TOPIC_EXAMPLES` list — add representative sentences for new off-topic categories |
| Off-topic detection threshold | `app/guardrails/strategies/rule_based.py` | `_OFF_TOPIC_THRESHOLD` float (default `0.28`) |
| Study-domain conflict signals | `app/guardrails/strategies/rule_based.py` | `_STUDY_SIGNALS` frozenset |
| What the LLM judges on input (criteria + leniency) | `app/guardrails/guards/safety_check.py` | `_LIGHTHEARTED_SYSTEM` and `_STUDY_FOCUSED_SYSTEM` prompt strings |
| What the LLM judges on output (criteria) | `app/guardrails/guards/response_evaluator.py` | `_SYSTEM_PROMPT_TEMPLATE` string |
| Which touchpoints are lighthearted vs study-focused | `app/guardrails/models.py` | `GuardrailContext.group` property |
| Add a new guard | `app/guardrails/guardrails_config.py` | Append to `input_guards` or `output_guards` inside `build_pipeline()` |
| Solar Pro model used for evaluation | `app/guardrails/strategies/llm_judge.py` | `LLMJudge.__init__` default `model` parameter |
| Discord webhook URL | `.env` | `DISCORD_WEBHOOK_URL` — set to empty string to disable |

---
---

## 한국어

### 접근 방식

핵심 문제는 초등학생이 두 방향에서 보호받아야 한다는 점입니다. 하나는 학생이 보내는 메시지(부적절한 언어, 탈옥 시도, 주제 이탈 요청), 다른 하나는 LLM이 돌려보내는 응답(잘못된 말투, 지나치게 어려운 표현, 답을 직접 알려주는 경우)입니다. 가드레일은 학생과 LLM 사이에서 각 라우트 핸들러 안의 두 명시적 단계로 동작합니다. 보이지 않는 HTTP 미들웨어가 아니기 때문에 엔드포인트별로 추가, 제거, 확인이 쉽습니다.

**입력 단계 (LLM 호출 전):** `SafetyCheck`가 두 단계로 실행됩니다.

- **1단계 — 규칙 기반 사전 검사 (~0 ms, API 호출 없음):** 정규식 패턴으로 알려진 욕설과 프롬프트 인젝션을 즉시 차단합니다. 걸리는 것이 없으면 TF-IDF 주제 분류기가 메시지가 알려진 비주제 콘텐츠(게임, 유튜브, 아이돌 등)와 유사한지 판단합니다. 분류기는 21개의 엄선된 비주제 예문에 대해 문자 n-gram 코사인 유사도를 계산하며, 키워드 목록 없이도 철자 변형과 새로운 플랫폼 명칭을 일반화해 처리합니다. 비주제 신호와 함께 학습 관련 신호가 포함된 메시지는 차단하지 않고 `unknown`으로 분류해 LLM에게 판단을 넘깁니다(충돌 감지). 짧은 인사말과 긍정 표현(`안녕`, `응`, `hi`)은 즉시 `on_topic`으로 통과시킵니다.

- **2단계 — LLM 평가 (Solar Pro 한 번 호출):** 콘텐츠 안전성, 프롬프트 인젝션, 주제 적합성을 단일 구조화 호출로 동시에 검사합니다. 페이로드에 `response_format: {"type": "json_object"}`를 설정해 모델이 항상 유효한 JSON을 반환하도록 강제합니다(마크다운 코드 펜스 제거 불필요). 하나라도 실패하면 메시지를 차단하고 학년에 맞는 한국어 안내 문구를 반환합니다.

**출력 단계 (LLM 호출 후):** `ResponseEvaluator`가 Solar Pro를 한 번 호출해 학년 적합성, 말투, 응답 품질을 검사합니다. 실패 시 WARN으로만 처리하며 응답은 항상 학생에게 전달합니다. 어떤 출력 항목이라도 실패하면 파이프라인이 `ERROR` 레벨로 전체 컨텍스트(세션, 터치포인트, 학년 그룹, 세그먼트, 실패 항목, 사유, 응답 발췌문)를 로깅하며, 기존 `DiscordWebhookHandler`가 이를 팀 Discord 채널로 자동 전달합니다.

주제 적합성 판단 기준은 두 가지 터치포인트 프로파일로 조정합니다. **라이트헤어티드** (`home_screen`, `after_all_tasks`, `exit`)는 가벼운 대화를 허용하고, **스터디 포커스드** (`during_study`, `after_task`)는 학습 관련 메시지만 허용합니다. `use_case`와 터치포인트가 모두 있을 경우 `use_case`가 우선합니다.

차단 메시지는 학년 그룹에 따라 다릅니다. 저학년은 이모지가 포함된 친근한 문구를, 고학년은 이모지 없이 정중한 문구를 받습니다. 알 수 없거나 예상치 못한 `grade_group` 값은 `middle` 메시지로 대체됩니다.

공유 `LLMJudge` 및 가드 인스턴스는 `build_pipeline()` 첫 호출 시 지연 초기화됩니다. 임포트 시점에 초기화하지 않으므로 Upstage API 키가 없는 환경(CI, 테스트 등)에서도 모듈 임포트가 실패하지 않습니다.

---

### 수정 위치 안내

| 변경하고 싶은 항목 | 파일 | 수정 대상 |
|---|---|---|
| 차단 시 학생에게 보이는 메시지 | `app/guardrails/pipeline.py` | `_BLOCKED_MESSAGES` 딕셔너리 — 학년 그룹별 (`lower`, `middle`, `upper`) |
| 욕설·부적절 표현 목록 | `app/guardrails/strategies/rule_based.py` | `_PROFANITY_PATTERNS` 리스트 |
| 프롬프트 인젝션 패턴 | `app/guardrails/strategies/rule_based.py` | `_INJECTION_PATTERNS` 리스트 |
| 비주제 분류기 예문 | `app/guardrails/strategies/rule_based.py` | `_OFF_TOPIC_EXAMPLES` 리스트 — 새로운 비주제 카테고리의 대표 예문 추가 |
| 비주제 감지 임계값 | `app/guardrails/strategies/rule_based.py` | `_OFF_TOPIC_THRESHOLD` 부동소수점 (기본값 `0.28`) |
| 학습 충돌 감지 신호 | `app/guardrails/strategies/rule_based.py` | `_STUDY_SIGNALS` frozenset |
| 입력 LLM 판단 기준 및 허용 범위 | `app/guardrails/guards/safety_check.py` | `_LIGHTHEARTED_SYSTEM`, `_STUDY_FOCUSED_SYSTEM` 프롬프트 문자열 |
| 출력 LLM 판단 기준 | `app/guardrails/guards/response_evaluator.py` | `_SYSTEM_PROMPT_TEMPLATE` 문자열 |
| 터치포인트 프로파일 분류 기준 | `app/guardrails/models.py` | `GuardrailContext.group` 프로퍼티 |
| 새로운 가드 추가 | `app/guardrails/guardrails_config.py` | `build_pipeline()` 안의 `input_guards` 또는 `output_guards` 리스트에 추가 |
| 평가에 사용하는 Solar Pro 모델 변경 | `app/guardrails/strategies/llm_judge.py` | `LLMJudge.__init__`의 기본값 `model` 파라미터 |
| Discord 웹훅 URL | `.env` | `DISCORD_WEBHOOK_URL` — 빈 문자열로 설정하면 비활성화 |