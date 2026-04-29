"""
모델 비교 실험 러너.

OpenRouter 6개 모델에 대해 동일 시나리오(TP1·TP2·TP3·TP4·TP5)를 반복 호출하고
자동 지표를 계산한 뒤 사람-평가용 마크다운 보고서를 생성한다.

실행:
    uv run python scripts/run_model_comparison.py
    uv run python scripts/run_model_comparison.py --iterations 3 --models gpt-5.4-mini,solar-pro2

요건:
    .env 에 OPENROUTER_API_KEY 설정.
    OpenRouter 모델 ID 가 본 파일 MODELS 리스트와 실제로 일치하는지 사전 확인.

출력:
    scripts/results/model_comparison/<YYYY-MM-DD>/
        ├── <YYYY-MM-DD>_model_test.md   # 메인 보고서 (자동 채움 + 사람 평가용 빈 표)
        └── raw/<model_label>.md          # 모델별 원본 출력 모음
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

# Windows 한글·이모지 출력
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage

import app.clients.llm as llm_module
from app.core.config import settings
from app.core.enums import GradeGroup, Touchpoint, UseCase
from app.core.logging import get_logger
from app.data.loader import load_student
from app.schemas.chat import ChatResponse
from app.services.graph import graph

logger = get_logger(__name__)


# ─── 모델 레지스트리 ──────────────────────────────────────────────────────────
# transport:
#   "openrouter" → OpenRouter 경유 (model_id 는 OpenRouter 카탈로그 ID)
#   "upstage"    → Upstage 네이티브 API 경유 (langchain_upstage.ChatUpstage)

MODELS: list[dict[str, str]] = [
    {"label": "gpt-5.4-mini",          "transport": "openrouter", "model_id": "openai/gpt-5.4-mini"},
    {"label": "gpt-5.4-nano",          "transport": "openrouter", "model_id": "openai/gpt-5.4-nano"},
    {"label": "gemini-2.5-flash",      "transport": "openrouter", "model_id": "google/gemini-2.5-flash"},
    {"label": "gemini-2.5-flash-lite", "transport": "openrouter", "model_id": "google/gemini-2.5-flash-lite"},
    {"label": "solar-pro3",            "transport": "openrouter", "model_id": "upstage/solar-pro-3"},
    {"label": "solar-pro2",            "transport": "upstage",    "model_id": "solar-pro2"},
]


# ─── 시나리오 ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Scenario:
    label: str
    student_id: str
    use_case: UseCase
    touchpoint: Touchpoint
    turn: int
    message_content: str  # "__cause__" → 학생 과목별 cause 토큰으로 치환

# PRD 케이스 1·2 학생 위주 + 양 학년 톤 차이를 보기 위해 TP1 두 학년 모두 포함.
SCENARIOS: list[Scenario] = [
    Scenario("TP1_뽀롱쌤_인사_저학년_불성실", "lower-lazy",     UseCase.TALK,     Touchpoint.TP1, 1, ""),
    Scenario("TP1_뽀롱쌤_인사_고학년_성실",   "upper-diligent", UseCase.TALK,     Touchpoint.TP1, 1, ""),
    Scenario("TP2_단원완료_피드백_저학년",    "lower-lazy",     UseCase.TALK,     Touchpoint.TP2, 1, ""),
    Scenario("TP3_이탈방지_저학년_불성실",    "lower-lazy",     UseCase.TALK,     Touchpoint.TP3, 1, ""),
    Scenario("TP4_막힘_원인선택지_고학년",    "upper-diligent", UseCase.LEARNING, Touchpoint.TP4, 1, ""),
    Scenario("TP4_막힘_코칭응답_고학년",      "upper-diligent", UseCase.LEARNING, Touchpoint.TP4, 2, "__cause__"),
    Scenario("TP5_학습종료_피드백_저학년",    "lower-lazy",     UseCase.TALK,     Touchpoint.TP5, 1, ""),
]

TP4_CAUSE_BY_SUBJECT = {"국어": "too_long", "수학": "confused_concept"}


# ─── 자동 지표 정의 ───────────────────────────────────────────────────────────

PERSONA_KEYWORDS = ["뽀롱쌤", "친구야~"]
SIGNATURE_PHRASES = ["뽀롱~", "뽀로롱?!"]
INTERNAL_NAMES_FORBIDDEN = [
    "TP1", "TP2", "TP3", "TP4", "TP5",
    "LOW_LAZY", "LOW_DILIGENT", "MID_DILIGENT", "HIGH_DILIGENT",
    "Touchpoint", "Segment", "GradeGroup",
]
ENGLISH_WORD_RE = re.compile(r"[A-Za-z]{3,}")

# 페르소나 가이드의 글자수 제한 (저 60·중 80·고 60–150).
GRADE_LENGTH_LIMITS = {
    GradeGroup.LOWER:  (1,   60),
    GradeGroup.MIDDLE: (1,   80),
    GradeGroup.UPPER:  (60, 150),
}


def evaluate_response(text: str, grade_group: GradeGroup | None) -> dict:
    if not text:
        return {
            "char_count": 0,
            "length_ok": False,
            "has_persona_keyword": False,
            "has_signature": False,
            "forbidden_hits": [],
            "english_leak_count": 0,
        }
    char_count = len(text)
    if grade_group in GRADE_LENGTH_LIMITS:
        lo, hi = GRADE_LENGTH_LIMITS[grade_group]
        length_ok = lo <= char_count <= hi
    else:
        length_ok = False
    forbidden = [
        token for token in INTERNAL_NAMES_FORBIDDEN
        if re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", text)
    ]
    return {
        "char_count": char_count,
        "length_ok": length_ok,
        "has_persona_keyword": any(kw in text for kw in PERSONA_KEYWORDS),
        "has_signature": any(sig in text for sig in SIGNATURE_PHRASES),
        "forbidden_hits": forbidden,
        "english_leak_count": len(ENGLISH_WORD_RE.findall(text)),
    }


def extract_text(response: ChatResponse | None) -> tuple[str, str]:
    """텍스트로 변환된 응답 + 메시지 타입 시퀀스 (`text|choices` 같은 형태) 반환."""
    if response is None:
        return "", ""
    parts: list[str] = []
    types: list[str] = []
    for m in response.messages:
        types.append(m.type)
        if m.type == "text":
            parts.append(m.content)
        elif m.type == "choices":
            parts.append(" / ".join(item.label for item in m.items))
        elif m.type == "hint_card":
            parts.append("\n".join(s.content for s in m.steps))
        elif m.type == "image_card":
            parts.append(m.caption)
    return "\n".join(parts), "|".join(types)


# ─── LLM 호출 메트릭 콜백 ─────────────────────────────────────────────────────

class LLMMetricsCollector(BaseCallbackHandler):
    """LangChain 콜백으로 LLM 호출별 latency·token 수집."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._stack: list[float] = []

    def on_llm_start(self, *args, **kwargs) -> None:
        self._stack.append(time.perf_counter())

    def on_chat_model_start(self, *args, **kwargs) -> None:
        self._stack.append(time.perf_counter())

    def on_llm_end(self, response, **kwargs) -> None:
        if not self._stack:
            return
        elapsed_ms = (time.perf_counter() - self._stack.pop()) * 1000

        prompt_tokens = 0
        completion_tokens = 0
        if response.llm_output:
            usage = response.llm_output.get("token_usage") or {}
            prompt_tokens = usage.get("prompt_tokens", 0) or 0
            completion_tokens = usage.get("completion_tokens", 0) or 0
        if not (prompt_tokens or completion_tokens):
            try:
                msg = response.generations[0][0].message
                meta = getattr(msg, "usage_metadata", None) or {}
                prompt_tokens = meta.get("input_tokens", 0) or 0
                completion_tokens = meta.get("output_tokens", 0) or 0
            except (AttributeError, IndexError):
                pass

        self.calls.append({
            "elapsed_ms": elapsed_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        })

    def on_llm_error(self, error, **kwargs) -> None:
        if self._stack:
            self._stack.pop()
        self.calls.append({"error": str(error)})


