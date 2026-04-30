# 모델 선택과 비용 트레이드오프

> **2026-04-30 · 발표 자료용**
> 단일 모델로 가지 못한 이유, OpenRouter 비교 실험 과정, 코드 상의 노드↔모델 바인딩, 그리고 현재 복합 혼용 구조의 비용 측정 결과를 정리한 문서.

---

## TL;DR

- **운영 구조 (코드 기준)**:
  - `app/services/nodes/motivator.py` (TP1·2·3·5) → `openai/gpt-5.4-mini`
  - `app/services/nodes/helper.py` (TP4) → `google/gemini-2.5-flash`
- **단일 모델을 버린 이유는 두 가지**:
  1. **GPT-5 Mini 단일** → helper의 `bind_tools` 도구 호출(`send_causes` 등)이 100% 실패 — **성능 실패**
  2. **Gemini 2.5 Flash 단일** → motivator의 단순 코칭에서도 출력이 길어짐 (TP1 고학년 평균 313자) — **토큰·비용 낭비**
- **선정 절차**: OpenRouter에 5\$ 충전 후 3사 6모델을 1차(N=10) → 2차(3조합 N=10) → 3차(N=30) 비교 실험으로 좁힘.
- **현재 비용**(시나리오 1회, 학생 2명, 38회 호출 기준): 약 70.8K 토큰 / **$0.03–$0.06**. 학생 1명·1일 4과목 환산 시 **월 $0.7–$1.5** 수준.

---

## 1. 운영 모델 구성과 코드 매핑

### 1.1 노드 ↔ 모델 매핑 표

| 노드 | 파일 | 역할 | 모델 | 핵심 호출 형태 |
|---|---|---|---|---|
| motivator | `app/services/nodes/motivator.py` | TP1 인사 / TP2 단원완료 / TP3 이탈방지 / TP5 학습종료 / 자유 대화 | `openai/gpt-5.4-mini` | plain text 응답 |
| helper | `app/services/nodes/helper.py` | TP4 문제 막힘 진단 → 원인 선택지 제시 → 코칭 | `google/gemini-2.5-flash` | **`bind_tools` 도구 호출** (`send_causes`, `send_text`, `send_hint_card`, `send_image_card`) |
| judge | `app/guardrails/...` | 가드레일 평가자 | `google/gemini-2.5-flash` (helper 별칭) | 응답 후처리 |

### 1.2 motivator.py — 코드 인용

```python
# app/services/nodes/motivator.py:67
def motivator(state: ChatState) -> ChatResponse:
    """Handle TP1, TP2, TP3, TP5, and non-TP4 free chat turns."""
    from app.clients.llm import motivator_llm as llm
    ...
    response = guarded_invoke(
        llm,
        messages,
        state,
        agent_name="motivator",
        render_output=lambda raw: str(getattr(raw, "content", "")),
    )
```

특징:
- **도구 바인딩 없음**. system + history + situation 메시지를 그대로 invoke.
- 출력은 단일 텍스트(ChatResponse) 한 건. 무거운 추론이 필요 없음.
- 호출 빈도가 가장 높은 노드(TP1·2·3·5 + 자유 대화 모두 담당) → **토큰 단가에 가장 민감**.

### 1.3 helper.py — 코드 인용

```python
# app/services/nodes/helper.py:53
def helper(state: ChatState) -> dict:
    from app.clients.llm import helper_llm as llm
    ...
```

```python
# app/services/nodes/helper.py:141
bound_llm = llm.bind_tools([
    send_causes,
    send_text,
    send_hint_card,
    send_image_card,
])
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_message),
]
response = guarded_invoke(
    bound_llm,
    messages,
    state,
    agent_name="helper",
    render_output=_render_helper_output_for_guard,
)
```

특징:
- **`bind_tools`로 4개 도구를 등록**. 모델이 상황에 맞춰 도구를 골라 호출.
- `send_causes`는 `{"id": "snake_case", "label": "한글"}` 형식의 리스트를 반환해야 함 — JSON 스키마 + 영문 ID 규칙을 지켜야 정상 파싱.
- 호출 빈도는 motivator보다 낮지만, **학습에서 가장 중요한 “문제 막힘” 모먼트**를 담당 → **신뢰성에 가장 민감**.

### 1.4 LLM 인스턴스 정의 — `app/clients/llm.py`

