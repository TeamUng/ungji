# Worklog — feature/persona-brs

## 작업 배경

PR #25(`refactor: 페르소나를 단일 캐릭터 '뽀롱쌤'으로 통합`)로 학년별 인격 분리에서 **인격 공통 + 톤만 학년별 분기** 구조로 페르소나가 재편되어 dev에 머지된 상태였다.
이 변경의 핵심 가치(BRS 단일 인격 정체성, 학년별 톤 차이)가 향후 문구 손질로 무너지지 않도록 회귀 테스트를 보강할 필요가 있었다.

## 왜 필요한가

- 뽀롱쌤은 모든 학년에서 동일한 캐릭터·가치관·금기어를 공유해야 한다 → 한 군데라도 빠지면 인격이 학년별로 다시 갈라진다.
- 학년별로 차별화돼야 하는 건 톤(글자수·말투)뿐인데, 우연히 같아지면 분기 의미가 없다.
- 시스템 프롬프트 조립(`build_system_prompt`)이 페르소나·전략·역할을 모두 포함하는지도 보호 대상.

## 구현 방법

- `tests/test_prompts.py`에 세 묶음의 회귀 테스트 추가
  - **BRS 인격 통일성**: 모든 `GradeGroup`에서 캐릭터명·fallback 호칭·핵심 가치관 4개·금기 2개·시그니처 표현(`뽀롱~`, `뽀로롱?!`)이 일관되게 나오는지
  - **학년별 톤 차이**: `LOWER`/`MIDDLE`/`UPPER` 각각이 자기 톤 가이드(글자수, 해요체 등)를 가지고 서로 달라지는지
  - **시스템 프롬프트 조립**: `build_system_prompt`가 persona + strategy + role 셋 다 포함하는지

## 변경 내용

- `tests/test_prompts.py` BRS 인격/톤/조립 회귀 테스트 71줄 추가

## 주요 변경 파일

- `tests/test_prompts.py` [수정]
  - BRS 인격 통일성 회귀 테스트
  - 학년별 톤 차이 회귀 테스트
  - `build_system_prompt` 조립 검증
- `docs/worklogs/2026-04-29_feature-persona-brs.md` [신규]
  - 작업 배경과 변경 기록

## 확인

- `uv run pytest tests/test_prompts.py` → 20 passed
- `uv run pytest` → 139 passed

## PR 참고

- PR 대상: `dev`
- 작업 도중 dev가 두 차례 진행돼(PR #25 본체 포함) 두 번의 머지 커밋이 포함된다.
- 본 PR의 실질적 추가 변경은 `tests/test_prompts.py` 71줄.
