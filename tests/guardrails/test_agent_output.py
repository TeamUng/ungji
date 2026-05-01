from __future__ import annotations

import logging
from dataclasses import dataclass

import app.guardrails
from app.guardrails.agent_output import (
    AgentOutputBlockedError,
    check_agent_input_sync,
    guarded_invoke,
)
from app.guardrails.models import GuardResult, InputCheckResult, OutputCheckResult, Severity
from app.core.enums import GradeGroup, Segment, Touchpoint


@dataclass
class FakeResponse:
    content: str


class FakeRunnable:
    def __init__(self):
        self.calls = []
        self.responses = [FakeResponse("bad meta response"), FakeResponse("clean child response")]

    def invoke(self, messages):
        self.calls.append(messages)
        return self.responses.pop(0)


class FakePipeline:
    def __init__(self):
        self.contexts = []
        self.checked_texts = []

    def check_output_sync(self, text, context):
        self.contexts.append(context)
        self.checked_texts.append(text)
        if len(self.checked_texts) == 1:
            return OutputCheckResult(
                passed=False,
                guard_results=[
                    GuardResult(
                        passed=False,
                        guard_name="response_evaluator",
                        severity=Severity.WARN,
                        reason="quality: contains teacher-facing rationale",
                        metadata={"failed_dimensions": ["quality"]},
                    )
                ],
            )
        return OutputCheckResult(passed=True, guard_results=[])


class AlwaysFailOutputPipeline:
    def __init__(self):
        self.checked_texts = []

    def check_output_sync(self, text, context):
        self.checked_texts.append(text)
        return OutputCheckResult(
            passed=False,
            guard_results=[
                GuardResult(
                    passed=False,
                    guard_name="response_evaluator",
                    severity=Severity.WARN,
                    reason="quality: unsafe for child",
                    metadata={"failed_dimensions": ["quality"]},
                )
            ],
        )


class FakeInputPipeline:
    def __init__(self, result: InputCheckResult):
        self.result = result
        self.contexts = []
        self.checked_texts = []

    def check_input_sync(self, text, context):
        self.contexts.append(context)
        self.checked_texts.append(text)
        return self.result


def test_guarded_invoke_regenerates_with_guardrail_reasons(monkeypatch, make_chat_state, case1_student):
    pipeline = FakePipeline()
    monkeypatch.setattr(app.guardrails, "build_pipeline", lambda context: pipeline)
    runnable = FakeRunnable()
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )

    result = guarded_invoke(
        runnable,
        messages=[],
        state=state,
        agent_name="motivator",
        render_output=lambda response: response.content,
    )

    assert result.content == "clean child response"
    assert len(runnable.calls) == 2
    repair_message = runnable.calls[1][-1].content
    assert "guardrail" in repair_message
    assert "quality: contains teacher-facing rationale" in repair_message
    assert pipeline.checked_texts == ["bad meta response", "clean child response"]
    assert pipeline.contexts[0].agent_name == "motivator"
    assert pipeline.contexts[0].touchpoint == "home_screen"


def test_guarded_invoke_blocks_delivery_after_failed_repair(
    monkeypatch,
    make_chat_state,
    case1_student,
    caplog,
):
    pipeline = AlwaysFailOutputPipeline()
    monkeypatch.setattr(app.guardrails, "build_pipeline", lambda context: pipeline)
    runnable = FakeRunnable()
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )

    with caplog.at_level(logging.ERROR, logger="app.guardrails.agent_output"):
        try:
            guarded_invoke(
                runnable,
                messages=[],
                state=state,
                agent_name="motivator",
                render_output=lambda response: response.content,
            )
        except AgentOutputBlockedError as exc:
            error = exc
        else:
            raise AssertionError("guarded_invoke should block final failed output")

    assert error.reasons == ["quality: unsafe for child"]
    assert pipeline.checked_texts == ["bad meta response", "clean child response"]
    assert len(runnable.calls) == 2
    assert any(
        record.levelname == "ERROR"
        and "blocking delivery" in record.getMessage()
        for record in caplog.records
    )


def test_check_agent_input_sync_returns_blocked_message(monkeypatch, make_chat_state, case1_student):
    pipeline = FakeInputPipeline(
        InputCheckResult(
            passed=False,
            blocked_message="blocked",
            guard_results=[
                GuardResult(
                    passed=False,
                    guard_name="safety_check",
                    severity=Severity.BLOCK,
                    reason="unsafe",
                )
            ],
        )
    )
    monkeypatch.setattr(app.guardrails, "build_pipeline", lambda context: pipeline)
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )

    blocked = check_agent_input_sync("unsafe", state, agent_name="motivator")

    assert blocked == "blocked"
    assert pipeline.checked_texts == ["unsafe"]
    assert pipeline.contexts[0].agent_name == "motivator"
