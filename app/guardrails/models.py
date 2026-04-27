"""
Core data models for the guardrail system.

Every guard produces a GuardResult. The pipeline aggregates these into
InputCheckResult (pre-LLM) and OutputCheckResult (post-LLM).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    BLOCK    = "block"     # Hard stop — refuse the message, show fallback to student
    SANITIZE = "sanitize"  # Modify text and continue (reserved for future use)
    WARN     = "warn"      # Log the issue; response still reaches the student
    LOG      = "log"       # Silent record only


# ---------------------------------------------------------------------------
# Single guard result
# ---------------------------------------------------------------------------

class GuardResult(BaseModel):
    passed:     bool
    guard_name: str
    severity:   Severity
    reason:     str | None = None
    """English explanation used only for logging — never shown to the student."""
    metadata:   dict       = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Aggregated results
# ---------------------------------------------------------------------------

class InputCheckResult(BaseModel):
    passed:          bool
    guard_results:   list[GuardResult] = Field(default_factory=list)
    blocked_message: str | None        = None
    """Age-appropriate Korean message shown to the student when input is blocked."""


class OutputCheckResult(BaseModel):
    passed:            bool
    guard_results:     list[GuardResult] = Field(default_factory=list)
    fallback_response: str | None        = None
    """Set only if a future BLOCK-severity output guard is added."""

    @property
    def final_text(self) -> str | None:
        return self.fallback_response


# ---------------------------------------------------------------------------
# Request context — passed to every guard unchanged
# ---------------------------------------------------------------------------

TouchpointType = Literal[
    "home_screen",      # Student enters the app home screen
    "during_study",     # Student clicks the coach while studying
    "after_task",       # Student finishes one task (may have errors)
    "after_all_tasks",  # Student finishes the full day's curriculum
    "exit",             # Student clicks the exit button
]

StudentType = Literal[
    "diligent_high",  # 모범 학생 — 성실형       (high achievement, diligent)
    "capable_lazy",   # 모범 학생 — 불성실형      (high achievement, not diligent)
    "diligent_low",   # 성실하지만 성취가 낮은 학생  (low achievement, diligent)
    "disengaged",     # 공부하지 않는 학생          (low achievement, not diligent)
]

TouchpointGroup = Literal["lighthearted", "study_focused"]


class GuardrailContext(BaseModel):
    touchpoint:           TouchpointType
    student_grade:        int            = Field(ge=1, le=6)
    student_type:         StudentType | None = None
    session_id:           str | None     = None
    conversation_history: list[dict]     = Field(default_factory=list)

    @property
    def group(self) -> TouchpointGroup:
        """
        Lighthearted: home_screen, after_all_tasks, exit
        Study-focused: during_study, after_task
        """
        if self.touchpoint in ("home_screen", "after_all_tasks", "exit"):
            return "lighthearted"
        return "study_focused"

    @property
    def grade_group(self) -> Literal["lower", "middle", "upper"]:
        if self.student_grade <= 2:
            return "lower"
        if self.student_grade <= 4:
            return "middle"
        return "upper"

    @property
    def grade_range_label(self) -> str:
        return {"lower": "1~2학년", "middle": "3~4학년", "upper": "5~6학년"}[
            self.grade_group
        ]
