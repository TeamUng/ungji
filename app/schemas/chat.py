from __future__ import annotations

from typing import Annotated, Literal, TypedDict, Union

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.core.enums import (
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


class Task(TypedDict):
    """A home-screen curriculum unit, optionally linked to TP4 mock problems."""

    subject: str
    unit: str
    problem_count: int
    estimated_time: int
    difficulty: str
    ai_predicted_score: int
    problem_ids: list[str]
    problem_id: str | None


class ChatState(TypedDict):
    # Session identity
    thread_id: str
    student_id: str

    # Student data loaded once by the graph
    student_profile: StudentProfile
    learning_history: LearningHistory
    learning_pattern: LearningPattern
    wrong_answer_pattern: WrongAnswerPattern

    # Today's learning state
    today_tasks: list[Task]
    completed_tasks: list[Task]
    current_task: Task | None
    current_problem: dict | None
    tp4_phase: str
    tp4_turn_count: int
    has_wrong_answers: bool
    wrong_content_done_today: bool
    today_score: int

    # Routing and memory
    use_case: UseCase
    grade_group: GradeGroup
    segment: Segment
    chat_history: Annotated[list[BaseMessage], add_messages]
    current_touchpoint: Touchpoint

    # Node output
    response: ChatResponse | None


class IncomingMessage(BaseModel):
    type: MessageType
    content: str = ""


class ChatRequest(BaseModel):
    thread_id: str
    student_id: str
    use_case: UseCase
    current_touchpoint: Touchpoint
    message: IncomingMessage


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
