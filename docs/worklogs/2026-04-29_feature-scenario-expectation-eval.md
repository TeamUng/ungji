# feature/scenario-expectation-eval

## 배경

프롬프트와 내부 구조를 수정할 때마다 실제 LLM 출력이 기획 의도와 맞는지 비교할 기준이 필요했다.
특히 TP3 이탈 이벤트처럼 자연어 입력이 아닌 프론트 행동 이벤트는 기대 출력과 금지 출력이 명확해야 한다.

## 작업 내용

- `docs/SCENARIO_EXPECTATIONS.md` 추가
  - 케이스 1/2의 학생 유형, TP1~TP5 기대 출력, 금지 출력, 평가 기준 정리
- `scripts/scenarios/expected_cases.json` 추가
  - runner가 읽을 수 있는 구조화된 기대 조건 정의
- `scripts/run_scenarios.py` 보강
  - 기대 조건 JSON을 읽어 `scenario_eval_*.csv` 생성
  - `must_include_any`, `must_include_all`, `must_not_include`, `max_choices`, `expected_problem_id` 평가 지원
- `scripts/README.md` 업데이트
  - 기대 조건 평가 파일과 CLI 옵션 설명 추가
- `tests/test_scenario_expectations.py` 추가
  - 기대 조건 로딩과 평가 로직 회귀 테스트

## 검증

```bash
uv run pytest tests/test_scenario_expectations.py
uv run python scripts/run_scenarios.py --list-students
uv run pytest
```

결과:

```text
4 passed
224 passed
```
