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
