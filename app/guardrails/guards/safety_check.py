"""SafetyCheck — the single input guard.

Input checks are intentionally rule-only for latency. Profanity and prompt
injection patterns block immediately; ordinary kid messages pass to the coach,
which redirects harmless off-topic content back to study.
"""

from __future__ import annotations

import logging

from app.guardrails.models import GuardResult, GuardrailContext, Severity
from app.guardrails.strategies import rule_based as rb

logger = logging.getLogger(__name__)


class SafetyCheck:
    name = "safety_check"

    def __init__(self, judge=None) -> None:
        # Kept for backwards-compatible tests/pipeline construction. Input
        # safety no longer calls an LLM judge on the hot path.
        self._judge = judge

    async def check(self, text: str, context: GuardrailContext) -> GuardResult:
        return self._check_rules(text, context)

    def check_sync(self, text: str, context: GuardrailContext) -> GuardResult:
        """Synchronous variant for LangGraph sync nodes."""
        return self._check_rules(text, context)

    def _check_rules(self, text: str, context: GuardrailContext) -> GuardResult:
        found, token = rb.has_profanity(text)
        if found:
            logger.info("SafetyCheck BLOCK (profanity) session=%s", context.session_id)
            return GuardResult(
                passed=False, guard_name=self.name, severity=Severity.BLOCK,
                reason=f"Profanity: {token!r}", metadata={"stage": "rule", "match": token},
            )

        found, snippet = rb.has_prompt_injection(text)
        if found:
            logger.info("SafetyCheck BLOCK (injection) session=%s", context.session_id)
            return GuardResult(
                passed=False, guard_name=self.name, severity=Severity.BLOCK,
                reason=f"Injection pattern: {snippet!r}", metadata={"stage": "rule", "match": snippet},
            )

        return GuardResult(
            passed=True, guard_name=self.name, severity=Severity.LOG,
            metadata={"stage": "rule"},
        )
