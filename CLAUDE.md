# CLAUDE.md

> Claude Code가 세션 시작 시 자동으로 읽는 파일입니다.
> 기술 코딩 규칙은 `AGENTS.md`, 협업 워크플로우 상세는 `docs/TEAM_WORKFLOW.md`를 참고하세요.

---

## 프로젝트

초등학생 1~6학년 맞춤형 AI 학습코치 챗봇 (웅진씽크빅 스마트올 MVP)
**스택**: Python 3.12, FastAPI, LangGraph, Upstage Solar Pro, pytest, uv
**개발 방식**: 5인 병렬 개발 — 각자 Claude Code로 작업, TODO.md 순서대로 진행

---

## 현재 상태

| 항목 | 내용 |
|------|------|
| Phase | 1 (기반 세팅 진행 중) |
| 완료 | Phase 0 (enums·constants·schemas), T2 (Upstage 클라이언트), T3 (프롬프트) |
| 진행 중 | T1 (데이터 로더) |
| 다음 단계 | T4~T8 (노드 구현) — T1 완료 후 시작 |

> **이 섹션은 T번호 작업 완료 후 머지 시마다 업데이트합니다.**

---

## 세션 시작 시 반드시 할 것

1. `AGENTS.md` 읽기 — 기술 규칙·현재 상태·협업 규칙 요약 확인
2. `TODO.md` 확인 → 현재 작업 파악, 완료 항목 확인
3. `git status` + `git branch` → 현재 브랜치·변경사항 파악
4. 작업할 T번호의 **담당 파일 범위** 확인 (다른 T번호 파일 수정 금지)

---

## 핵심 규칙 요약

### 새 작업 시작할 때
```bash
git fetch origin
git checkout dev && git pull origin dev   # 반드시 원격 dev 최신화
git checkout -b feature/T번호-간단설명    # 예: feature/T1-data-loader
```
→ 상세: `docs/TEAM_WORKFLOW.md` 섹션 3

### 커밋할 때
- 형식: `type: 한 줄 요약 (무엇을 + 왜)`
- 본문 필수: 배경(왜) · 방법(어떻게) · 주요 변경 파일
- type: `feat` / `fix` / `docs` / `chore` / `refactor` / `test`
→ 상세: `docs/TEAM_WORKFLOW.md` 섹션 4

### PR 올리기 전에
- `TODO.md` 완료 항목 체크박스 업데이트 후 커밋
- `docs/worklogs/YYYY-MM-DD_브랜치명.md` 작성 후 커밋
- PR 템플릿(`.github/pull_request_template.md`) 모든 항목 채우기
→ 상세: `docs/TEAM_WORKFLOW.md` 섹션 5, 10

### 머지 후
- GitHub에서 브랜치 삭제
- 이슈 close 확인
- 이 파일(CLAUDE.md)의 **현재 상태 섹션** 업데이트

---

## 절대 하면 안 되는 것

- `dev` 브랜치에 직접 커밋 또는 push
- 자신의 T번호 이외 파일 수정
- `git push` 사용자 확인 없이 단독 실행
- PR 없이 dev 브랜치 머지
- `--no-verify` 또는 `--force` push

---

## 참고 문서

| 목적 | 파일 |
|------|------|
| 기술 규칙 (로깅·설정·테스트 규칙) | `AGENTS.md` |
| 협업 워크플로우 전체 (브랜치·커밋·PR·워크로그) | `docs/TEAM_WORKFLOW.md` |
| 기능 요구사항 (케이스 1·2 시나리오) | `docs/PRD.md` |
| State 설계 (ChatState·세그먼트 판별·TP 정의) | `docs/STATE_DESIGN.md` |
| 아키텍처 (기술 스택·디렉토리·그래프 흐름) | `docs/ARCHITECTURE_REVIEW.md` |
| 전체 작업 목록 (Phase별 TODO) | `TODO.md` |
| 작업 이력 | `docs/worklogs/` |
