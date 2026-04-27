# ─── 기간 설정 ───────────────────────────────────────────────────────────────
# 평균값 산정에 사용하는 기준 기간 (일)
RECENT_PERIOD_DAYS: int = 7

# ─── 학년 그룹 경계 ──────────────────────────────────────────────────────────
# grade <= LOWER_GRADE_MAX  → GradeGroup.LOWER  (1~2학년)
# grade <= MIDDLE_GRADE_MAX → GradeGroup.MIDDLE (3~4학년)
# 그 외                     → GradeGroup.UPPER  (5~6학년)
LOWER_GRADE_MAX: int = 2
MIDDLE_GRADE_MAX: int = 4

# ─── 세그먼트 판별 임계값 ────────────────────────────────────────────────────
# 최근_평균정답률 >= HIGH_ACHIEVER_SCORE_THRESHOLD → 잘함
HIGH_ACHIEVER_SCORE_THRESHOLD: int = 90

# 평균완료율 >= DILIGENT_COMPLETION_RATE_THRESHOLD → 성실 1차 조건
DILIGENT_COMPLETION_RATE_THRESHOLD: int = 70

# 오답_콘텐츠_진행률 >= DILIGENT_WRONG_CONTENT_THRESHOLD → 성실 2차 조건
# (오답이 없어 None인 경우 이 조건은 자동 통과)
DILIGENT_WRONG_CONTENT_THRESHOLD: int = 50

# ─── 점수 / 비율 범위 ────────────────────────────────────────────────────────
SCORE_MIN: int = 0
SCORE_MAX: int = 100
RATE_MIN: int = 0
RATE_MAX: int = 100