# ─── 모델 스왑 ────────────────────────────────────────────────────────────────

def _build_openrouter_llm(model_id: str, temperature: float):
    from langchain_openai import ChatOpenAI

    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY 가 .env 에 설정되지 않았습니다.")

    return ChatOpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model_id,
        temperature=temperature,
        timeout=60,
        max_retries=1,
        default_headers={
            "HTTP-Referer": "https://github.com/TeamUng/ungji",
            "X-Title": "ungji-model-comparison",
        },
    )


def _build_upstage_llm(model_id: str, temperature: float):
    from langchain_upstage import ChatUpstage

    api_key = settings.UPSTAGE_API_KEY
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY 가 .env 에 설정되지 않았습니다.")

    return ChatUpstage(
        api_key=api_key,
        model=model_id,
        temperature=temperature,
        timeout=60,
    )


@contextmanager
def use_model(transport: str, model_id: str, temperature: float, target: str = "both"):
    """transport 에 따라 LLM 을 만들고 `app.clients.llm` 의 어트리뷰트를 일시 교체.

    target:
      - "both": motivator_llm 과 helper_llm 둘 다 같은 모델로 교체 (단일 모델 평가)
      - "motivator": motivator_llm 만 교체
      - "helper": helper_llm 만 교체
    """
    if transport == "openrouter":
        new_llm = _build_openrouter_llm(model_id, temperature)
    elif transport == "upstage":
        new_llm = _build_upstage_llm(model_id, temperature)
    else:
        raise ValueError(f"지원하지 않는 transport: {transport}")

    targets = ("motivator_llm", "helper_llm") if target == "both" else (f"{target}_llm",)
    originals = {attr: getattr(llm_module, attr) for attr in targets}
    for attr in targets:
        setattr(llm_module, attr, new_llm)
    try:
        yield
    finally:
        for attr, orig in originals.items():
            setattr(llm_module, attr, orig)