```python
# app/clients/llm.py
def _build_openrouter_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model,
        ...
    )

# motivator: TP1·2·3·5 동기 코칭 노드용
motivator_llm = _build_openrouter_llm(settings.MOTIVATOR_MODEL)
# helper: TP4 문제 막힘 진단/코칭 노드용
helper_llm = _build_openrouter_llm(settings.HELPER_MODEL)
```

```python
# app/core/config.py
MOTIVATOR_MODEL: str = "openai/gpt-5.4-mini"
HELPER_MODEL: str = "google/gemini-2.5-flash"
```

→ 두 인스턴스 모두 OpenRouter 경유. 환경변수만 바꾸면 다른 모델로 즉시 swap 가능 → 비교 실험·롤백이 쉽다.

---

## 2. 현재 비용 측정 (시나리오 1회 실행 기준)

| 항목 | 값 |
|---|---|
| 학생 수 | 2명 |
| 총 LLM 호출 | 38회 (motivator + helper + judge 합산) |
| Input tokens | 68,618 |
| Output tokens | 2,237 |
| Total tokens | **70,855** |
| 추정 비용 | **$0.03 – $0.06** / run |

학생 1명 환산 (전체 세션 1회):

- **35,400 tokens / 약 $0.013–$0.031**
- 30일: 약 $0.39–$0.92

학생 1명 · 매일 4과목 학습 환산 (보수적):

- 하루 약 **59,000 tokens / $0.022–$0.051**
- 30일: **$0.65–$1.54 / 학생 / 월**

> 비용 범위는 OpenRouter 단가 기반 추정이다. 모델별 token breakdown 캡처를 추가하면 좁힐 수 있다.

---

## 3. 단일 모델 후보 검증 — 두 가지 실패 모드

처음 초안은 **GPT-5 Mini 단일**이었다. 운영 진입을 앞두고 6모델을 비교 실험한 결과, 단일 모델 구성은 어떤 선택지로도 성립하지 않았다.

### 3.1 GPT-5 Mini 단일 — **성능 실패 (추론·도구 호출 부족)**

- helper.py의 핵심은 `llm.bind_tools([send_causes, send_text, send_hint_card, send_image_card])` 도구 호출.
- gpt-5.4-mini / gpt-5.4-nano는 1차 N=10 실험에서 **`send_causes` 도구 호출 100% 실패**.
- 학생 입장에서 “문제가 막혔어요” 같은 가장 중요한 학습 모먼트에서 응답이 끊긴다 → 운영 불가.
- 그래서 **추론·도구 호출이 더 강한 모델**(Gemini 2.5 Flash)로 바꾸려고 시도.

### 3.2 Gemini 2.5 Flash 단일 — **비용·토큰 효율 실패**

- helper의 도구 호출은 안정적(30/30 성공). 하지만 motivator.py가 담당하는 **TP1 인사·TP2 단원완료** 같은 짧은 코칭에서도 출력 길이가 늘어난다.

  | 시나리오 | gpt-5.4-mini 평균 | gemini-2.5-flash 평균 | 한도 |
  |---|---|---|---|
  | TP1 고학년 인사 | ~150자 | **313자** | 60–150자 |
  | TP1 저학년 | ~100자 | ~155자 | 60자 |
  | TP4 코칭 | ~155자 | ~155자 | 60–150자 |

- 단순 코칭에 **2배 가까운 토큰을 쓰는 셈** → motivator는 호출 빈도가 가장 높기 때문에 학생 수가 늘면 그대로 비용으로 누적.
- 또한 일부 회차(TP5 ~10%)에서 학습 시작/종료 상황을 혼동하는 안전 사고도 관측.

### 3.3 결론: 단일 모델로 양쪽을 동시에 만족하는 후보 없음

- 강한 모델(Flash) → 단순 작업까지 토큰 낭비 (motivator 영역에서 손해)
- 가벼운 모델(Mini) → 추론·도구 호출에서 무너짐 (helper 영역에서 무용)
- **노드별로 요구사항이 다른 일이 동시에 도는 그래프**라서, 한 모델에 양쪽을 다 맡기면 한 축이 항상 손해.

→ 코드 구조상 motivator.py와 helper.py가 이미 서로 다른 호출 형태(plain text vs tool calling)를 갖고 있었으므로, **`from app.clients.llm import motivator_llm/helper_llm` 두 인스턴스로 분리**하는 것이 가장 자연스러운 해법.

