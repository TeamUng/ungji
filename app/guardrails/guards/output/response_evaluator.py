"""
ResponseEvaluator — the single output guard.

Runs one Solar Pro call that checks three dimensions simultaneously:

  • age_appropriateness — vocabulary and concept complexity match the
                          student's grade group (lower / middle / upper)
  • tone               — encouraging, kind, not discouraging; never gives
                          away direct answers
  • quality            — relevant to the touchpoint; appropriate length;
                          provides a clear next step

Severity: always WARN (per plan).
The LLM response is always delivered to the student; failures are logged
for prompt-improvement monitoring.

Content safety is intentionally NOT checked here — it belongs in SafetyCheck
(input guard) which evaluates the conversation context before the LLM call.

Fail-safe policy
----------------
If the LLM judge call fails, the guard logs a warning and marks the result
as passed=True (WARN).  We never withhold a potentially good response from
a child due to an infrastructure issue.
"""

from __future__ import annotations

import logging

from app.guardrails.guards.base import AbstractOutputGuard
from app.guardrails.models import GuardResult, GuardrailContext, Severity
from app.guardrails.strategies.llm_judge import LLMJudge, LLMJudgeError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM system prompt — single call, three dimensions
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are a response quality evaluator for an AI study coach chatbot serving \
Korean elementary school students.

Context
-------
Touchpoint : {touchpoint}
Grade group: {grade_group} ({grade_range_label})
Student type: {student_type}

Evaluate the chatbot's response on three dimensions and reply with JSON only \
(no markdown, no extra text):

{{
  "age_appropriateness": {{"passed": true, "reason": null}},
  "tone":                {{"passed": true, "reason": null}},
  "quality":             {{"passed": true, "reason": null}}
}}

Definitions
-----------
age_appropriateness:
  PASS if vocabulary, sentence length, and concept complexity are appropriate
  for the grade group.
    lower  (1–2): very short sentences, concrete words, playful tone.
    middle (3–4): slightly longer, some domain vocabulary is fine.
    upper  (5–6): more structured, abstract concepts allowed if explained.
  FAIL if the language is clearly too advanced or too infantile for the group.

tone:
  PASS if the response is encouraging, warm, and supportive.
  FAIL if it is discouraging, cold, condescending, or gives the direct
  answer to a study problem instead of guiding the student.

quality:
  PASS if the response is relevant to the touchpoint below, is not
  excessively long (rough guide: ≤ 200 characters for lower grades,
  ≤ 400 for middle/upper), and ends with a clear next step or question.
  FAIL if it is off-topic, empty, or leaves the student with nothing to do.

Touchpoint guide
----------------
home_screen      : motivational welcome, suggest next study step.
during_study     : diagnose the blockage, guide step-by-step (no direct answers).
after_task       : acknowledge result, motivate to review errors, suggest next task.
after_all_tasks  : celebrate completion, suggest optional extension activities.
exit             : encourage the student to come back and keep studying.

Rules
-----
- Respond with JSON only.
- Use English for reason strings (internal logging, never shown to student).
- Set reason to null when passed is true.
"""


class ResponseEvaluator(AbstractOutputGuard):
    name = "response_evaluator"

    def __init__(self, judge: LLMJudge | None = None) -> None:
        self._judge = judge or LLMJudge()

    async def check(self, text: str, context: GuardrailContext) -> GuardResult:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            touchpoint=context.touchpoint,
            grade_group=context.grade_group,
            grade_range_label=context.grade_range_label,
            student_type=context.student_type or "unknown",
        )

        try:
            verdict = await self._judge.evaluate(system_prompt, text)
        except LLMJudgeError as exc:
            logger.warning(
                "ResponseEvaluator LLM judge failed session=%s error=%s",
                context.session_id, exc,
            )
            return GuardResult(
                passed=True,
                guard_name=self.name,
                severity=Severity.WARN,
                reason="LLM judge unavailable — skipped evaluation",
                metadata={"error": str(exc)},
            )

        failures: list[str] = []
        reasons:  list[str] = []
        for dimension in ("age_appropriateness", "tone", "quality"):
            dim_result = verdict.get(dimension, {})
            if not dim_result.get("passed", True):
                failures.append(dimension)
                if dim_result.get("reason"):
                    reasons.append(f"{dimension}: {dim_result['reason']}")

        if failures:
            logger.warning(
                "ResponseEvaluator WARN session=%s dimensions=%s reasons=%s",
                context.session_id, failures, reasons,
            )
            return GuardResult(
                passed=False,
                guard_name=self.name,
                severity=Severity.WARN,
                reason="; ".join(reasons) or f"Failed: {failures}",
                metadata={"failed_dimensions": failures},
            )

        return GuardResult(
            passed=True,
            guard_name=self.name,
            severity=Severity.LOG,
        )
