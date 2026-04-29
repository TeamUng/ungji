from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment
from app.services.prompts.agents import MOTIVATOR_ROLE, build_system_prompt
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona


@pytest.mark.parametrize("grade_group", list(GradeGroup))
def test_get_persona_returns_prompt_for_every_grade_group(grade_group):
    persona = get_persona(grade_group)

    assert isinstance(persona, str)
    assert persona.strip()


@pytest.mark.parametrize("segment", list(Segment))
def test_get_coaching_strategy_returns_prompt_for_every_segment(segment):
    strategy = get_coaching_strategy(segment)

    assert isinstance(strategy, str)
    assert strategy.strip()


def test_build_system_prompt_combines_persona_strategy_and_role():
    prompt = build_system_prompt(GradeGroup.LOWER, Segment.LOW_LAZY, MOTIVATOR_ROLE)

    assert get_persona(GradeGroup.LOWER) in prompt
    assert get_coaching_strategy(Segment.LOW_LAZY) in prompt
    assert MOTIVATOR_ROLE in prompt


def test_case_1_lower_low_lazy_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.LOWER)
    strategy = get_coaching_strategy(Segment.LOW_LAZY)
    combined_prompt = f"{persona}\n{strategy}"

    assert "1~2학년" in persona
    assert "짧고 쉬운 단어" in persona
    assert "한 번에 한 가지만" in persona
    assert "아주 작은 목표" in strategy
    assert "즉시 성공 경험" in strategy
    assert "절대 길게 설명하지 마" in strategy
    assert "딱 이것만 해보자" in combined_prompt


def test_case_2_upper_low_diligent_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.UPPER)
    strategy = get_coaching_strategy(Segment.LOW_DILIGENT)
    combined_prompt = f"{persona}\n{strategy}"

    assert "5~6학년" in persona
    assert "차분하고 논리적인 코치" in persona
    assert "해요체" in persona
    assert "막힌 원인을 먼저 파악" in strategy
    assert "단계별로 설명" in strategy
    assert "정답을 바로 알려주지 말고" in strategy
    assert "teach-back" in combined_prompt
