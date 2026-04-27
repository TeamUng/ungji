# Worklog — feature/T3-prompts-tests

## 작업 배경

T3 프롬프트 구현은 완료되어 있었지만, 학년별 페르소나와 세그먼트별 코칭 전략이 PRD 케이스 1·2 방향을 계속 만족하는지 보호하는 테스트가 없었다.

## 작업 내용

- `tests/test_prompts.py` 신규 작성
  - 3개 학년 그룹 전체에 대해 persona 반환값 검증
  - 4개 세그먼트 전체에 대해 coaching strategy 반환값 검증
  - 케이스 1: lower + `못함+불성실` 프롬프트 방향 검증
  - 케이스 2: upper + `못함+성실` 프롬프트 방향 검증
- `TODO.md` T3 테스트 체크리스트 완료 반영

## 확인

- `uv run pytest tests/test_prompts.py` 통과

## 다음 작업

- T2 Upstage client 테스트 보완
- T4~T7 노드 구현 시 T3 프롬프트를 시스템 프롬프트 조립에 연결
