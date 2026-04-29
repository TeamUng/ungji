# Worklog — feat/model-test

## 작업 배경

뽀롱쌤 챗봇은 motivator(TP1·2·3·5)와 helper(TP4) 두 노드로 구성되며 각 노드가 LLM 호출을 한다. 그동안 두 노드가 동일한 `solar-pro2` 단일 LLM을 공유하는 구조였는데, 운영 진입을 앞두고 어떤 모델이 어떤 노드에 적합한지를 데이터로 결정할 필요가 있었다.

OpenRouter에 5\$ 충전 후, 다음 6개 모델을 후보로 선정해 비교 실험을 진행했다.

- OpenAI: `gpt-5.4-mini`, `gpt-5.4-nano`
- Google: `gemini-2.5-flash`, `gemini-2.5-flash-lite`
- Upstage: `solar-pro-3` (OpenRouter), `solar-pro-2` (Upstage 직접 호출 — OpenRouter 미지원)

## 왜 필요한가

- Solar 단일 모델이 모든 TP에 최적이라는 보장이 없음.
- TP4 helper의 `bind_tools` 도구 호출(`send_causes`, `send_text`, `send_hint_card`)을 모델마다 얼마나 신뢰성 있게 처리하는지 비교 필요.
- 학년별 톤·페르소나 일관성·환각·메타 노출 등 안전 지표를 정량화해 운영 후보를 좁힐 필요.

## 구현 방법

### 실험 인프라

- `scripts/run_model_comparison.py`: 단일 모델 평가 러너. `app.clients.upstage.llm` (당시 명) 모듈 어트리뷰트를 컨텍스트 매니저로 일시 교체해 노드 코드 무수정으로 모델 스왑.
- LangChain `BaseCallbackHandler`로 LLM 호출별 latency·prompt/completion 토큰 자동 캡처.
- 자동 지표: 성공률 / 길이 OK / 페르소나·시그니처 노출률 / 금기어·영어 누수 / graph p50·p95 / 토큰 평균 / 글자수 σ.
- 모델별 raw 출력은 `scripts/results/model_comparison/2026-04-29/raw/<모델>.md` 로 분리 저장. Claude(본 작업자)가 평가 표를 직접 채워 메인 리포트에 반영.

### 3단계 실험

- **1차 (N=10, 단독 6모델)**: gpt-5.4-mini/nano TP4 도구 호출 100% 실패, solar-pro2 메타·환각·이름 오류, gemini 계열 길이 위반 다수.
- **2차 (N=10, 3 조합)**: motivator/helper 노드별 모델 분리. `scripts/run_combo_comparison.py` 신규.
  - A_안정 (mini + gemini-flash), B_Solar활용 (mini + solar-pro3), C_Gemini단일 (flash-lite + flash).
- **3차 (N=30, 패치 후 재검증)**: HELPER_ROLE에 placeholder 차단 한 줄 추가하여 solar-pro3의 "아까 ~라고" 노출 해결. 그러나 학생 이름 오류 13% 잔존 확정.

### 운영 LLM 분리 (A_안정 채택)

- `app/clients/upstage.py` → `app/clients/llm.py` 로 재구성. ChatOpenAI 를 OpenRouter 경유로 호출하는 `motivator_llm`·`helper_llm` 두 인스턴스 export.
- `motivator.py`, `helper.py` 에서 각자 자기 LLM을 lazy import.
- 환경변수로 모델·temperature·timeout override 가능.
- `tests/conftest.py mock_llm` fixture가 두 어트리뷰트 모두 fake 로 패치하도록 갱신.
- `tests/test_upstage_client.py` → `test_llm_client.py` 재작성.
- `.env.example` LLM 섹션 재구성, 협업 멤버 참고용 의도 주석 추가.
- 보조 스크립트 `scripts/run_combo_comparison.py`, `scripts/summarize_length_violations.py` 신규.

### 결과 보고서

- `scripts/results/model_comparison/2026-04-29/FINAL_REPORT.md` (179줄): 협업 참고용 종합 보고서. A_안정 채택 근거, Solar 사용 불가 사유, 글자수 한도 비현실성 등 운영 의사결정 정보 정리.
- 1차/2차/3차 메인 보고서 + raw 출력물 통째로 `scripts/results/` 에 보존 (`.gitignore` 예외 `git add -f`).

## 주요 변경 파일

- `app/clients/upstage.py` → `app/clients/llm.py` [rename + content]
- `app/services/nodes/{motivator,helper}.py` [LLM import 변경]
- `app/services/prompts/agents.py` [HELPER_ROLE placeholder 차단 한 줄]
- `app/core/config.py` [MOTIVATOR_MODEL·HELPER_MODEL·LLM_TEMPERATURE·LLM_TIMEOUT_SECONDS 추가]
- `tests/conftest.py` [mock_llm fixture 갱신]
- `tests/test_upstage_client.py` → `tests/test_llm_client.py` [rename + 재작성]
- `.env.example` [LLM 섹션 재구성]
- `scripts/run_model_comparison.py` [use_model 컨텍스트에 target 인자 추가]
- `scripts/run_combo_comparison.py` [신규]
- `scripts/summarize_length_violations.py` [신규]
- `scripts/results/model_comparison/2026-04-29/` [신규 — 1·2·3차 결과 + FINAL_REPORT.md]
- `docs/worklogs/2026-04-29_feat-model-test.md` [신규]

## 확인

- `uv run pytest -q` → 139 passed
- 실 호출 sanity: motivator_llm·helper_llm 각각 OpenRouter 정상 응답
- graph end-to-end sanity: TP1 motivator·TP4 helper 정상 라우팅, helper의 도구 호출이 영문 snake_case ID(`find_claim`, `distinguish_evidence` 등) 정상 반환

## PR 참고

- PR 대상: `dev`
- 본 PR 직전 dev 에 대규모 LLM client refactor (#27 fallback 시스템)가 머지된 상태. 본 브랜치의 `app/clients/llm.py`·`tests/test_llm_client.py`·`config.py`·`agents.py`·`motivator.py`·`helper.py`·`conftest.py`·`.env.example` 모두 dev 와 충돌 가능성 높음. PR 생성 시 GitHub UI에서 충돌 검토 필요.

## 다음 작업

- §5.1 글자수 한도 비현실성 해결 (저학년 60자 한도가 실측 평균 155자 — 위반율 100%). 한도 현실화·프롬프트 압축·UI 절단 중 정책 결정 필요.
- §5.2 motivator 페르소나 자기 호명("뽀롱쌤이야") 가이드 추가 후 재실험.
- 운영 진입 직전 N=100+ 재실험 (희귀 안전 사고 빈도 확정).
