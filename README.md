# ungji

Chatbot-styled study coach for Korean elementary schoolers.

---

## 새 팀원이라면 — 여기서 시작하세요

**Step 1. 레포 클론 + 환경 세팅** → 아래 [First-time setup](#first-time-setup) 따라 진행

**Step 2. AI 에이전트 실행**

    # Claude Code 사용자
    claude

    # OpenAI Codex CLI 사용자
    codex

**Step 3. 에이전트에게 한 마디**

    "TODO.md 확인하고 T번호 작업 시작해줘"

에이전트가 현재 상태·브랜치 규칙·커밋 형식·워크로그 작성까지 자동으로 안내합니다.

> 협업 규칙 전체: `docs/TEAM_WORKFLOW.md`

---

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

---

## AI 코딩 에이전트로 작업하기

이 프로젝트는 팀원 각자가 AI 코딩 에이전트와 함께 작업합니다.
에이전트가 프로젝트 규칙·현재 상태·협업 워크플로우를 자동으로 인식하도록 설정되어 있습니다.

### Claude Code 사용자

`CLAUDE.md`가 세션 시작 시 자동으로 로드됩니다.

**설치 (없다면)**

    npm install -g @anthropic-ai/claude-code

**시작 방법**

    cd ungji
    claude

그 다음 에이전트에게 한 마디만 하면 됩니다.

    "TODO.md 확인하고 T1 작업 시작해줘"

에이전트가 `CLAUDE.md` → `AGENTS.md` 순서로 읽고, 브랜치 생성부터 커밋·워크로그 작성까지 규칙대로 안내합니다.

### OpenAI Codex CLI 사용자

`AGENTS.md`가 세션 시작 시 자동으로 로드됩니다.

**설치 (없다면)**

    npm install -g @openai/codex

**시작 방법**

    cd ungji
    codex

그 다음 에이전트에게 한 마디만 하면 됩니다.

    "TODO.md 확인하고 T1 작업 시작해줘"

에이전트가 `AGENTS.md`를 읽고 현재 상태·협업 규칙·기술 규칙을 모두 파악한 상태로 시작합니다.

### 두 도구 공통 — 작업 흐름

```
에이전트 실행
    ↓
컨텍스트 자동 로드 (CLAUDE.md 또는 AGENTS.md)
    ↓
"T번호 작업 시작해줘"
    ↓
에이전트가 TODO.md 확인 → origin/dev 기준 브랜치 생성 → 구현 → 커밋 안내
    ↓
PR 전: 에이전트가 TODO.md 체크 + docs/worklogs/ 작성 안내
    ↓
사람이 직접: git push → PR 생성 → 리뷰 → 머지
```

> 협업 규칙 상세: `docs/TEAM_WORKFLOW.md`
> 현재 작업 목록: `TODO.md`

---

## Project structure

See `AGENTS.md` for conventions, current status, and architecture notes.
