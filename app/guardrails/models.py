"""
Core data models for the guardrail system.

Field alignment with ChatState
-------------------------------
GuardrailContext is populated directly from ChatState fields:

    ChatState field          → GuardrailContext field
    ─────────────────────────────────────────────────
    current_touchpoint[0]    → touchpoint
    use_case[0]              → use_case  ("talk" | "learning")
    grade_group              → grade_group
    segment                  → segment
    thread_id / student_id   → session_id
    chat_history             → conversation_history
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

    @property
    def final_text(self) -> str | None:
        return self.fallback_response


# ---------------------------------------------------------------------------
# Request context — populated from ChatState, passed to every guard unchanged
# ---------------------------------------------------------------------------

TouchpointType = Literal[
    "home_screen",
    "during_study",
    "after_task",
    "after_all_tasks",
    "exit",
]

# Aligned with ChatState.use_case — drives lighthearted vs study_focused
UseCaseType = Literal["talk", "learning"]

# Aligned with ChatState.grade_group
GradeGroup = Literal["lower", "middle", "upper"]

TouchpointGroup = Literal["lighthearted", "study_focused"]


class GuardrailContext(BaseModel):
    # ── Core fields (map directly from ChatState) ─────────────────────────
    touchpoint:  TouchpointType

    use_case:    UseCaseType | None = None
    """
    From ChatState.use_case[0].
    "talk"     → lighthearted profile (home_screen, after_all_tasks, exit)
    "learning" → study_focused profile (during_study, after_task)
    When None, profile is inferred from touchpoint for backwards compatibility.
    """

    grade_group: GradeGroup = "middle"
    """From ChatState.grade_group — 'lower' | 'middle' | 'upper'."""

    segment:     tuple | None = None
    """
    From ChatState.segment.
    tuple[잘함+성실 | 잘함+불성실 | 못함+성실 | 못함+불성실]
    Passed through to guards for future personalisation hooks.
    """

    session_id:            str | None = None
    conversation_history:  list[dict] = Field(default_factory=list)

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def group(self) -> TouchpointGroup:
        """
        Primary source: use_case (aligned with ChatState).
        Fallback: inferred from touchpoint for backwards compatibility.
        """
        if self.use_case == "talk":
            return "lighthearted"
        if self.use_case == "learning":
            return "study_focused"
        # fallback
        if self.touchpoint in ("home_screen", "after_all_tasks", "exit"):
            return "lighthearted"
        return "study_focused"

    @property
    def grade_range_label(self) -> str:
        return {
            "lower":  "1~2학년",
            "middle": "3~4학년",
            "upper":  "5~6학년",
        }[self.grade_group]
