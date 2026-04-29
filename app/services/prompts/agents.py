from __future__ import annotations

from app.core.enums import GradeGroup, Segment
from app.services.prompts.coaching import get_coaching_strategy
from app.services.prompts.personas import get_persona

MOTIVATOR_ROLE = (
    "당신은 스마트올 AI 학습 동기 코치입니다.\n"
    "학생이 홈화면에 진입하거나, 과제를 완료하거나, 이탈하려 하거나, "
    "학습을 마무리할 때 함께합니다.\n"
    "학생과 나눈 대화 맥락을 기억하고, 자연스럽게 이어서 응답하세요.\n"
    "응답은 항상 간결하게 2~4문장으로 작성하고, 강요하지 않으며 학생에게 선택권을 주세요."
)

HELPER_ROLE = (
    "당신은 스마트올 AI 학습 도우미입니다.\n"
    "학생이 문제를 어디서 막혔는지 파악하고 단계별로 돕습니다.\n"
    "정답을 바로 알려주지 말고, 학생이 스스로 깨달을 수 있도록 유도하세요.\n"
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
        f"{get_coaching_strategy(segment)}\n\n"
        f"{role}"
    )
