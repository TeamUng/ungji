# Worklog — feature/T4-classify-node

## 작업 배경

T9 그래프 조립 전에 모든 요청의 진입점이 되는 classify 노드가 필요하다.
LangGraph 그래프는 classify 노드를 통해 학생 데이터를 로드하고, 세그먼트와 학년 그룹을 판별한 뒤 ChatState를 초기화한다.
이 값을 기반으로 TP1~TP5 노드가 세그먼트별 응답을 분기하기 때문에, classify가 올바르게 동작해야 전체 흐름이 성립한다.

## 왜 필요한가

- 케이스 1 (1학년 국어, 못함+불성실)과 케이스 2 (5학년 수학, 못함+성실)는 세그먼트와 학년 그룹에 따라 완전히 다른 응답 흐름을 탄다.
- constants.py에 정의된 임계값(HIGH_ACHIEVER_SCORE_THRESHOLD, DILIGENT_COMPLETION_RATE_THRESHOLD, DILIGENT_WRONG_CONTENT_THRESHOLD)을 일관되게 적용해야 하며, 이를 하나의 노드에서 처리해야 팀 전체가 같은 기준을 공유한다.
- wrong_content_rate=None(오답 자체가 없는 경우)을 불성실로 오판하지 않도록 명시적으로 처리해야 한다.

## 구현 방법

- `get_grade_group(grade)`: constants.py 경계값 기준으로 LOWER/MIDDLE/UPPER 반환
- `get_segment(profile, learning_pattern)`: 점수와 완료율·오답률 기준으로 4개 세그먼트 중 하나 반환
  - wrong_content_rate가 None이면 성실도 2차 조건 자동 통과
- `classify(state)`: load_student()로 목업 데이터 로드 → 위 두 함수로 판별 → ChatState 업데이트 dict 반환
- 테스트는 load_student를 mock으로 주입해 파일 I/O 없이 순수 로직만 검증

## 변경 내용

- `app/services/nodes/__init__.py` 신규 (패키지 초기화)
- `app/services/nodes/classify.py` 신규
  - `get_grade_group()`: 학년 → GradeGroup 변환
  - `get_segment()`: StudentProfile + LearningPattern → Segment 판별
  - `classify()`: LangGraph 노드 함수 (ChatState → dict)
- `tests/test_classify.py` 신규 (18개 테스트)
  - 케이스 1·2 세그먼트 검증
  - 잘함+성실, 잘함+불성실 세그먼트 검증
  - wrong_content_rate=None 성실도 불이익 없음 검증
  - 학년 1~6 전체 경계값 parametrize 검증
  - classify 노드 mock 기반 통합 검증 4종
- `TODO.md` T4 체크리스트 완료 반영

## 주요 변경 파일

- `app/services/nodes/__init__.py`
- `app/services/nodes/classify.py`
- `tests/test_classify.py`
- `TODO.md`

## 확인

- `uv run pytest tests/test_classify.py` — 18개 통과
- `uv run pytest` (guardrails 제외) — 42개 전체 통과

## PR 참고

- PR 대상: `dev`
- T8 conftest fixture(case1_student, case2_student, high_diligent_student, high_lazy_student)를 그대로 활용해 테스트를 작성했다.
- load_student는 mock으로 대체했으므로 mock_students.json 데이터 없이도 테스트가 통과한다.

## 다음 작업

- T9: classify 노드를 StateGraph entry로 등록하고 TP 노드들과 라우팅 연결
