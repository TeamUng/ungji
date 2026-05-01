from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.enums import GradeGroup, Segment, Touchpoint, UseCase
from app.guardrails.agent_output import (
    AgentOutputBlockedError,
    OUTPUT_GUARDRAIL_FALLBACK_MESSAGE,
)
from app.services.nodes.motivator import motivator
from app.services.prompts.personas import get_persona


def _prompt_text(mock_llm) -> str:
    return "\n".join(message.content for message in mock_llm.calls[0]["messages"])


def test_response_shape(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    response = motivator(state)

    types = [message.type for message in response.messages]
    assert "text" in types


def test_system_prompt_uses_lower_persona(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    motivator(state)

    system_content = mock_llm.calls[0]["messages"][0].content
    assert get_persona(GradeGroup.LOWER) in system_content


def test_situation_contains_student_and_task_info(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    motivator(state)

    prompt_text = _prompt_text(mock_llm)
    assert case1_student["profile"]["name"] in prompt_text
    assert case1_student["today_tasks"][0]["unit"] in prompt_text


def test_touchpoint_context_is_sent_as_child_user_message(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    motivator(state)

    messages = mock_llm.calls[0]["messages"]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)
    assert "안녕, 나는" in messages[-1].content
    assert "홈 화면" in messages[-1].content


def test_chat_history_is_passed_to_llm(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    state["chat_history"] = [HumanMessage(content="오늘은 국어부터 할래요")]

    motivator(state)

    contents = [message.content for message in mock_llm.calls[0]["messages"]]
    assert "오늘은 국어부터 할래요" in contents


def test_chat_followup_gets_child_context_with_tasks(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.CHAT,
        touchpoint=Touchpoint.TP1,
    )
    state["chat_history"] = [
        AIMessage(content="국어 - 받침이 있는 낱말 읽기를 추천해."),
        HumanMessage(content="좋아요, 받침이 있는 낱말 읽기부터 해볼게요."),
    ]

    motivator(state)

    context_message = mock_llm.calls[0]["messages"][-1]
    assert isinstance(context_message, HumanMessage)
    assert case1_student["profile"]["name"] in context_message.content
    assert case1_student["today_tasks"][0]["unit"] in context_message.content
    assert "내가 추천한 단원을 해보겠다고 했어" in context_message.content


def test_response_does_not_expose_segment_name(case1_student, make_chat_state, mock_llm):
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )
    response = motivator(state)

    content = response.messages[0].content
    assert "LOW_LAZY" not in content
    assert Segment.LOW_LAZY.value not in content


def test_blocked_user_input_skips_motivator_llm(
    case1_student, make_chat_state, mock_llm, monkeypatch
):
    import app.services.nodes.motivator as motivator_module

    monkeypatch.setattr(
        motivator_module,
        "check_agent_input_sync",
        lambda input_text, state, *, agent_name: "blocked input",
    )
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        use_case=UseCase.CHAT,
        touchpoint=Touchpoint.TP1,
    )
    state["chat_history"] = [HumanMessage(content="unsafe text")]

    response = motivator(state)

    assert response.messages[0].content == "blocked input"
    assert mock_llm.calls == []


def test_empty_tp1_entry_skips_input_guard_and_calls_llm(
    case1_student, make_chat_state, mock_llm, monkeypatch
):
    import app.services.nodes.motivator as motivator_module

    def fail_if_called(*args, **kwargs):
        raise AssertionError("input guard should not run without student input")

    monkeypatch.setattr(motivator_module, "check_agent_input_sync", fail_if_called)
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )

    motivator(state)

    assert mock_llm.calls


def test_output_guard_failure_returns_resting_fallback(
    case1_student,
    make_chat_state,
    mock_llm,
    monkeypatch,
):
    import app.services.nodes.motivator as motivator_module

    def block_output(*args, **kwargs):
        raise AgentOutputBlockedError(
            reasons=["quality: unsafe for child"],
            output_excerpt="unsafe output",
        )

    monkeypatch.setattr(motivator_module, "guarded_invoke", block_output)
    state = make_chat_state(
        case1_student,
        segment=Segment.LOW_LAZY,
        grade_group=GradeGroup.LOWER,
        touchpoint=Touchpoint.TP1,
    )

    response = motivator(state)

    assert response.messages[0].content == OUTPUT_GUARDRAIL_FALLBACK_MESSAGE