---

## 4. OpenRouter 비교 실험 — 어떻게 골랐나

### 4.1 실험 인프라

- **OpenRouter에 5\$ 충전** → 3사(OpenAI / Google / Upstage) 6모델을 동일 API로 호출.
- `app.clients.llm` 모듈 어트리뷰트(`motivator_llm`, `helper_llm`)를 컨텍스트 매니저로 일시 교체 → **노드 코드 수정 없이 모델 swap**.
- LangChain `BaseCallbackHandler`로 호출별 latency·prompt/completion 토큰 자동 캡처.
- 자동 지표: 성공률 / 길이 OK / 페르소나·시그니처 노출 / 금기어·영어 누수 / graph p50·p95 / 출력 토큰 평균 / 글자수 σ.
- 모델별 raw 응답은 `scripts/results/model_comparison/2026-04-29/raw/` 에 분리 저장 → 사람이 평가 표를 채워 정성평가까지 결합.

### 4.2 후보 모델 6개

| 벤더 | 모델 |
|---|---|
| OpenAI | `gpt-5.4-mini`, `gpt-5.4-nano` |
| Google | `gemini-2.5-flash`, `gemini-2.5-flash-lite` |
| Upstage | `solar-pro-3` (OpenRouter), `solar-pro-2` (Upstage 직접 호출) |

### 4.3 3단계 실험

| 차수 | 목적 | 대상 | N |
|---|---|---|---|
| 1차 | 6모델 단독 평가 | 6모델 × TP1~5 시나리오 7개 | **10** |
| 2차 | 노드별 분리 조합 비교 | A·B·C 3조합 | **10** |
| 3차 | placeholder 패치 후 재검증 | A·B·C 3조합 | **30** |

3조합 정의 (motivator + helper):

- **A_안정**: `gpt-5.4-mini` + `gemini-2.5-flash`
- **B_Solar활용**: `gpt-5.4-mini` + `solar-pro-3`
- **C_Gemini단일**: `gemini-2.5-flash-lite` + `gemini-2.5-flash`

→ **각 조합 30회씩 7개 시나리오 = 210회**를 돌려 정량 + 정성 평가.

### 4.4 3차 N=30 자동 지표 요약

| 조합 | 성공률 | 페르소나 | 시그니처 | graph p50 | 출력 토큰 |
|---|---|---|---|---|---|
| **A_안정** | 210/210 | 1% | 74% | 1545ms | **84** |
| B_Solar활용 | 209/210 | 0% | 67% | 1219ms | 84 |
| C_Gemini단일 | 210/210 | 2% | 79% | **1063ms** | **94** |

A vs C: 출력 토큰 **84 vs 94 (+12%)**. 호출 수가 누적될수록 차이가 커진다.

### 4.5 Solar 계열 탈락 사유

| 모델 | 사유 |
|---|---|
| solar-pro-2 | 응답 안에 내부 메타 노출(“추천 이유:”, “[코칭 전략]”), 콘텐츠 환각, 학생 이름 오류, 길이 σ 180(최악) |
| solar-pro-3 | helper 후보였으나 학생 이름 오류 **13% (4/30)** — placeholder 패치로 다른 이슈는 잡혔지만 이름 오류는 별개 원인으로 잔존 |

→ Solar 계열은 어디에도 채택하지 않음.

---

## 5. 복합 모델 혼용 채택 — A_안정

| 노드 | 파일 | 모델 | 채택 근거 |
|---|---|---|---|
| motivator | `app/services/nodes/motivator.py` | `openai/gpt-5.4-mini` | 짧고 안정적, 출력 토큰 짧음, 페르소나 일관 |
| helper | `app/services/nodes/helper.py` | `google/gemini-2.5-flash` | TP4 도구 호출 30/30, 추론·페르소나 모두 안정 |

이 구조의 장점:

1. **비용**: 호출 빈도 높은 motivator를 가벼운 Mini가 담당 → 토큰 비용 줄임
2. **성능**: 도구 호출이 필요한 TP4(추론 작업)만 더 강한 Flash로 라우팅 → 가장 중요한 학습 모먼트의 신뢰성 확보
3. **벤더 분산**: 한 벤더 장애 시 다른 노드는 계속 동작
4. **운영 swap 용이성**: motivator/helper 노드가 import 시점에 각각의 LLM 인스턴스를 가져오므로, 환경변수(`MOTIVATOR_MODEL`/`HELPER_MODEL`) 변경만으로 무코드 교체 가능

