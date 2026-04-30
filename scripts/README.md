# Script Test Runners

This folder contains offline-ish test runners for checking how the study coach behaves across mock students, touchpoints, and LLM/model choices. The scripts call the LangGraph graph directly; they do not start FastAPI.

Use these scripts when you want to answer questions like:

- What does the coach say in TP1-TP5 for a specific mock student?
- Did a prompt change alter the tone, length, persona, or safety wording?
- Which model or motivator/helper model combo gives better scenario outputs?

Important distinction: these scripts save generated coach responses and scenario transcripts. They do not save the full internal LLM prompt payload by default. If you need raw prompt/trace inspection, enable LangSmith tracing through the project environment.

## Prerequisites

From the repository root:

```powershell
uv --cache-dir .uv-cache sync
cp .env.example .env
```

Fill the relevant API keys in `.env`.

- `run_scenarios.py` uses the app's normal graph and LLM routing from `app/clients/llm.py`.
- `run_model_comparison.py` needs `OPENROUTER_API_KEY` for OpenRouter models and `UPSTAGE_API_KEY` for `solar-pro2`.
- `run_combo_comparison.py` has the same model/API-key requirements as `run_model_comparison.py`.
- `summarize_length_violations.py` only parses existing report files and does not call an LLM.

Use `uv --cache-dir .uv-cache ...` on Windows to avoid uv user-cache permission issues.

Current app model routing and fallback routing are code-visible in `app/clients/llm.py`:

| Agent | Touchpoints | Model |
|---|---|---|
| motivator | TP1, TP2, TP3, TP5, non-TP4 chat | `google/gemini-2.5-flash` |
| helper | TP4 stuck/help coaching | `openai/gpt-5.4-mini` |
| guardrail judge | input/output guardrail LLM judge | `openai/gpt-5.4-mini` |
| common fallback | used when any primary LLM call fails | Upstage `solar-pro2` |

Do not set model names in `.env`; change `app/clients/llm.py` when the runtime model routing changes.

## Quick Path: Check Scenario Outputs

For the most direct "how do the prompts/responses come out for each scenario?" check, run `run_scenarios.py`.

List available mock students:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --list-students
```

Run the default smoke set:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py
```

Run one or two specific students:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --students lower-low-lazy upper-low-diligent
```

Run all 12 mock student profiles:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --all
```

Run a richer conversational pass where the script simulates student follow-up replies:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --students lower-low-lazy --simulate-conversation
```

Every run writes:

```text
scripts/results/scenario_results_YYYYMMDD_HHMMSS.csv
scripts/results/scenario_transcript_YYYYMMDD_HHMMSS.md
```

Open the Markdown transcript first when reviewing wording. Open the CSV when comparing fields, touchpoints, choices, message types, errors, or expectation checks.

If `scripts/scenarios/expected_cases.json` exists, the runner also writes:

```text
scripts/results/scenario_eval_YYYYMMDD_HHMMSS.csv
```

Skip expectation checks when you only want raw outputs:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --skip-expectations
```

## Script Map

### `run_scenarios.py`

Primary scenario regression runner.

- Calls `app.services.graph.graph` directly.
- Uses the 12 mock student profiles in `app/data/mock_students.json`.
- Defaults to 4 smoke profiles: `lower-low-diligent`, `lower-low-lazy`, `upper-low-diligent`, `upper-low-lazy`.
- Runs 6 base touchpoint scenarios per selected student: TP1, TP2, TP3, TP4 turn 1, TP4 turn 2, TP5.
- Writes a structured CSV, a human-readable Markdown transcript, and optional expectation-evaluation CSV.
- `--simulate-conversation` adds extra graph turns after coach responses.

Useful commands:

```powershell
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group middle --ability high
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --grade-group lower upper --ability low --diligence lazy diligent
uv --cache-dir .uv-cache run python scripts/run_scenarios.py --expectations scripts/scenarios/expected_cases.json
```

Main CLI options:

| Option | Purpose |
|---|---|
| `--all` | Run all 12 mock student profiles |
| `--students ...` | Run exact student IDs |
| `--grade-group lower middle upper` | Filter by grade group |
| `--ability low high` | Filter by ability |
| `--diligence lazy diligent` | Filter by diligence |
| `--list-students` | Print available profiles and exit |
| `--simulate-conversation` | Simulate student replies and continue the graph |
| `--expectations PATH` | Use a specific expectation JSON file |
| `--skip-expectations` | Skip expectation CSV generation |

