from __future__ import annotations

import pytest

from app.core.enums import GradeGroup, Segment
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona


# ─── 스모크 테스트 ──────────────────────────────────────────────


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


# ─── 뽀롱쌤 인격 통일성 (모든 학년 공통) ──────────────────────────


@pytest.mark.parametrize("grade_group", list(GradeGroup))
def test_persona_shares_brs_identity_across_grades(grade_group):
    persona = get_persona(grade_group)

    # 캐릭터명
    assert "뽀롱쌤" in persona
    # fallback 호칭
    assert "친구야~" in persona
    # 핵심 가치관 4개
    assert "단계로 같이 도달한다" in persona
    assert "평가하지 않는다" in persona
    assert "학생에 맞춰 다가간다" in persona
    assert "격려하고 위로한다" in persona
    # 주요 금기
    assert "정답 키워드 직접 노출" in persona
    assert "내부 분류명 노출" in persona


@pytest.mark.parametrize("grade_group", list(GradeGroup))
def test_persona_includes_brs_signature_phrases(grade_group):
    persona = get_persona(grade_group)

    assert "뽀롱~" in persona
    assert "뽀로롱?!" in persona


# ─── 학년별 톤 차이 ────────────────────────────────────────────


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


# ─── PRD 케이스 방향 검증 ───────────────────────────────────────


def test_case_1_lower_low_lazy_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.LOWER)
    strategy = get_coaching_strategy(Segment.LOW_LAZY)
    combined_prompt = f"{persona}\n{strategy}"

    # 학년 톤 (저학년)
    assert "1~2학년" in persona
    # 인격 (뽀롱쌤 통일)
    assert "뽀롱쌤" in persona
    # 코칭 전략 (PRD 2-5: 즉시 성공 경험 / 짧은 대화 / 작은 목표)
    assert "아주 작은 목표" in strategy
    assert "즉시 성공 경험" in strategy
    assert "절대 길게 설명하지 마" in strategy
    assert "딱 이것만 해보자" in combined_prompt


def test_case_2_upper_low_diligent_prompt_matches_prd_direction():
    persona = get_persona(GradeGroup.UPPER)
    strategy = get_coaching_strategy(Segment.LOW_DILIGENT)
    combined_prompt = f"{persona}\n{strategy}"

    # 학년 톤 (고학년)
    assert "5~6학년" in persona
    assert "해요체" in persona
    # 인격 (뽀롱쌤 통일)
    assert "뽀롱쌤" in persona
    # 코칭 전략 (PRD 2-6: 막힘 원인 진단 / 단계별 / 정답 X / teach-back)
    assert "막힌 원인을 먼저 파악" in strategy
    assert "단계별로 설명" in strategy
    assert "정답을 바로 알려주지 말고" in strategy
    assert "teach-back" in combined_prompt