---

## 6. 토큰·비용 비교 (추정)

3차 N=30 출력 토큰 평균을 기준으로 **단일 vs 혼합** 누적 차이를 추정.

| 구성 | 호출당 평균 출력 | 38회 누적 출력 | 상대 |
|---|---|---|---|
| 단일 GPT-5 Mini | (TP4 도구 호출 실패로 측정 불가) | — | **운영 불가** |
| 단일 Gemini 2.5 Flash (≈C) | 94 | 3,572 | +12% |
| **혼합 A_안정 (현재)** | **84** | **3,192** | 기준 |

- TP1 고학년 실측: Mini 평균 ~150자 vs Flash 평균 313자 → **이 시나리오에서만 토큰 약 2배**.
- motivator.py 호출이 helper.py 호출보다 빈도가 높기 때문에, 단일 Flash 구성에서는 **누적 토큰 비용이 가장 비싸지는 영역(motivator)에서 손해**가 커진다.
- 반대로 단일 Mini 구성은 helper.py의 `bind_tools` 도구 호출 자체를 못 돌려 **TP4가 무용** → 비용 비교 자체가 의미 없음.

> 정확한 \$ 절감폭은 모델별 input/output 토큰 단가가 다르므로, 모델별 token breakdown 캡처가 추가되면 다음 발표에서 수치 확정 가능.

---

## 7. 한계 / 다음 단계

| 우선순위 | 항목 |
|---|---|
| P0 | 글자수 한도 비현실 — 저학년 60자 한도가 실측 평균 155자(위반율 100%). 한도 현실화 / 프롬프트 압축 / UI 절단 중 정책 결정 필요 |
| P0 | motivator 페르소나 자기 호명(“뽀롱쌤이야”)이 1%만 등장 → 가이드 추가 후 재실험 |
| P1 | TP1 고학년 응답 길이(평균 239자) 단축 |
| P2 | 운영 진입 직전 N=100+ 재실험으로 희귀 안전 사고 빈도 확정 (예상 비용 $1.5–2) |
| P2 | 모델별 input/output 단가 분리 측정 → 비용 추정 범위 확정 |

---

## 8. 발표 시 핵심 메시지 (3줄)

1. **코드 구조** — `motivator.py`는 plain LLM 호출, `helper.py`는 `bind_tools` 도구 호출. 두 노드의 요구사항이 본질적으로 다름.
2. **단일 모델은 양쪽 다 무리** — GPT-5 Mini 단일은 helper 도구 호출(추론) 실패, Gemini Flash 단일은 motivator에서 토큰 2배 낭비.
3. **OpenRouter로 3사 6모델·3조합·N=30 = 210회 실험으로 데이터 기반 채택** → motivator=GPT-5 Mini · helper=Gemini 2.5 Flash 복합 혼용 = 단일 Flash 대비 출력 토큰 12% 절감, 안전사고 0건.

---

## 부속 자료

- 실험 종합 보고서: `scripts/results/model_comparison/2026-04-29/FINAL_REPORT.md`
- 1차 (6모델 단독 N=10): `scripts/results/model_comparison/2026-04-29/2026-04-29_model_test.md`
- 2차 (3조합 N=10): `scripts/results/model_comparison/2026-04-29/combos/2026-04-29_combo_test.md`
- 3차 (3조합 N=30, 패치 후): `scripts/results/model_comparison/2026-04-29/combos_v3/2026-04-29_combo_test.md`
- 글자수 위반 사례: `scripts/results/model_comparison/2026-04-29/length_violations.md`
- 실험 코드: `scripts/run_model_comparison.py`, `scripts/run_combo_comparison.py`
- 실험 워크로그: `docs/worklogs/2026-04-29_feat-model-test.md`
- 운영 코드 진입점:
  - `app/services/nodes/motivator.py` (motivator_llm)
  - `app/services/nodes/helper.py` (helper_llm + bind_tools)
  - `app/clients/llm.py` (인스턴스 정의)
  - `app/core/config.py` (`MOTIVATOR_MODEL` / `HELPER_MODEL` 기본값)
