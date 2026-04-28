from __future__ import annotations

from typing import Annotated, Literal, TypedDict, Union

from pydantic import BaseModel, Field

from app.core.enums import (
    Difficulty,
    GradeGroup,
    MessageType,
    Segment,
    Touchpoint,
    UseCase,
)
from app.schemas.student import (
    LearningHistory,
    LearningPattern,
    StudentProfile,
    WrongAnswerPattern,
)

# LangGraph가 런타임에 get_type_hints()를 호출하므로 TYPE_CHECKING 블록 밖에서 import
from langchain_core.messages import BaseMessage


# ─── LangGraph State (TypedDict) ─────────────────────────────────────────────

class Task(TypedDict):
    subject: str             # Subject enum 값 (예: "수학")
    unit: str                # 단원명 (예: "비율과 비례식")
    problem_count: int       # 문제 수
    estimated_time: int      # 예상 소요시간 (분)
    difficulty: str          # Difficulty enum 값 ("상" | "중" | "하")
    ai_predicted_score: int  # AI 예상점수 (0~100)


class ChatState(TypedDict):
    # ─── 세션 식별 ───
    thread_id: str    # 프론트에서 UUID 생성, LangGraph InMemorySaver thread 키
    student_id: str   # mock_students.json 조회 키

    # ─── 학생 정보 (세션 시작 시 1회 로드, 이후 불변) ───
    student_profile: StudentProfile
    learning_history: LearningHistory
    learning_pattern: LearningPattern
    wrong_answer_pattern: WrongAnswerPattern

    # ─── 오늘의 학습 상태 ───
    today_tasks: list[Task]         # 오늘 배정된 전체 태스크
    completed_tasks: list[Task]     # 오늘 완료한 태스크
    current_task: Task | None       # 현재 진행 중인 태스크 (TP4 코칭용)
    has_wrong_answers: bool         # 오늘 틀린 문제가 있는지
    wrong_content_done_today: bool  # 오늘 오답 콘텐츠를 진행했는지
    today_score: int                # 오늘의 학습 문항 평균 점수 (0~100)

    # ─── 대화 상태 ───
    use_case: UseCase
    grade_group: GradeGroup
    segment: Segment
    chat_history: list[BaseMessage]  # add_messages reducer로 자동 누적

    # ─── 노드 라우팅용 ───
    current_touchpoint: Touchpoint

    # ─── 노드 출력 ───
    response: ChatResponse | None  # 각 TP 노드가 생성한 최종 응답


# ─── API Request / Response (Pydantic) ───────────────────────────────────────

class IncomingMessage(BaseModel):
    type: MessageType
    content: str = ""


class ChatRequest(BaseModel):
    thread_id: str
    student_id: str
    use_case: UseCase
    current_touchpoint: Touchpoint
    message: IncomingMessage


# Response 메시지 타입 (discriminated union — type 필드로 분기)

class TextMessage(BaseModel):
    type: Literal["text"] = "text"
    content: str


class ChoiceItem(BaseModel):
    id: str
    label: str


class ChoicesMessage(BaseModel):
    type: Literal["choices"] = "choices"
    items: list[ChoiceItem]


class ImageCardMessage(BaseModel):
    type: Literal["image_card"] = "image_card"
    image_url: str
    caption: str


class HintStep(BaseModel):
    step: int
    content: str


class HintCardMessage(BaseModel):
    type: Literal["hint_card"] = "hint_card"
    steps: list[HintStep]


ResponseMessage = Annotated[
    Union[TextMessage, ChoicesMessage, ImageCardMessage, HintCardMessage],
    Field(discriminator="type"),
]


class ChatResponse(BaseModel):
    thread_id: str
    messages: list[ResponseMessage]