`--all` cannot be combined with `--students` or filters. `--students` cannot be combined with filters.

### `run_model_comparison.py`

Model sweep runner for comparing single-model behavior.

- Defines a fixed 7-scenario comparison set in `SCENARIOS`.
- Replaces both `motivator_llm` and `helper_llm` with the selected model during each run.
- Repeats each scenario with `--iterations`.
- Collects graph latency, LLM latency, token usage, character counts, persona/signature checks, forbidden internal-name leaks, and English-word leaks.
- Writes a main report and one raw Markdown file per model.

Smoke test one or two models:

```powershell
uv --cache-dir .uv-cache run python scripts/run_model_comparison.py --iterations 1 --models gpt-5.4-mini,solar-pro2
```

Run the full configured model list:

```powershell
uv --cache-dir .uv-cache run python scripts/run_model_comparison.py --iterations 10
```

Available model labels are currently:

```text
gpt-5.4-mini
gpt-5.4-nano
gemini-2.5-flash
gemini-2.5-flash-lite
solar-pro3
solar-pro2
```

Outputs:

```text
scripts/results/model_comparison/YYYY-MM-DD/YYYY-MM-DD_model_test.md
scripts/results/model_comparison/YYYY-MM-DD/raw/<model-label>.md
```

Read the `raw/<model-label>.md` files when you want the actual generated responses scenario by scenario.

### `run_combo_comparison.py`

Hybrid model-combo runner.

- Imports the same comparison scenarios and `run_iteration()` logic from `run_model_comparison.py`.
- Routes TP1, TP2, TP3, and TP5 through the combo's `motivator` model.
- Routes TP4 through the combo's `helper` model.
- Aggregates success, persona/signature, internal-name leaks, English leaks, latency, and token usage.
- Leaves length-limit review to the separate length-summary script.

Smoke test combo A:

```powershell
uv --cache-dir .uv-cache run python scripts/run_combo_comparison.py --iterations 1 --combos A --out-suffix combos_smoke
```

Run all configured combos:

```powershell
uv --cache-dir .uv-cache run python scripts/run_combo_comparison.py --iterations 10
```

`--combos` accepts comma-separated label prefixes, so `A`, `B`, and `C` are usually enough.

Outputs:

```text
scripts/results/model_comparison/YYYY-MM-DD/<out-suffix>/YYYY-MM-DD_combo_test.md
scripts/results/model_comparison/YYYY-MM-DD/<out-suffix>/raw/<combo-label>.md
```

### `summarize_length_violations.py`

Post-processor for model-comparison raw files.

- Reads `scripts/results/model_comparison/<date>/raw/*.md`.
- Extracts per-scenario character counts and responses.
- Writes a Markdown summary with shortest examples, longest examples, and per-model averages.
- Intended for `run_model_comparison.py` output, not combo output.

Run it after a model comparison:

```powershell
uv --cache-dir .uv-cache run python scripts/summarize_length_violations.py --date 2026-04-30
```

Output:

```text
scripts/results/model_comparison/YYYY-MM-DD/length_violations.md
```

## Result Review Order

For prompt/wording review:

1. Run `run_scenarios.py` for the student set you care about.
2. Read `scenario_transcript_*.md`.
3. Check `scenario_eval_*.csv` for expectation failures if enabled.
4. Use `run_model_comparison.py --iterations 1 --models ...` for a quick model smoke comparison.
5. Increase `--iterations` only after the smoke run looks sane.
6. Use `run_combo_comparison.py` when deciding whether motivator and helper should use different models.
7. Run `summarize_length_violations.py` after a model sweep when response length is the main concern.

## Current Scenario Sources

- Student profiles: `app/data/mock_students.json`
- Problem content: `app/data/mock_problems.json`
- Scenario expectations: `scripts/scenarios/expected_cases.json`
- App graph under test: `app/services/graph.py`
- LLM client globals patched by comparison scripts: `app/clients/llm.py`

Generated files under `scripts/results/` are review artifacts. Check whether they are intentionally needed before committing them.
