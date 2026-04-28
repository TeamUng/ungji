# 2026-04-28 feature/T12-tp4-dynamic-coaching

## 작업 배경

TP4는 학습 중 학생이 막혔을 때 도움을 주는 핵심 노드입니다.
기존 구현은 막힘 원인 선택지와 일부 힌트 스텝이 고정되어 있어, 실제 문제와 해설지에 따라 달라져야 하는 코칭을 충분히 실험하기 어려웠습니다.

이번 작업에서는 해설지가 제공된다는 가정하에, TP4가 문제·정답·해설·학생 학년·학생 세그먼트·학생이 선택한 막힘 원인을 함께 보고 선택지와 힌트 스텝을 생성할 수 있도록 고도화했습니다.

## 구현 내용

- GitHub Issue #19 생성
- `TODO.md`에 T12 작업 추가 및 완료 항목 업데이트
- `app/data/mock_problems.json`에 소금물 비율 문제 예제 추가
- `app/schemas/chat.py`의 `Task`에 `problem_id` 필드 추가
- `app/services/nodes/tp4.py`에서 `current_task.problem_id` 기반 문제 데이터 로드
- 문제 데이터가 있을 때 TP4 첫 진입 선택지를 LLM JSON 응답으로 생성
- 학생이 선택한 원인 ID가 들어오면 문제/해설 기반 `TextMessage`와 `HintCardMessage` 생성
- LLM JSON 응답이 깨질 경우 사용할 fallback 선택지와 힌트 스텝 추가
- PR #20의 의도였던 `build_expression` 하드코딩 힌트 제거를 흡수해, 문제 ID가 없는 기존 경로에서도 태스크 맥락 기반 LLM 힌트 생성과 fallback을 사용하도록 보강
- 고학년 수학 + 저성취 성실 세그먼트에서는 기존처럼 teach-back 메시지 유지
- `tests/test_tp4_problem_examples.py` 추가
- `docs/experiments/tp4_problem_examples.md`에 소금물 문제 모의 대화 기록

## 이전과 달라진 점

### 이전

- TP4 막힘 원인 선택지는 공통 placeholder 중심
- `build_expression` 같은 일부 원인의 힌트 스텝은 코드에 고정
- `load_problem()`은 있었지만 TP4에서 문제/해설 데이터를 직접 사용하지 않음

### 이후

- `current_task.problem_id`가 있으면 TP4가 문제 데이터를 불러옴
- LLM 프롬프트에 문제, 정답, 해설, 학년 그룹, 세그먼트, 선택한 막힘 원인을 함께 전달
- 문제별 막힘 선택지와 힌트 스텝을 실험할 수 있음
- `current_task.problem_id`가 없더라도 `build_expression`은 과목·단원 맥락으로 LLM 힌트를 생성하고, 실패 시 일반 fallback을 사용
- LLM 응답 실패 시에도 기본 선택지/힌트로 안전하게 응답 가능

## 테스트

```bash
uv run pytest tests/test_tp4.py tests/test_tp4_problem_examples.py
```

결과:

```text
17 passed
```

## 남은 논의

- 실제 PDF 20문제에서 어떤 필드까지 구조화할지 결정 필요
- 정답 노출 방지 규칙을 더 강하게 둘지, 프롬프트 지침으로 충분한지 팀 합의 필요
- 프론트에서 `problem_id`를 직접 넘길지, 학생의 `today_tasks`에 연결된 문제 ID를 사용할지 결정 필요
