"""
Per-touchpoint pipeline factory.

Two profiles (as defined in the plan):

  Lighthearted  → home_screen, after_all_tasks, exit
  Study-focused → during_study, after_task

Both profiles use the same guards but the guards behave differently based
on GuardrailContext.group, so no separate guard instances are needed.

Extending later
---------------
To add a new guard, import it here and append it to the relevant list.
To customise per student-type, pass extra parameters to the guard's __init__
and route them through GuardrailContext.student_type.
"""

from __future__ import annotations

from app.guardrails.guards.input.safety_check import SafetyCheck
from app.guardrails.guards.output.response_evaluator import ResponseEvaluator
from app.guardrails.models import GuardrailContext
from app.guardrails.pipeline import GuardrailPipeline
from app.guardrails.strategies.llm_judge import LLMJudge

# Shared judge instance (one httpx client pool, reused across requests)
_judge = LLMJudge()

# Shared guard instances (stateless — safe to share across requests)
_safety_check       = SafetyCheck(judge=_judge)
_response_evaluator = ResponseEvaluator(judge=_judge)


def build_pipeline(context: GuardrailContext) -> GuardrailPipeline:
    """
    Return the correct GuardrailPipeline for the given context.

    Both touchpoint groups currently use the same pipeline object.
    The guards read `context.group` at call-time to adjust their behaviour
    (e.g. topic-relevance leniency), so a single pipeline handles both.

    If you later need genuinely different guard sets per group, split this
    function into two branches and return different GuardrailPipeline instances.
    """
    return GuardrailPipeline(
        input_guards  = [_safety_check],
        output_guards = [_response_evaluator],
    )
