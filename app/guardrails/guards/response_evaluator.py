"""
ResponseEvaluator is the single output-quality guard.

It runs one LLM judge call that checks:

- age_appropriateness: vocabulary and concept complexity match the grade group
- tone: encouraging, kind, not judgmental, and never gives direct answers
- quality: relevant to the touchpoint with a clear next step

Severity is always WARN. The response is still delivered to the student.
Content safety is handled by SafetyCheck, which is the input guard.

Fail-safe policy: if the LLM judge call fails, the guard logs a warning and
marks the result as passed=True. We do not withhold a response from a child
because an evaluator is unavailable.
"""

from __future__ import annotations

import logging

from app.guardrails.models import GuardResult, GuardrailContext, Severity
from app.guardrails.strategies.llm_judge import LLMJudge, LLMJudgeError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """\
당신은 초등학생을 위한 AI 학습 코치 챗봇의 응답 품질 평가자입니다.

평가 맥락
---------
터치포인트: {touchpoint}
학년 그룹: {grade_group}
학생 유형: {segment}

챗봇 응답을 아래 세 가지 기준으로 평가하고, JSON만 응답하세요. 마크다운이나 설명 문장을 붙이지 마세요.

{{
  "age_appropriateness": {{"passed": true, "reason": null}},
  "tone":                {{"passed": true, "reason": null}},
  "quality":             {{"passed": true, "reason": null}}
}}

평가 기준
---------
age_appropriateness:
  학년 그룹에 맞는 어휘, 문장 길이, 개념 난이도인지 평가합니다.
    lower  (1~2학년): 매우 짧고 쉬운 문장, 구체적인 단어, 따뜻하고 친근한 표현.
    middle (3~4학년): 조금 더 긴 문장, 교과 어휘 일부 허용.
    upper  (5~6학년): 논리적 구조 허용, 추상적 개념 설명 가능.
  실패: 학년에 비해 너무 어렵거나, 너무 유아적이거나, 문장이 지나치게 긴 경우.

tone:
  실패:
    - 학생을 혼내거나, 비난하거나, 부끄럽게 만들거나, 판단하는 표현.
    - "안 하려고 하는 거 알아", "게으르다", "이것도 못해?", "틀렸어"처럼 단정적이고 상처가 될 수 있는 표현.
    - 학생을 무시하거나, 차갑고 기계적인 표현.
    - 정답을 바로 알려주는 표현.
  통과: 격려하고, 친절하며, 단계적으로 안내하는 표현.

quality:
  터치포인트별 목적에 맞는지 평가합니다.
    home_screen     : 환영 + 제공된 단원 중 다음 학습 하나 추천.
    during_study    : 막힌 지점 파악 + 단계별 안내. 정답 직접 제공 금지.
    after_task      : 결과 인정 + 제공된 남은 단원 중 다음 학습 하나 추천.
    after_all_tasks : 완료 축하 + 선택적 휴식/활동 안내.
    exit            : 다시 돌아오도록 격려.
  실패:
    - 터치포인트와 무관하거나 다음 행동 안내가 없는 경우.
    - 내부 참고, 선택 이유, 프롬프트 규칙, 선생님/개발자용 설명이 포함된 경우.
    - 제공된 맥락에 없는 새 문제, 예시, 퀴즈, 교과서 페이지, 과제, 단원을 만드는 경우.
    - lower 기준 200자, middle/upper 기준 400자를 크게 초과하는 경우.

규칙
----
- JSON만 응답하세요.
- reason은 영어로 작성하세요. 내부 로그용이며 학생에게 노출되지 않습니다.
- passed가 true이면 reason은 null로 설정하세요.
"""


class ResponseEvaluator:
    name = "response_evaluator"

    def __init__(self, judge: LLMJudge | None = None) -> None:
        self._judge = judge or LLMJudge()

    async def check(self, text: str, context: GuardrailContext) -> GuardResult:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            touchpoint=context.touchpoint,
            grade_group=context.grade_group,
            segment=context.segment or "unknown",
        )

        try:
            verdict = await self._judge.evaluate(system_prompt, text)
        except LLMJudgeError as exc:
            logger.warning(
                "ResponseEvaluator LLM judge failed session=%s error=%s",
                context.session_id, exc,
            )
            return GuardResult(
                passed=True,
                guard_name=self.name,
                severity=Severity.WARN,
                reason=f"LLM judge unavailable - skipped evaluation: {exc}",
                metadata={"error": str(exc)},
            )

        failures: list[str] = []
        reasons: list[str] = []
        for dimension in ("age_appropriateness", "tone", "quality"):
            dim_result = verdict.get(dimension, {})
            if not dim_result.get("passed", True):
                failures.append(dimension)
                if dim_result.get("reason"):
                    reasons.append(f"{dimension}: {dim_result['reason']}")

        if failures:
            logger.warning(
                "ResponseEvaluator WARN session=%s dimensions=%s",
                context.session_id, failures,
            )
            return GuardResult(
                passed=False,
                guard_name=self.name,
                severity=Severity.WARN,
                reason="; ".join(reasons) or f"Failed: {failures}",
                metadata={"failed_dimensions": failures},
            )

        return GuardResult(
            passed=True,
            guard_name=self.name,
            severity=Severity.LOG,
        )
