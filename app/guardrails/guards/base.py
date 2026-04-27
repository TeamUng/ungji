"""
Abstract base classes for input and output guards.

Every guard is a small, focused unit that receives a text string plus the
full GuardrailContext and returns a GuardResult.  The pipeline composes
multiple guards and aggregates their results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.guardrails.models import GuardrailContext, GuardResult


class AbstractInputGuard(ABC):
    """Checks student input before it reaches the LLM."""

    name: str  # Used in logging and GuardResult.guard_name

    @abstractmethod
    async def check(self, text: str, context: GuardrailContext) -> GuardResult:
        ...


class AbstractOutputGuard(ABC):
    """Checks the LLM response before it is returned to the student."""

    name: str

    @abstractmethod
    async def check(self, text: str, context: GuardrailContext) -> GuardResult:
        ...
