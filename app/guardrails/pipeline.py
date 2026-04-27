"""
GuardrailPipeline — orchestrates input and output guards for one request.

Usage (inside a route handler)
-------------------------------
    from app.guardrails import build_pipeline, GuardrailContext

    context = GuardrailContext(touchpoint="during_study", student_grade=4)
    pipeline = build_pipeline(context)

    # Before LLM call
    input_result = await pipeline.check_input(user_message, context)
    if not input_result.passed:
        return ChatResponse(message=input_result.blocked_message)

    llm_response = await solar_pro.chat(...)

    # After LLM call
    output_result = await pipeline.check_output(llm_response, context)
    # output always passes through (WARN only) — use output_result.final_text
    # if you ever need the sanitised version in the future.

    return ChatResponse(message=llm_response)
"""

from __future__ import annotations

import logging

from app.guardrails.guards.base import AbstractInputGuard, AbstractOutputGuard
from app.guardrails.models import (
    GuardrailContext,
    InputCheckResult,
    OutputCheckResult,
    Severity,
)

logger = logging.getLogger(__name__)

# Age-appropriate blocked messages — indexed by grade_group
_BLOCKED_MESSAGES: dict[str, str] = {
    "lower":  "앗! 공부 관련 이야기만 도와줄 수 있어. 다시 물어봐줘! 😊",
    "middle": "이런! 그 내용은 도와드리기 어려워요. 공부에 관한 질문을 해줄래요?",
    "upper":  "죄송하지만 그 내용은 도와드리기 어렵습니다. 공부나 학습 관련 질문이 있으면 언제든지 물어보세요.",
}


class GuardrailPipeline:
    """
    Holds a list of input guards and output guards and runs them in order.

    Design decisions
    ----------------
    - Input guards: fail-fast — the first BLOCK stops the chain immediately.
    - Output guards: run all and aggregate — all are WARN-only so we always
      deliver the response; failures are logged for monitoring.
    - The pipeline is stateless across requests; instantiate once and reuse.
    """

    def __init__(
        self,
        input_guards:  list[AbstractInputGuard],
        output_guards: list[AbstractOutputGuard],
    ) -> None:
        self._input_guards  = input_guards
        self._output_guards = output_guards

    # ------------------------------------------------------------------
    # Input check (pre-LLM)
    # ------------------------------------------------------------------

    async def check_input(
        self, text: str, context: GuardrailContext
    ) -> InputCheckResult:
        """
        Run input guards in order.  Returns on the first BLOCK.
        WARN-severity results are collected but do not stop processing.
        """
        results = []

        for guard in self._input_guards:
            result = await guard.check(text, context)
            results.append(result)

            if not result.passed and result.severity == Severity.BLOCK:
                blocked_msg = _BLOCKED_MESSAGES[context.grade_group]
                logger.info(
                    "Input BLOCKED guard=%s session=%s reason=%s",
                    guard.name, context.session_id, result.reason,
                )
                return InputCheckResult(
                    passed=False,
                    guard_results=results,
                    blocked_message=blocked_msg,
                )

        return InputCheckResult(passed=True, guard_results=results)

    # ------------------------------------------------------------------
    # Output check (post-LLM)
    # ------------------------------------------------------------------

    async def check_output(
        self, text: str, context: GuardrailContext
    ) -> OutputCheckResult:
        """
        Run all output guards and aggregate.
        All current output guards are WARN-only — the response is always
        returned to the student.  Failures are logged for monitoring.
        """
        results = []

        for guard in self._output_guards:
            result = await guard.check(text, context)
            results.append(result)

        overall_passed = all(r.passed for r in results)
        return OutputCheckResult(passed=overall_passed, guard_results=results)
