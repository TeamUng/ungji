# Scenario Runner README / 시나리오 러너 README

## 한국어

`scripts/run_scenarios.py`는 FastAPI 엔드포인트를 거치지 않고 LangGraph를 직접 호출하는 회귀 테스트용 실행 스크립트입니다. 선택한 학생 프로필에 대해 TP1~TP5 시나리오를 실행하고, 결과를 CSV와 Markdown 대화 기록으로 저장합니다.

### 무엇을 실행하나요?

기본 실행은 아래 4개 학생 프로필만 사용합니다.

- `lower-low-diligent`
- `lower-low-lazy`
- `upper-low-diligent`
- `upper-low-lazy`

각 학생에 대해 기본적으로 다음 6개 시나리오를 실행합니다.

1. TP1 홈 화면 진입
2. TP2 단원 학습 완료
3. TP3 이탈 방지
4. TP4 문제 도움 1턴: 문제 ID 전달 및 막힌 이유/코칭 응답
5. TP4 문제 도움 2턴: 학생의 응답 전달 및 코칭
6. TP5 학습 종료

TP4에서는 선택된 curriculum unit의 첫 번째 `problem_ids` 값을 사용합니다. 문제 내용은 `app/data/mock_problems.json`에서 로드됩니다.

### 실행 방법

기본 4개 프로필 실행:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py
```

전체 12개 프로필 실행:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --all
```

특정 학생만 실행:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --students lower-low-lazy upper-high-diligent
```

조건으로 필터링:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group middle --ability high
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group lower upper --ability low --diligence lazy diligent
```

사용 가능한 학생 목록 보기:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --list-students
```

학생 응답을 시뮬레이션해서 대화를 더 이어가기:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --simulate-conversation
```

`--simulate-conversation`은 추가 LangGraph 호출을 만들기 때문에 LLM API 호출 수가 늘어납니다.

### CLI 옵션

| 옵션 | 설명 |
|---|---|
| `--all` | 12개 전체 학생 프로필 실행 |
| `--students ...` | 지정한 student ID만 실행 |
| `--grade-group lower middle upper` | 학년 그룹 필터 |
| `--ability low high` | 학습 능력 필터 |
| `--diligence lazy diligent` | 성실도 필터 |
| `--list-students` | 사용 가능한 프로필 출력 후 종료 |
| `--simulate-conversation` | 코치 응답 뒤에 학생 응답을 시뮬레이션하고 그래프를 이어서 호출 |

`--all`은 `--students` 또는 조건 필터와 함께 사용할 수 없습니다. `--students`도 조건 필터와 함께 사용할 수 없습니다.

### 출력 파일

실행하면 `scripts/results/` 아래에 두 파일이 생성됩니다.

```text
scripts/results/scenario_results_YYYYMMDD_HHMMSS.csv
scripts/results/scenario_transcript_YYYYMMDD_HHMMSS.md
```

CSV에는 회귀 비교에 필요한 구조화된 결과가 들어갑니다.

주요 컬럼:

- `student_id`
- `grade_group`
- `segment`
- `expected_grade_group`
- `expected_ability`
- `expected_diligence`
- `classification_ok`
- `task_index`
- `task_count`
- `available_units`
- `problem_id`
- `touchpoint`
- `use_case`
- `turn`
- `response_text`
- `choices`
- `message_types`
- `error`

Markdown transcript에는 학생과 코치의 대화가 사람이 읽기 쉬운 형태로 기록됩니다. TP4 선택지는 choice id와 label이 함께 표시됩니다.

### 주의사항

- 이 스크립트는 실제 LangGraph와 LLM 클라이언트를 호출합니다.
- `.env`에 필요한 API 키가 없으면 실제 실행이 실패할 수 있습니다.
- `--list-students`는 LLM을 호출하지 않는 가벼운 확인 명령입니다.
- 생성된 CSV/Markdown 결과 파일은 회귀 확인용 산출물입니다. 커밋 전에 필요한 파일인지 확인하세요.

## English

`scripts/run_scenarios.py` is a regression runner that calls LangGraph directly instead of going through the FastAPI endpoint. It runs TP1-TP5 scenarios for selected mock student profiles and saves both structured CSV results and a Markdown conversation transcript.

### What Does It Run?

By default, it runs only these 4 profiles:

- `lower-low-diligent`
- `lower-low-lazy`
- `upper-low-diligent`
- `upper-low-lazy`

For each student, it runs these 6 base scenarios:

1. TP1 home-screen entry
2. TP2 unit completed
3. TP3 exit prevention
4. TP4 help turn 1: send problem ID and receive stuck-reason/coaching response
5. TP4 help turn 2: send simulated student response and receive coaching
6. TP5 learning wrap-up

For TP4, the runner uses the first `problem_ids` entry from the selected curriculum unit. The problem content is loaded from `app/data/mock_problems.json`.

### How To Run

Run the default 4 profiles:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py
```

Run all 12 profiles:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --all
```

Run exact student IDs:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --students lower-low-lazy upper-high-diligent
```

Filter by criteria:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group middle --ability high
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group lower upper --ability low --diligence lazy diligent
```

List available students:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --list-students
```

Simulate student replies and continue the conversation:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --simulate-conversation
```

`--simulate-conversation` increases the number of LangGraph and LLM calls.

### CLI Options

| Option | Description |
|---|---|
| `--all` | Run all 12 student profiles |
| `--students ...` | Run exact student IDs |
| `--grade-group lower middle upper` | Filter by grade group |
| `--ability low high` | Filter by ability |
| `--diligence lazy diligent` | Filter by diligence |
| `--list-students` | Print available profiles and exit |
| `--simulate-conversation` | Simulate student replies after coach responses and continue the graph |

`--all` cannot be combined with `--students` or criteria filters. `--students` cannot be combined with criteria filters.

### Output Files

Each run creates two files under `scripts/results/`:

```text
scripts/results/scenario_results_YYYYMMDD_HHMMSS.csv
scripts/results/scenario_transcript_YYYYMMDD_HHMMSS.md
```

The CSV contains structured data for regression comparison.

Important columns:

- `student_id`
- `grade_group`
- `segment`
- `expected_grade_group`
- `expected_ability`
- `expected_diligence`
- `classification_ok`
- `task_index`
- `task_count`
- `available_units`
- `problem_id`
- `touchpoint`
- `use_case`
- `turn`
- `response_text`
- `choices`
- `message_types`
- `error`

The Markdown transcript records the student/coach conversation in a human-readable form. TP4 choices include both choice IDs and labels.

### Notes

- The script calls the real LangGraph and LLM client.
- A valid `.env` with the required API keys may be needed for live runs.
- `--list-students` is a lightweight command and does not call the LLM.
- Generated CSV/Markdown files are regression artifacts. Check whether you want to keep them before committing.
