# 워크로그: 2026-04-27

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-27 |
| 담당자 | mireuyoon |
| 브랜치 | feature/T1-data-loader |
| TODO 항목 | T1 데이터 로더 |
| PR 대상 | dev ← feature/T1-data-loader |

---

## 한 줄 요약

> 학생과 문제 목업 JSON을 읽는 데이터 로더를 만들고, 정상 조회와 없는 ID 예외 처리를 테스트했습니다.

---

## 비개발자 요약 — 왜 했고 무엇을 바꿨는지

### 왜 했나요?

이후 T4~T8 노드는 학생의 학년, 성취도, 성실도, 오늘의 학습 과제, 문제 해설 데이터를 읽어야 합니다.
아직 실제 DB나 Supabase가 연결되지 않았기 때문에, 지금은 JSON 파일을 임시 데이터 저장소처럼 사용합니다.

### 무엇을 바꿨나요?

- `app/data/mock_students.json`: 학생 목업 데이터를 담을 빈 배열 파일을 만들었습니다.
- `app/data/mock_problems.json`: 문제 목업 데이터를 담을 빈 배열 파일을 만들었습니다.
- `app/data/loader.py`: `student_id`, `problem_id`로 원하는 데이터를 찾아오는 함수를 만들었습니다.
- `tests/test_loader.py`: 정상 조회와 없는 ID 조회 시 예외가 나는지 확인하는 테스트를 추가했습니다.

---

## 기술 상세

### 변경 파일 목록

| 파일 | 구분 | 설명 |
|------|------|------|
| `app/data/__init__.py` | 신규 | 데이터 로더 패키지 진입점 |
| `app/data/loader.py` | 신규 | `load_student`, `load_problem` 구현 |
| `app/data/mock_students.json` | 신규 | 학생 목업 데이터 파일, 현재는 빈 배열 |
| `app/data/mock_problems.json` | 신규 | 문제 목업 데이터 파일, 현재는 빈 배열 |
| `tests/test_loader.py` | 신규 | 데이터 로더 정상/예외 테스트 |
| `TODO.md` | 수정 | T1 완료 체크박스 반영 |
| `docs/worklogs/2026-04-27_feature-T1-data-loader.md` | 신규 | 이번 브랜치 작업 기록 |

### 구현 메모

- JSON 파일 최상위 구조는 배열이어야 합니다.
- 배열 안의 각 값은 학생 또는 문제 한 건을 나타내는 객체여야 합니다.
- 실제 목업 파일은 빈 배열로 유지하고, 테스트에서는 임시 JSON 파일을 만들어 로더가 그 파일을 읽도록 바꿨습니다.
- 없는 `student_id`나 `problem_id`를 요청하면 `KeyError`를 발생시켜 이후 API 계층에서 4xx 응답으로 바꾸기 쉽게 했습니다.

### 결과 및 확인

```bash
uv run pytest tests/test_loader.py
# 4 passed

uv run pytest
# 7 passed
```

### 다음 작업에 주는 영향

- T4 classify 노드는 `load_student()`를 사용해 학생 데이터를 읽을 수 있습니다.
- T6 TP4 노드는 `load_problem()`을 사용해 문제 해설, 힌트, 단계별 풀이 데이터를 참조할 수 있습니다.
