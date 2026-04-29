"""
Core data models for the guardrail system.

GuardrailContext maps directly from ChatState:
  current_touchpoint → touchpoint
  use_case           → use_case
  grade_group        → grade_group
  segment            → segment
  thread_id          → session_id
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    BLOCK    = "block"
    SANITIZE = "sanitize"
    WARN     = "warn"
    LOG      = "log"


class GuardResult(BaseModel):
    passed:     bool
    guard_name: str
    severity:   Severity
    reason:     str | None = None
    metadata:   dict       = Field(default_factory=dict)


class InputCheckResult(BaseModel):
    passed:          bool
    guard_results:   list[GuardResult] = Field(default_factory=list)
    blocked_message: str | None        = None


class OutputCheckResult(BaseModel):
    passed:            bool
    guard_results:     list[GuardResult] = Field(default_factory=list)
    fallback_response: str | None        = None

    @property
    def final_text(self) -> str | None:
        return self.fallback_response

    @property
    def reasons(self) -> list[str]:
        return [result.reason for result in self.guard_results if result.reason]


TouchpointType = Literal["home_screen", "during_study", "after_task", "after_all_tasks", "exit"]
UseCaseType    = Literal["talk", "learning"]
GradeGroup     = Literal["lower", "middle", "upper"]
TouchpointGroup = Literal["lighthearted", "study_focused"]


class GuardrailContext(BaseModel):
    touchpoint:  TouchpointType

    use_case:    UseCaseType | None = None
    grade_group: GradeGroup = "middle"
    segment:     str | None = None
    session_id:  str | None = None
    agent_name:  str | None = None
    conversation_history: list[dict] = Field(default_factory=list)

    @property
    def group(self) -> TouchpointGroup:
        if self.use_case == "talk":
            return "lighthearted"
        if self.use_case == "learning":
            return "study_focused"
        if self.touchpoint in ("home_screen", "after_all_tasks", "exit"):
            return "lighthearted"
        return "study_focused"
