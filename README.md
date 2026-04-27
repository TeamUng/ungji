# ungji

Chatbot-styled study coach for Korean elementary schoolers.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (fast Python package manager)

### Install uv

**macOS / Linux:**

    curl -LsSf https://astral.sh/uv/install.sh | sh

**Windows (PowerShell):**

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

## First-time setup

    git clone https://github.com/TeamUng/ungji.git
    cd ungji
    git config user.name "Your Name"
    git config user.email "your-github-email@example.com"
    git config merge.autoStash true
    git config push.autoSetupRemote true
    git checkout dev
    git pull

    uv sync                  # installs Python 3.12 + deps into .venv
    cp .env.example .env     # then fill in any keys you need

> **Windows**: use `copy .env.example .env` or `Copy-Item .env.example .env` in PowerShell instead of `cp`.

## Run the server

    uv run uvicorn app.main:app --reload

Then open:

- http://localhost:8000 → redirects to interactive API docs
- http://localhost:8000/docs → Swagger UI (test any endpoint from the browser)
- http://localhost:8000/health → `{"status": "ok"}`

## Run tests

    uv run pytest

## Project structure

See `AGENTS.md` for conventions and architecture notes.

---

## Guardrail middleware

The guardrail system lives in `app/guardrails/` and is fully self-contained.
It is not wired into any route yet — integration is opt-in per endpoint.

### How it works

Two pipeline stages wrap every LLM call:

| Stage | Guard | Checks | Severity |
|---|---|---|---|
| Pre-LLM (input) | `SafetyCheck` | profanity · prompt injection · topic relevance | **BLOCK** — refuses input, shows age-appropriate Korean message to student |
| Post-LLM (output) | `ResponseEvaluator` | age-appropriateness · tone · quality | **WARN** — logs issue, response still delivered |

`SafetyCheck` runs a fast rule-based pre-screen first (no API call), then falls back to a single Solar Pro call for nuanced cases. `ResponseEvaluator` always uses one Solar Pro call. Both read `UPSTAGE_API_KEY` and `UPSTAGE_BASE_URL` from `.env`.

Two touchpoint profiles control how strictly topic relevance is enforced:

| Profile | Touchpoints |
|---|---|
| Lighthearted | `home_screen`, `after_all_tasks`, `exit` |
| Study-focused | `during_study`, `after_task` |

### Integrating into a route

```python
from app.guardrails import GuardrailContext, build_pipeline

@router.post("/chat/during_study")
async def during_study_chat(request: ChatRequest):
    context = GuardrailContext(
        touchpoint    = "during_study",
        student_grade = request.student_grade,
        student_type  = request.student_type,  # optional, for later personalisation
        session_id    = request.session_id,
    )
    pipeline = build_pipeline(context)

    # ① Check student input — blocks if unsafe
    input_result = await pipeline.check_input(request.message, context)
    if not input_result.passed:
        return ChatResponse(message=input_result.blocked_message)

    # ② Normal LLM call (unchanged)
    llm_response = await solar_pro.chat(...)

    # ③ Check LLM output — warns only, response always delivered
    await pipeline.check_output(llm_response, context)

    return ChatResponse(message=llm_response)
```

To remove the guardrail from a route, delete the three marked steps. Nothing else in the codebase depends on `app/guardrails/`.

### Run guardrail tests

    uv run pytest tests/guardrails/
