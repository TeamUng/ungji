from enum import Enum


class Segment(str, Enum):
    HIGH_DILIGENT = "잘함+성실"
    HIGH_LAZY = "잘함+불성실"
    LOW_DILIGENT = "못함+성실"
    LOW_LAZY = "못함+불성실"


class GradeGroup(str, Enum):
    LOWER = "lower"    # 1~2학년
    MIDDLE = "middle"  # 3~4학년
    UPPER = "upper"    # 5~6학년


class UseCase(str, Enum):
    TALK = "talk"          # TP1 / TP2 / TP3 / TP5
    LEARNING = "learning"  # TP4


class Touchpoint(str, Enum):
    TP1 = "tp1"  # 홈화면 진입 — 첫 학습 유도
    TP2 = "tp2"  # 단위 학습 완료 — 다음 학습 제안
    TP3 = "tp3"  # 이탈 시도 감지 — 리텐션
    TP4 = "tp4"  # 학습 중 도움 요청 — 막힘 코칭
    TP5 = "tp5"  # 오늘 학습 종료 — 복습 유도


class Subject(str, Enum):
    KOREAN = "국어"
    MATH = "수학"
    SOCIAL = "사회"
    SCIENCE = "과학"
    ENGLISH = "영어"


class Difficulty(str, Enum):
    HIGH = "상"
    MEDIUM = "중"
    LOW = "하"


class WrongCause(str, Enum):
    CONCEPT_LACK = "개념 부족"
    MISTAKE = "실수"
    GUESSING = "찍기"


class MessageType(str, Enum):
    INIT = "init"        # 첫 진입
    TEXT = "text"        # 자유 입력
    CHOICE = "choice"    # 선택지 클릭