# ─── 한 회차 실행 ─────────────────────────────────────────────────────────────

@dataclass
class IterResult:
    iteration: int
    success: bool
    error: str = ""
    text: str = ""
    message_types: str = ""
    grade_group: str = ""
    segment: str = ""
    graph_elapsed_ms: float = 0.0
    llm_calls: list[dict] = field(default_factory=list)
    eval: dict = field(default_factory=dict)


def _build_state(thread_id: str, scenario: Scenario, message: str) -> dict:
    return {
        "thread_id": thread_id,
        "student_id": scenario.student_id,
        "use_case": scenario.use_case,
        "current_touchpoint": scenario.touchpoint,
        "chat_history": [HumanMessage(content=message)] if message else [],
        "response": None,
    }


def run_iteration(scenario: Scenario, iter_num: int) -> IterResult:
    record = load_student(scenario.student_id)

    message = scenario.message_content
    if message == "__cause__":
        subject = (record["today_tasks"][0] if record["today_tasks"] else {}).get("subject", "")
        message = TP4_CAUSE_BY_SUBJECT.get(subject, "too_long")

    thread_id = f"compare-{scenario.label}-{iter_num}-{uuid.uuid4()}"
    config_base = {"configurable": {"thread_id": thread_id}}
    collector = LLMMetricsCollector()

    try:
        # TP4 turn=2 시나리오는 turn=1 (원인 선택지 생성) 을 먼저 돌려서 current_problem 을 채운다.
        # 이때 워밍업 호출은 측정 대상에서 제외 (콜백 미부착, latency 측정 X).
        if scenario.touchpoint == Touchpoint.TP4 and scenario.turn == 2:
            warmup = _build_state(thread_id, scenario, "")
            graph.invoke(warmup, config=dict(config_base))

        state = _build_state(thread_id, scenario, message)
        t0 = time.perf_counter()
        result = graph.invoke(
            state,
            config={**config_base, "callbacks": [collector]},
        )
        graph_elapsed = (time.perf_counter() - t0) * 1000

        response = result.get("response")
        text, types = extract_text(response)
        grade_group = result.get("grade_group")
        segment = result.get("segment")
        evaluation = evaluate_response(text, grade_group)

        return IterResult(
            iteration=iter_num,
            success=True,
            text=text,
            message_types=types,
            grade_group=grade_group.value if grade_group else "",
            segment=segment.value if segment else "",
            graph_elapsed_ms=graph_elapsed,
            llm_calls=collector.calls,
            eval=evaluation,
        )

    except Exception as exc:
        logger.exception(
            "model comparison iteration failed",
            extra={"scenario": scenario.label, "iter": iter_num},
        )
        return IterResult(
            iteration=iter_num,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            llm_calls=collector.calls,
        )


