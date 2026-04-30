from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment
from app.services.prompts.agents import (
    COMMON_COACHING_BOUNDARY,
    GLOBAL_OUTPUT_CONTRACT,
    MOTIVATOR_ROLE,
    build_system_prompt,
)
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


@pytest.mark.parametrize("grade_group", list(GradeGroup))
def test_persona_shares_brs_identity_across_grades(grade_group):
    persona = get_persona(grade_group)

    assert "뽀롱쌤" in persona
    assert "친구야~" in persona
    assert "단계로 같이 도달한다" in persona
    assert "평가하지 않는다" in persona
    assert "학생에 맞춰 다가간다" in persona
    assert "격려하고 위로한다" in persona
    assert "정답 키워드 직접 노출" in persona
    assert "내부 분류명 노출" in persona


@pytest.mark.parametrize("grade_group", list(GradeGroup))
def test_persona_includes_brs_signature_phrases(grade_group):
    persona = get_persona(grade_group)

    assert "뽀롱~" in persona
    assert "뽀로롱?!" in persona


def test_lower_persona_uses_lower_tone_guide():
    persona = get_persona(GradeGroup.LOWER)

    assert "1~2학년" in persona
    assert "60자 이하" in persona
    assert "쉬운 우리말" in persona


def test_middle_persona_uses_middle_tone_guide():
    persona = get_persona(GradeGroup.MIDDLE)

    assert "3~4학년" in persona
    assert "80자 이하" in persona


def test_upper_persona_uses_upper_tone_guide():
    persona = get_persona(GradeGroup.UPPER)

    assert "5~6학년" in persona
    assert "60~150자" in persona
    assert "해요체" in persona


def test_grade_tones_differ_by_group():
    lower = get_persona(GradeGroup.LOWER)
    middle = get_persona(GradeGroup.MIDDLE)
    upper = get_persona(GradeGroup.UPPER)

    assert lower != middle
    assert middle != upper
    assert lower != upper


def test_build_system_prompt_combines_persona_strategy_and_role():
    prompt = build_system_prompt(GradeGroup.LOWER, Segment.LOW_LAZY, MOTIVATOR_ROLE)

    assert get_persona(GradeGroup.LOWER) in prompt
    assert COMMON_COACHING_BOUNDARY in prompt
    assert GLOBAL_OUTPUT_CONTRACT in prompt
    assert get_coaching_strategy(Segment.LOW_LAZY) in prompt
    assert MOTIVATOR_ROLE in prompt


def test_global_output_contract_blocks_invented_study_content():
    prompt = build_system_prompt(GradeGroup.LOWER, Segment.LOW_LAZY, MOTIVATOR_ROLE)

    assert "새로운 문제" in prompt
    assert "연습문제" in prompt
    assert "예시" in prompt
    assert "교과서 페이지" in prompt
    assert "퀴즈" in prompt
    assert "과제" in prompt
    assert "제공된 today_tasks/current_task/current_problem" in prompt
    assert "선택 이유" in prompt
    assert "도구 이름" in prompt


def test_common_boundary_redirects_harmless_off_topic_interests():
    prompt = build_system_prompt(GradeGroup.MIDDLE, Segment.HIGH_LAZY, MOTIVATOR_ROLE)

    assert "공부 범위 대화 원칙" in prompt
    assert "유튜브, 게임, 아이돌" in prompt
    assert "공부 밖 주제로 깊게 대화하거나 추천, 공략, 정보 제공을 하지 않는다" in prompt
    assert "차단하거나 혼내지 말고" in prompt


def test_low_lazy_strategy_contains_choice_policy_in_korean_strategy_only():
    strategy = get_coaching_strategy(Segment.LOW_LAZY)

    assert "여러 선택지를 주지 말고" in strategy
    assert "하나의 분명한 추천이나 행동" in strategy
    assert "TP4" in strategy
    assert "CHOICE POLICY" not in strategy


def test_case_1_lower_low_lazy_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.LOWER)
    strategy = get_coaching_strategy(Segment.LOW_LAZY)
    combined_prompt = f"{persona}\n{strategy}"

    assert "1~2학년" in persona
    assert "뽀롱쌤" in persona
    assert "한 번에 하나의 행동만" in strategy
    assert "아주 작은 목표" in strategy
    assert "즉시 성공 경험" in strategy
    assert "긴 설명" in strategy and "피하고" in strategy
    assert "이건 금방 끝낼 수 있어" in combined_prompt


def test_case_2_upper_low_diligent_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.UPPER)
    strategy = get_coaching_strategy(Segment.LOW_DILIGENT)
    combined_prompt = f"{persona}\n{strategy}"

    assert "5~6학년" in persona
    assert "해요체" in persona
    assert "뽀롱쌤" in persona
    assert "어디가 어려운지 짚어내게" in strategy
    assert "막힌 원인을 먼저 파악" in strategy
    assert "단계별로" in strategy
    assert "단계별로 설명" in strategy
    assert "정답을 바로 말하지 말고" in strategy
    assert "정답을 바로 알려주지 말고" in strategy
    assert "자기 말로 다시 설명" in combined_prompt
    assert "teach-back" in combined_prompt
