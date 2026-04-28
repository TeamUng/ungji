"""
Guardrail middleware for the ungji study coach chatbot.

Public API
----------
    from app.guardrails import GuardrailContext, build_pipeline

    context = GuardrailContext(touchpoint="home_screen", use_case="talk")
    pipeline = build_pipeline(context)

    input_result = await pipeline.check_input(user_message, context)
    if not input_result.passed:
        return input_result.blocked_message   # age-appropriate Korean refusal

    llm_response = await call_llm(...)

    output_result = await pipeline.check_output(llm_response, context)
    # output always passes through (WARN only) — just use llm_response directly
"""

from app.guardrails.guardrails_config import build_pipeline
from app.guardrails.models import (
    GuardrailContext,
    GuardResult,
    InputCheckResult,
    OutputCheckResult,
    Severity,
)
from app.guardrails.pipeline import GuardrailPipeline

__all__ = [
    "build_pipeline",
    "GuardrailContext",
    "GuardResult",
    "InputCheckResult",
    "OutputCheckResult",
    "Severity",
    "GuardrailPipeline",
]