# ─── 모델별 집계 ──────────────────────────────────────────────────────────────

def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[k]


def aggregate(model_iters: list[IterResult]) -> dict:
    n = len(model_iters)
    successes = [it for it in model_iters if it.success]
    if not successes:
        return {"n_total": n, "n_success": 0, "success_rate": 0.0}

    char_counts = [it.eval["char_count"] for it in successes]
    in_tokens = [sum(c.get("prompt_tokens", 0) for c in it.llm_calls) for it in successes]
    out_tokens = [sum(c.get("completion_tokens", 0) for c in it.llm_calls) for it in successes]
    llm_lat = [sum(c.get("elapsed_ms", 0) for c in it.llm_calls) for it in successes]
    graph_lat = [it.graph_elapsed_ms for it in successes]

    return {
        "n_total": n,
        "n_success": len(successes),
        "success_rate": len(successes) / n,
        "char_mean": mean(char_counts),
        "char_stdev": stdev(char_counts) if len(char_counts) > 1 else 0.0,
        "length_ok_rate": mean(1 if it.eval["length_ok"] else 0 for it in successes),
        "persona_rate": mean(1 if it.eval["has_persona_keyword"] else 0 for it in successes),
        "signature_rate": mean(1 if it.eval["has_signature"] else 0 for it in successes),
        "forbidden_total": sum(len(it.eval["forbidden_hits"]) for it in successes),
        "english_leak_total": sum(it.eval["english_leak_count"] for it in successes),
        "graph_p50_ms": _percentile(graph_lat, 0.5),
        "graph_p95_ms": _percentile(graph_lat, 0.95),
        "graph_mean_ms": mean(graph_lat),
        "llm_latency_mean_ms": mean(llm_lat) if llm_lat else 0.0,
        "tokens_in_mean": mean(in_tokens) if in_tokens else 0.0,
        "tokens_out_mean": mean(out_tokens) if out_tokens else 0.0,
    }


# ─── 보고서 ───────────────────────────────────────────────────────────────────

def write_raw_per_model(
    out_dir: Path,
    model_label: str,
    transport: str,
    model_id: str,
    scenario_to_iters: dict[str, list[IterResult]],
) -> Path:
    path = out_dir / "raw" / f"{model_label}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    L: list[str] = [
        f"# {model_label} — 원본 출력",
        "",
        f"- Transport: `{transport}` · Model ID: `{model_id}`",
        f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for scenario_label, iters in scenario_to_iters.items():
        L.append(f"## {scenario_label}")
        L.append("")
        for it in iters:
            head = f"### {it.iteration}회차"
            if not it.success:
                L.append(head + " · 실패")
                L.append("")
                L.append(f"- 오류: `{it.error}`")
                L.append("")
                continue

            in_t = sum(c.get("prompt_tokens", 0) for c in it.llm_calls)
            out_t = sum(c.get("completion_tokens", 0) for c in it.llm_calls)
            llm_lat = sum(c.get("elapsed_ms", 0) for c in it.llm_calls)

            L.append(head)
            L.append("")
            L.append(
                f"- 메타: 학년={it.grade_group} · 세그먼트={it.segment} · "
                f"메시지타입=`{it.message_types}`"
            )
            L.append(
                f"- 지연: graph {it.graph_elapsed_ms:.0f} ms / LLM 누적 {llm_lat:.0f} ms · "
                f"토큰 in {in_t} / out {out_t} · LLM 호출 {len(it.llm_calls)}회"
            )
            ev = it.eval
            L.append(
                f"- 자동 지표: 글자 {ev['char_count']} · 길이OK={ev['length_ok']} · "
                f"페르소나={ev['has_persona_keyword']} · 시그니처={ev['has_signature']} · "
                f"금기={len(ev['forbidden_hits'])} · 영어누수={ev['english_leak_count']}"
            )
            L.append("")
            L.append("**응답**")
            L.append("")
            for line in it.text.splitlines():
                L.append(f"> {line}")
            if not it.text:
                L.append("> _(빈 응답)_")
            L.append("")
        L.append("")

    path.write_text("\n".join(L), encoding="utf-8")
    return path


