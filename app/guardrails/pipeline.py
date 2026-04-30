"""
GuardrailPipeline — orchestrates input and output guards for one request.

Usage (inside a route handler)
-------------------------------
    from app.guardrails import build_pipeline, GuardrailContext

    context = GuardrailContext(touchpoint="during_study", use_case="learning", grade_group="middle")
    pipeline = build_pipeline(context)

    input_result = await pipeline.check_input(user_message, context)
    if not input_result.passed:
        return ChatResponse(message=input_result.blocked_message)

    llm_response = await solar_pro.chat(...)

    output_result = await pipeline.check_output(llm_response, context)
    return ChatResponse(message=llm_response)
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.guardrails.models import (
    GuardrailContext,
    InputCheckResult,
    OutputCheckResult,
    Severity,
)

logger = get_logger(__name__)

_BLOCKED_MESSAGES: dict[str, str] = {
    "lower":  "앗! 공부 관련 이야기만 도와줄 수 있어. 다시 물어봐줘! 😊",
    "middle": "이런! 그 내용은 도와드리기 어려워요. 공부에 관한 질문을 해줄래요?",
    "upper":  "죄송하지만 그 내용은 도와드리기 어렵습니다. 공부나 학습 관련 질문이 있으면 언제든지 물어보세요.",
}


class GuardrailPipeline:
    """
    Holds a list of input guards and output guards and runs them in order.

    - Input guards: fail-fast — the first BLOCK stops the chain immediately.
    - Output guards: run all and aggregate — WARN-only at pipeline level.
    - The pipeline is stateless; instantiate once and reuse across requests.
    """

    def __init__(self, input_guards: list, output_guards: list) -> None:
        self._input_guards  = input_guards
        self._output_guards = output_guards

    async def check_input(self, text: str, context: GuardrailContext) -> InputCheckResult:
        """Run input guards in order. Returns on the first BLOCK."""
        results = []
        for guard in self._input_guards:
            result = await guard.check(text, context)
            results.append(result)
            if not result.passed and result.severity == Severity.BLOCK:
                blocked_msg = _BLOCKED_MESSAGES.get(context.grade_group, _BLOCKED_MESSAGES["middle"])
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

    def check_input_sync(self, text: str, context: GuardrailContext) -> InputCheckResult:
        """Synchronous input check for sync LangGraph nodes."""
        results = []
        for guard in self._input_guards:
            if hasattr(guard, "check_sync"):
                result = guard.check_sync(text, context)
            else:
                raise TypeError(f"Guard {guard.name} does not support sync input checks")
            results.append(result)
            if not result.passed and result.severity == Severity.BLOCK:
                blocked_msg = _BLOCKED_MESSAGES.get(context.grade_group, _BLOCKED_MESSAGES["middle"])
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

    async def check_output(self, text: str, context: GuardrailContext) -> OutputCheckResult:
        """Run all output guards. Callers decide whether to repair or deliver."""
        results = []
        for guard in self._output_guards:
            result = await guard.check(text, context)
            results.append(result)
        overall_passed = all(r.passed for r in results)

        if not overall_passed:
            failed = [r for r in results if not r.passed]
            dims    = [d for r in failed for d in r.metadata.get("failed_dimensions", [])]
            reasons = "; ".join(r.reason for r in failed if r.reason)
            logger.warning(
                "Output quality WARN | session=%s touchpoint=%s grade=%s segment=%s"
                " | dims=%s | reasons=%s | response_excerpt=%r",
                context.session_id,
                context.touchpoint,
                context.grade_group,
                context.segment or "unknown",
                dims,
                reasons,
                text[:200],
            )

        return OutputCheckResult(passed=overall_passed, guard_results=results)

    def check_output_sync(self, text: str, context: GuardrailContext) -> OutputCheckResult:
        """Synchronous output check for sync LangGraph nodes."""
        results = []
        for guard in self._output_guards:
            if hasattr(guard, "check_sync"):
                result = guard.check_sync(text, context)
            else:
                raise TypeError(f"Guard {guard.name} does not support sync output checks")
            results.append(result)
        overall_passed = all(r.passed for r in results)

        if not overall_passed:
            failed = [r for r in results if not r.passed]
            dims = [d for r in failed for d in r.metadata.get("failed_dimensions", [])]
            reasons = "; ".join(r.reason for r in failed if r.reason)
            logger.warning(
                "Output quality WARN | session=%s touchpoint=%s grade=%s segment=%s agent=%s"
                " | dims=%s | reasons=%s | response_excerpt=%r",
                context.session_id,
                context.touchpoint,
                context.grade_group,
                context.segment or "unknown",
                context.agent_name or "unknown",
                dims,
                reasons,
                text[:200],
            )

        return OutputCheckResult(passed=overall_passed, guard_results=results)
