from __future__ import annotations

from typing import Literal, TypedDict

from app.core.enums import Subject, WrongCause


class StudentProfile(TypedDict):
    name: str
    grade: Literal[1, 2, 3, 4, 5, 6]
    preferred_subject: Subject   # 선호 과목 1개
    strong_subject: Subject      # 잘하는 과목 1개
    recent_avg_score: int        # 최근 N일 평균 정답률 (0~100)
    avg_completion_rate: int     # 최근 N일 평균 완료율 (0~100)


class LearningHistory(TypedDict):
    # key: Subject enum 값 (예: "수학"), value: 0~100
    subject_avg_scores: dict[str, int]        # 최근 N일 과목별 평균 점수
    subject_completion_rates: dict[str, int]  # 최근 N일 과목별 평균 완료율


class LearningPattern(TypedDict):
    # 오답 콘텐츠 — None 은 오답 자체가 없음을 의미 (성실도 판별 시 자동 통과)
    wrong_content_rate: int | None  # 최근 N일 오답 콘텐츠 진행률 (0~100, None=오답없음)
    wrong_content_total: int        # 오늘 전체 오답 콘텐츠 수 (0이면 오답 없음)
    wrong_content_done: int         # 오늘 완료한 오답 콘텐츠 수
    # 학습 습관 (최근 N일 기준)
    skipping_habit: bool            # 건너뛰는 습관
    guessing_habit: bool            # 찍는 습관
    careless_habit: bool            # 대충 푸는 습관


class WrongAnswerPattern(TypedDict):
    frequent_wrong_type: str           # 자주 틀리는 유형 (예: "분수 계산")
    repeated_wrong_subjects: list[str] # 반복 오답 과목 (Subject enum 값 목록)
    wrong_cause: WrongCause            # 주요 오답 원인