def write_main_report(
    out_dir: Path,
    iterations: int,
    results_by_model: dict[str, list[IterResult]],
    scenarios: list[Scenario],
    model_meta: dict[str, str],
) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    path = out_dir / f"{today}_model_test.md"

    aggregates = {label: aggregate(iters) for label, iters in results_by_model.items()}

    L: list[str] = [
        "# 모델 비교 실험",
        "",
        f"- 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 모델 수: {len(results_by_model)} · 시나리오 수: {len(scenarios)} · 모델·시나리오당 반복: {iterations}",
        "- 평가자: _(작성 필요)_",
        "",
        "## 모델 목록",
        "",
        "| 라벨 | Transport | Model ID |",
        "|---|---|---|",
    ]
    for label, meta in model_meta.items():
        L.append(f"| {label} | {meta['transport']} | `{meta['model_id']}` |")

    L.extend([
        "",
        "## 1. 자동 게이트",
        "",
        "| 모델 | 성공 | 길이 OK | 페르소나 노출 | 시그니처 | 금기어 합 | 영어 누수 합 |",
        "|---|---|---|---|---|---|---|",
    ])
    for label, agg in aggregates.items():
        if agg.get("n_success", 0) == 0:
            L.append(f"| {label} | 0/{agg['n_total']} | – | – | – | – | – |")
            continue
        L.append(
            f"| {label} | {agg['n_success']}/{agg['n_total']} "
            f"| {agg['length_ok_rate']*100:.0f}% "
            f"| {agg['persona_rate']*100:.0f}% "
            f"| {agg['signature_rate']*100:.0f}% "
            f"| {agg['forbidden_total']} "
            f"| {agg['english_leak_total']} |"
        )

    L.extend([
        "",
        "## 2. 운영 지표",
        "",
        "| 모델 | graph p50 | graph p95 | LLM 누적 평균 | 입력 토큰 평균 | 출력 토큰 평균 | 글자수 σ |",
        "|---|---|---|---|---|---|---|",
    ])
    for label, agg in aggregates.items():
        if agg.get("n_success", 0) == 0:
            L.append(f"| {label} | – | – | – | – | – | – |")
            continue
        L.append(
            f"| {label} "
            f"| {agg['graph_p50_ms']:.0f} ms "
            f"| {agg['graph_p95_ms']:.0f} ms "
            f"| {agg['llm_latency_mean_ms']:.0f} ms "
            f"| {agg['tokens_in_mean']:.0f} "
            f"| {agg['tokens_out_mean']:.0f} "
            f"| {agg['char_stdev']:.1f} |"
        )

    L.extend([
        "",
        "비용은 `토큰 평균 × OpenRouter 단가`로 별도 산정. 단가표는 https://openrouter.ai/models 참조.",
        "",
        "## 3. 인간 평가 (사람이 채우기)",
        "",
        "✓ = 합격 / △ = 애매 / ✗ = 부적합. **메모는 구체 사례를 인용해 작성**.",
        "원본 출력은 `raw/<모델>.md` 참고.",
        "",
        "| 시나리오 | 모델 | 코칭 | 톤 | 페르소나 | TP 의도 | 안전 | 메모 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for scenario in scenarios:
        for label in results_by_model:
            L.append(f"| {scenario.label} | {label} |  |  |  |  |  |  |")

    L.extend([
        "",
        "## 4. 시나리오별 종합 순위 (사람이 채우기)",
        "",
        "| 시나리오 | 1위 | 2위 | 3위 | 비고 |",
        "|---|---|---|---|---|",
    ])
    for scenario in scenarios:
        L.append(f"| {scenario.label} |  |  |  |  |")

    L.extend([
        "",
        "## 5. 최종 추천 (사람이 채우기)",
        "",
        "- 운영 후보: ",
        "- 비용 절감 후보: ",
        "- 탈락: ",
        "",
        "## 6. 한계 및 다음 단계",
        "",
        f"- 회차 N={iterations} → 통계 신뢰도 제한",
        "- 인간 평가 1인 → 평가자 간 분산 미측정",
        "- 비용은 OpenRouter 단가표 별도 참조 필요",
        "- 시스템 프롬프트는 Solar Pro 계열 기준으로 튜닝되어 있어 타 모델에 불리할 가능성",
        "",
        "## 7. claude.ai 개인 플랜으로 평가하는 방법",
        "",
        "1. claude.ai 새 대화에 본 보고서 + `raw/` 폴더 안 모든 모델 파일 첨부.",
        "2. 아래 프롬프트 블록을 그대로 복사·붙여넣기.",
        "3. Claude 가 출력한 마크다운 표를 위 §3·§4·§5 의 빈 셀에 붙여넣기.",
        "",
        "Claude 컨텍스트(200k) 안에 6모델 raw 가 모두 들어가도록 설계됨.",
        "응답이 길면 모델별·시나리오별로 끊어 요청해도 됨.",
        "",
        "<details>",
        "<summary>평가 프롬프트 (복사용)</summary>",
        "",
        "````text",
        _build_judge_prompt(scenarios, list(results_by_model.keys())),
        "````",
        "",
        "</details>",
        "",
        "## 8. 원본 출력",
        "",
    ])
    for label in results_by_model:
        L.append(f"- [{label}](raw/{label}.md)")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")
    return path


def _build_judge_prompt(scenarios: list[Scenario], model_labels: list[str]) -> str:
    """claude.ai 에 붙여넣을 사람-스타일 평가 프롬프트 생성."""
    scenario_lines = "\n".join(f"  - {s.label}" for s in scenarios)
    model_lines = "\n".join(f"  - {label}" for label in model_labels)
    return f"""당신은 초등학생용 한국어 AI 학습코치 챗봇 '뽀롱쌤'의 모델 비교 평가자입니다.

## 서비스 맥락
- 대상: 초등 1~6학년. 저(1~2)·중(3~4)·고(5~6)학년 톤이 다름.
- 페르소나: 모든 학년에서 동일한 캐릭터 '뽀롱쌤'. 시그니처 표현 `뽀롱~`, `뽀로롱?!`. 호칭 fallback `친구야~`.
- 코칭 원칙: 정답 직접 노출 금지, 평가/판단 금지, 단계로 같이 도달, 격려·위로.
- TP 의도:
  - TP1: 홈 진입 인사 + 오늘 과제 추천
  - TP2: 단원 학습 완료 후 격려 + 다음 과제 안내
  - TP3: 이탈 방지 (강요 없이 작은 행동 유도)
  - TP4: 문제 막힘 → 원인 선택지 / 원인별 코칭 (정답 직접 X, teach-back)
  - TP5: 학습 종료 + 오답 복습 권유 또는 칭찬

## 평가 대상
- 모델 {len(model_labels)}종:
{model_lines}
- 시나리오 {len(scenarios)}종:
{scenario_lines}
- 첨부된 raw/<모델>.md 파일에 모델·시나리오·반복회차별 응답이 들어 있음.

## 평가 차원 (각 ✓ / △ / ✗)
1. **코칭**: 세그먼트(불성실/성실 등) 의도에 맞는 코칭 전략을 따랐는가
2. **톤**: 학년대 (저/중/고) 톤 가이드(글자수·말투)에 맞는가
3. **페르소나**: 단순 키워드 너머 캐릭터 일관성·따뜻함이 살아있는가
4. **TP 의도**: 해당 TP 의 본래 목표를 달성했는가
5. **안전**: 정답 직접 노출·평가·유해 표현 없는가

## 출력 형식

### 출력 1: 시나리오별 모델 평가 표 (§3 에 붙여넣기)

```
| 시나리오 | 모델 | 코칭 | 톤 | 페르소나 | TP 의도 | 안전 | 메모 |
|---|---|---|---|---|---|---|---|
| <시나리오> | <모델> | ✓/△/✗ | ✓/△/✗ | ✓/△/✗ | ✓/△/✗ | ✓/△/✗ | <구체 사례 인용 1줄> |
...
```

모든 (시나리오 × 모델) 조합을 채우세요. 메모는 raw 의 응답을 인용해 구체적으로.

### 출력 2: 시나리오별 종합 순위 (§4 에 붙여넣기)

```
| 시나리오 | 1위 | 2위 | 3위 | 비고 |
|---|---|---|---|---|
| <시나리오> | <모델> | <모델> | <모델> | <왜 그 순위인지 1줄> |
...
```

### 출력 3: 최종 추천 (§5 에 붙여넣기)

```
- 운영 후보: <모델> — <이유 1~2줄>
- 비용 절감 후보: <모델> — <이유>
- 탈락: <모델> — <이유>
```

## 채점 원칙
- 인상이 아닌 **인용**으로 판단할 것. 메모에는 raw 의 실제 표현을 짧게 인용.
- 10회 반복 안에서 들쭉날쭉이면 **△** 또는 **✗**.
- 한 모델만 잘하더라도 시나리오마다 별개로 평가.
- 모호하면 사용자에게 되묻지 말고 가장 합리적인 채점을 한 뒤 메모에 근거를 남길 것.
"""


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--iterations", type=int, default=10,
        help="모델·시나리오당 반복 횟수 (기본 10)",
    )
    parser.add_argument(
        "--models", type=str, default="",
        help="실험할 모델 라벨 콤마구분. 비우면 전체.",
    )
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    selected_models = MODELS
    if args.models:
        wanted = {m.strip() for m in args.models.split(",") if m.strip()}
        selected_models = [m for m in MODELS if m["label"] in wanted]
        if not selected_models:
            print(f"[오류] --models 와 일치하는 모델 없음: {args.models}")
            sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "scripts" / "results" / "model_comparison" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)

    print(f"\n{'='*72}")
    print(f"  모델 비교 실험")
    print(f"  모델 {len(selected_models)} × 시나리오 {len(SCENARIOS)} × 반복 {args.iterations}")
    print(f"  총 호출 (원인선택지 워밍업 제외): "
          f"{len(selected_models) * len(SCENARIOS) * args.iterations}")
    print(f"  출력: {out_dir}")
    print(f"{'='*72}")

    results_by_model: dict[str, list[IterResult]] = {}
    model_meta: dict[str, dict[str, str]] = {}

    for model_cfg in selected_models:
        label = model_cfg["label"]
        transport = model_cfg["transport"]
        model_id = model_cfg["model_id"]
        model_meta[label] = {"transport": transport, "model_id": model_id}
        print(f"\n▶ {label}  ({transport} · {model_id})")

        per_scenario: dict[str, list[IterResult]] = {}
        all_iters: list[IterResult] = []

        try:
            with use_model(transport, model_id, temperature=args.temperature):
                for scenario in SCENARIOS:
                    iters: list[IterResult] = []
                    for k in range(1, args.iterations + 1):
                        it = run_iteration(scenario, k)
                        iters.append(it)
                        flag = "OK " if it.success else "ERR"
                        preview = (it.text[:60] if it.text else it.error).replace("\n", " ")
                        print(f"  [{flag}] {scenario.label} #{k}: {preview}")
                    per_scenario[scenario.label] = iters
                    all_iters.extend(iters)
        except Exception as exc:
            print(f"  [모델 단위 오류] {exc}")
            traceback.print_exc()

        write_raw_per_model(out_dir, label, transport, model_id, per_scenario)
        results_by_model[label] = all_iters

    main_path = write_main_report(out_dir, args.iterations, results_by_model, SCENARIOS, model_meta)

    print(f"\n{'='*72}")
    print(f"  완료")
    print(f"  메인 리포트: {main_path}")
    print(f"  원본:        {out_dir / 'raw'}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
