# 가드레일 미들웨어 — 요약

## 접근 방식

핵심 문제는 초등학생이 두 방향에서 보호받아야 한다는 점입니다. 하나는 학생이 보내는 메시지(부적절한 언어, 탈옥 시도, 주제 이탈 요청), 다른 하나는 LLM이 돌려보내는 응답(잘못된 말투, 지나치게 어려운 표현, 답을 직접 알려주는 경우)입니다. 가드레일은 학생과 LLM 사이에서 각 라우트 핸들러 안의 두 명시적 단계로 동작합니다. 보이지 않는 HTTP 미들웨어가 아니기 때문에 엔드포인트별로 추가, 제거, 확인이 쉽습니다.

**입력 단계 (LLM 호출 전):** `SafetyCheck`가 두 단계로 실행됩니다. 1단계는 API 호출 없이 정규식으로 빠르게 검사하여 알려진 욕설과 탈옥 패턴을 즉시 차단합니다. 걸리는 것이 없으면 2단계에서 Solar Pro를 한 번 호출해 콘텐츠 안전성, 프롬프트 인젝션, 주제 적합성을 동시에 판단합니다. 하나라도 실패하면 메시지를 차단하고 학년에 맞는 한국어 안내 문구를 학생에게 반환합니다.

**출력 단계 (LLM 호출 후):** `ResponseEvaluator`가 Solar Pro를 한 번 호출해 학년 적합성, 말투, 응답 품질을 검사합니다. 실패 시 경고 로그만 남기고 응답은 항상 학생에게 전달합니다. 막힌 아이에게는 조금 부족한 답변이라도 침묵보다 낫기 때문입니다.

주제 적합성 판단 기준은 두 가지 터치포인트 프로파일로 조정합니다. **라이트헤어티드** (`home_screen`, `after_all_tasks`, `exit`)는 가벼운 대화를 허용하고, **스터디 포커스드** (`during_study`, `after_task`)는 학습 관련 메시지만 허용합니다.

---

## 수정 위치 안내

| 변경하고 싶은 항목 | 파일 | 수정 대상 |
|---|---|---|
| 차단 시 학생에게 보이는 메시지 | `app/guardrails/pipeline.py` | `_BLOCKED_MESSAGES` 딕셔너리 — 학년 그룹별 (`lower`, `middle`, `upper`) |
| 욕설·부적절 표현 목록 | `app/guardrails/strategies/rule_based.py` | `_PROFANITY_PATTERNS` 리스트 |
| 프롬프트 인젝션 패턴 | `app/guardrails/strategies/rule_based.py` | `_INJECTION_PATTERNS` 리스트 |
| 주제 판단 키워드 (빠른 휴리스틱) | `app/guardrails/strategies/rule_based.py` | `_STUDY_KEYWORDS`, `_CLEARLY_OFF_TOPIC` 집합 |
| 입력 LLM 판단 기준 및 허용 범위 | `app/guardrails/guards/input/safety_check.py` | `_LIGHTHEARTED_SYSTEM`, `_STUDY_FOCUSED_SYSTEM` 프롬프트 문자열 |
| 출력 LLM 판단 기준 | `app/guardrails/guards/output/response_evaluator.py` | `_SYSTEM_PROMPT_TEMPLATE` 문자열 |
| 터치포인트 프로파일 분류 기준 | `app/guardrails/models.py` | `GuardrailContext.group` 프로퍼티 |
| 새로운 가드 추가 | `app/guardrails/config.py` | `build_pipeline()` 안의 `input_guards` 또는 `output_guards` 리스트에 추가 |
| 판단에 사용하는 Solar Pro 모델 변경 | `app/guardrails/strategies/llm_judge.py` | `LLMJudge.__init__`의 기본값 `model` 파라미터 |
