# Guardrail Middleware — Summary

## Approach

The core problem is that elementary school kids need to be shielded from two directions: what they send in (inappropriate language, jailbreak attempts, off-topic requests) and what the LLM sends back (wrong tone, too complex, too direct). The guardrail sits between the student and the LLM as two explicit steps in every route handler — not as invisible HTTP middleware — so it is easy to add, remove, or inspect per endpoint.

**Input (pre-LLM):** A two-stage `SafetyCheck` runs first. Stage 1 is a fast regex pre-screen with no API call; it catches known profanity and injection patterns immediately. If nothing fires, Stage 2 sends the message to Solar Pro in a single structured call that checks three things at once: content safety, prompt injection, and topic relevance. Any failure blocks the message and returns an age-appropriate Korean refusal to the student.

**Output (post-LLM):** A `ResponseEvaluator` sends the LLM response to Solar Pro in one call checking age-appropriateness, tone, and quality. Failures are logged as warnings — the response is always delivered, because a slightly imperfect answer is better than silence for a stuck child.

Two touchpoint profiles adjust how strictly topic relevance is enforced: **lighthearted** (`home_screen`, `after_all_tasks`, `exit`) allows casual conversation; **study-focused** (`during_study`, `after_task`) requires messages to relate to studying.

---

## Where to change things

| What you want to change | File | What to edit |
|---|---|---|
| Message shown to student when blocked | `app/guardrails/pipeline.py` | `_BLOCKED_MESSAGES` dict — one entry per grade group (`lower`, `middle`, `upper`) |
| Profanity word/pattern list | `app/guardrails/strategies/rule_based.py` | `_PROFANITY_PATTERNS` list |
| Prompt injection patterns | `app/guardrails/strategies/rule_based.py` | `_INJECTION_PATTERNS` list |
| Study keyword heuristic (fast topic check) | `app/guardrails/strategies/rule_based.py` | `_STUDY_KEYWORDS` and `_CLEARLY_OFF_TOPIC` sets |
| What the LLM judges on input (criteria + leniency) | `app/guardrails/guards/input/safety_check.py` | `_LIGHTHEARTED_SYSTEM` and `_STUDY_FOCUSED_SYSTEM` prompt strings |
| What the LLM judges on output (criteria) | `app/guardrails/guards/output/response_evaluator.py` | `_SYSTEM_PROMPT_TEMPLATE` string |
| Which touchpoints are lighthearted vs study-focused | `app/guardrails/models.py` | `GuardrailContext.group` property |
| Add a new guard | `app/guardrails/config.py` | Append to `input_guards` or `output_guards` in `build_pipeline()` |
| Change Solar Pro model used for evaluation | `app/guardrails/strategies/llm_judge.py` | `LLMJudge.__init__` default `model` parameter |
