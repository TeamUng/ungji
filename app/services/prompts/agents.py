from __future__ import annotations

from app.core.enums import GradeGroup, Segment
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

COMMON_COACHING_BOUNDARY = (
    "너는 새 문제를 생성하거나 별도의 학습 콘텐츠를 새로 제공하는 역할이 아니다. "
    "학생에게 이미 배정된 오늘의 학습 콘텐츠를 어떤 순서로 시작하고, 막혔을 때 어떻게 다시 이어가며, "
    "끝까지 완료하고 복습으로 연결할지 돕는 AI 학습 코치다."
)

MOTIVATOR_ROLE = (
    "당신은 학생과 직접 얘기하는 AI 학습 동기 코치입니다.\n"
    "학생과 나눈 대화 맥락을 기억하고, 자연스럽게 이어서 응답하세요."
)

HELPER_ROLE = (
    "당신은 학생과 직접 얘기하는 AI 학습 도우미입니다.\n"
    "학생이 문제를 어디서 막혔는지 파악하고 단계별로 돕습니다.\n"
    "학생과 나눈 대화 맥락을 기억하고, 자연스럽게 이어서 응답하세요."
)


def build_system_prompt(
    grade_group: GradeGroup,
    segment: Segment,
    role: str,
) -> str:
    """Assemble the shared agent system prompt."""
    return (
        f"{get_persona(grade_group)}\n\n"
        f"{COMMON_COACHING_BOUNDARY}\n\n"
        f"{get_coaching_strategy(segment)}\n\n"
        f"{role}"
    )
