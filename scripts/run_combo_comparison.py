"""
하이브리드 조합 비교 실험.

motivator(TP1·2·3·5)와 helper(TP4) 노드에 서로 다른 모델을 할당하는
3가지 조합을 동일 시나리오에 대해 실행하고 자동 지표 + 사람 평가용
보고서를 생성한다.

이번 실험에서는 글자수 한도 검사를 끈다 (사용자가 따로 검토 예정).

실행:
    uv run python scripts/run_combo_comparison.py [--iterations 10]
    uv run python scripts/run_combo_comparison.py --iterations 1 --combos A
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# run_model_comparison 가 모듈 import 시 sys.stdout 을 utf-8 로 재포장하므로
# 본 모듈에서 별도로 처리할 필요 없음.

from app.core.enums import Touchpoint
from scripts.run_model_comparison import (
    SCENARIOS,
    Scenario,
    IterResult,
    use_model,
    run_iteration,
    _percentile,
)


# ─── 조합 레지스트리 ──────────────────────────────────────────────────────────

COMBOS: list[dict] = [
    {
        "label": "A_안정",
        "summary": (
            "GPT-5.4-mini로 일상 코칭 + Gemini-2.5-flash로 문제 해설. "
            "두 노드 모두 단독 평가에서 톱이며 환각·메타 노출 0건이라 가장 안전한 조합."
        ),
        "motivator": {"transport": "openrouter", "model_id": "openai/gpt-5.4-mini"},
        "helper":    {"transport": "openrouter", "model_id": "google/gemini-2.5-flash"},
    },
    {
        "label": "B_Solar활용",
        "summary": (
            "GPT-5.4-mini로 일상 코칭 + Solar-pro3로 문제 해설. "
            "Solar-pro3는 TP4 원인선택지(send_causes 도구 호출)에서 10/10 성공으로 안정적이라는 점이 강점."
        ),
        "motivator": {"transport": "openrouter", "model_id": "openai/gpt-5.4-mini"},
        "helper":    {"transport": "openrouter", "model_id": "upstage/solar-pro-3"},
    },
    {
        "label": "C_Gemini단일",
        "summary": (
            "Gemini-2.5-flash-lite로 일상 + Gemini-2.5-flash로 해설. "
            "단일 벤더 운영으로 단가·연동 단순화. lite 사용으로 비용 절감 기대."
        ),
        "motivator": {"transport": "openrouter", "model_id": "google/gemini-2.5-flash-lite"},
        "helper":    {"transport": "openrouter", "model_id": "google/gemini-2.5-flash"},
    },
]


def is_helper_scenario(scenario: Scenario) -> bool:
    return scenario.touchpoint == Touchpoint.TP4


# ─── 한 조합 실행 ────────────────────────────────────────────────────────────

def run_combo(combo: dict, iterations: int, temperature: float) -> dict[str, list[IterResult]]:
    per_scenario: dict[str, list[IterResult]] = {}

    for scenario in SCENARIOS:
        node_role = "helper" if is_helper_scenario(scenario) else "motivator"
        cfg = combo[node_role]
        iters: list[IterResult] = []
        try:
            with use_model(cfg["transport"], cfg["model_id"], temperature=temperature, target=node_role):
                for k in range(1, iterations + 1):
                    it = run_iteration(scenario, k)
                    iters.append(it)
                    flag = "OK " if it.success else "ERR"
                    preview = (it.text[:60] if it.text else it.error).replace("\n", " ")
                    print(f"  [{flag}] [{node_role:9}] {scenario.label} #{k}: {preview}")
        except Exception as exc:
            print(f"  [시나리오 오류] {scenario.label}: {exc}")
            traceback.print_exc()
        per_scenario[scenario.label] = iters

    return per_scenario


# ─── 집계 (글자수 OK 제외) ────────────────────────────────────────────────────

def aggregate_no_length(model_iters: list[IterResult]) -> dict:
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

def write_raw_per_combo(out_dir: Path, combo: dict, scenario_to_iters: dict[str, list[IterResult]]) -> Path:
    label = combo["label"]
    path = out_dir / "raw" / f"{label}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    L: list[str] = [
        f"# {label} — 원본 출력",
        "",
        f"**구성 의도**: {combo['summary']}",
        "",
        f"- motivator (TP1·2·3·5): `{combo['motivator']['model_id']}` ({combo['motivator']['transport']})",
        f"- helper (TP4): `{combo['helper']['model_id']}` ({combo['helper']['transport']})",
        f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "_글자수 한도 OK 표기는 이 보고서에서 생략 (별도 검토 예정)._",
        "",
    ]

    for scenario_label, iters in scenario_to_iters.items():
        node_role = "helper" if "TP4" in scenario_label else "motivator"
        L.append(f"## {scenario_label} · *{node_role}*")
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
                f"- 자동 지표: 글자 {ev['char_count']} · 페르소나={ev['has_persona_keyword']} · "
                f"시그니처={ev['has_signature']} · 금기={len(ev['forbidden_hits'])} · 영어누수={ev['english_leak_count']}"
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


def write_main_report(out_dir: Path, iterations: int, combos: list[dict], results_by_combo: dict[str, dict]) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    path = out_dir / f"{today}_combo_test.md"

    aggregates: dict[str, dict] = {}
    for combo in combos:
        label = combo["label"]
        all_iters: list[IterResult] = []
        for iters in results_by_combo[label].values():
            all_iters.extend(iters)
        aggregates[label] = aggregate_no_length(all_iters)

    L: list[str] = [
        "# 하이브리드 조합 비교 실험",
        "",
        f"- 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 조합 수: {len(combos)} · 시나리오 수: {len(SCENARIOS)} · 조합·시나리오당 반복: {iterations}",
        "- 평가자: Claude Code (Opus 4.7)",
        "- 글자수 한도 게이트는 이번 실험에서 제외함 (별도 검토 예정).",
        "",
        "## 조합 정의",
        "",
        "| 라벨 | motivator (TP1·2·3·5) | helper (TP4) | 설계 의도 |",
        "|---|---|---|---|",
    ]
    for combo in combos:
        L.append(
            f"| {combo['label']} | `{combo['motivator']['model_id']}` | "
            f"`{combo['helper']['model_id']}` | {combo['summary']} |"
        )

    L.extend([
        "",
        "## 1. 자동 게이트 (글자수 제외)",
        "",
        "| 조합 | 성공 | 페르소나 노출 | 시그니처 | 금기어 합 | 영어 누수 합 |",
        "|---|---|---|---|---|---|",
    ])
    for combo in combos:
        agg = aggregates[combo["label"]]
        if agg.get("n_success", 0) == 0:
            L.append(f"| {combo['label']} | 0/{agg['n_total']} | – | – | – | – |")
            continue
        L.append(
            f"| {combo['label']} | {agg['n_success']}/{agg['n_total']} "
            f"| {agg['persona_rate']*100:.0f}% "
            f"| {agg['signature_rate']*100:.0f}% "
            f"| {agg['forbidden_total']} "
            f"| {agg['english_leak_total']} |"
        )

    L.extend([
        "",
        "## 2. 운영 지표",
        "",
        "| 조합 | graph p50 | graph p95 | LLM 누적 평균 | 입력 토큰 평균 | 출력 토큰 평균 | 글자수 σ |",
        "|---|---|---|---|---|---|---|",
    ])
    for combo in combos:
        agg = aggregates[combo["label"]]
        if agg.get("n_success", 0) == 0:
            L.append(f"| {combo['label']} | – | – | – | – | – | – |")
            continue
        L.append(
            f"| {combo['label']} "
            f"| {agg['graph_p50_ms']:.0f} ms "
            f"| {agg['graph_p95_ms']:.0f} ms "
            f"| {agg['llm_latency_mean_ms']:.0f} ms "
            f"| {agg['tokens_in_mean']:.0f} "
            f"| {agg['tokens_out_mean']:.0f} "
            f"| {agg['char_stdev']:.1f} |"
        )

    L.extend([
        "",
        "비용은 `토큰 평균 × OpenRouter 단가`로 별도 산정. 조합 운영 시 motivator/helper 각각 다른 단가가 적용됨에 주의.",
        "",
        "## 3. 인간 평가 (Claude 채움)",
        "",
        "✓ = 합격 / △ = 애매 / ✗ = 부적합. 메모는 raw 인용 기반.",
        "",
        "| 시나리오 | 조합 | 코칭 | 톤 | 페르소나 | TP 의도 | 안전 | 메모 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for scenario in SCENARIOS:
        for combo in combos:
            L.append(f"| {scenario.label} | {combo['label']} |  |  |  |  |  |  |")

    L.extend([
        "",
        "## 4. 시나리오별 종합 순위",
        "",
        "| 시나리오 | 1위 | 2위 | 3위 | 비고 |",
        "|---|---|---|---|---|",
    ])
    for scenario in SCENARIOS:
        L.append(f"| {scenario.label} |  |  |  |  |")

    L.extend([
        "",
        "## 5. 최종 추천",
        "",
        "- 운영 1순위: ",
        "- 운영 2순위 (대안): ",
        "- 비추천: ",
        "",
        "## 6. 한계 및 다음 단계",
        "",
        f"- 회차 N={iterations}",
        "- 글자수 한도 미평가 — 별도 검토 후 통합 필요",
        "- 평가자 1인 (Claude)",
        "",
        "## 7. 원본 출력",
        "",
    ])
    for combo in combos:
        L.append(f"- [{combo['label']}](raw/{combo['label']}.md)")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")
    return path


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--combos", type=str, default="",
                        help="실험할 조합 라벨(콤마 구분, 비우면 전체). 예: A_안정,B_Solar활용")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--out-suffix", type=str, default="combos",
                        help="결과 디렉토리 이름 (기본 'combos'). 재실험 분리용 (예: 'combos_v3').")
    args = parser.parse_args()

    selected = COMBOS
    if args.combos:
        wanted = {x.strip() for x in args.combos.split(",") if x.strip()}
        # prefix 매칭 허용 (A → A_안정)
        selected = [c for c in COMBOS if any(c["label"].startswith(w) or c["label"] == w for w in wanted)]
        if not selected:
            print(f"[오류] --combos 와 매칭되는 조합 없음: {args.combos}")
            sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "scripts" / "results" / "model_comparison" / today / args.out_suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)

    motivator_count = sum(1 for s in SCENARIOS if not is_helper_scenario(s))
    helper_count = sum(1 for s in SCENARIOS if is_helper_scenario(s))

    print(f"\n{'='*72}")
    print(f"  하이브리드 조합 비교 실험")
    print(f"  조합 {len(selected)} × 시나리오 {len(SCENARIOS)} × 반복 {args.iterations}")
    print(f"  (motivator 시나리오 {motivator_count}개 + helper 시나리오 {helper_count}개)")
    print(f"  총 호출 (TP4 워밍업 제외): {len(selected) * len(SCENARIOS) * args.iterations}")
    print(f"  출력: {out_dir}")
    print(f"{'='*72}")

    results_by_combo: dict[str, dict] = {}
    for combo in selected:
        label = combo["label"]
        print(f"\n▶ {label}")
        print(f"  motivator: {combo['motivator']['transport']} · {combo['motivator']['model_id']}")
        print(f"  helper:    {combo['helper']['transport']} · {combo['helper']['model_id']}")

        per_scenario = run_combo(combo, args.iterations, args.temperature)
        write_raw_per_combo(out_dir, combo, per_scenario)
        results_by_combo[label] = per_scenario

    main_path = write_main_report(out_dir, args.iterations, selected, results_by_combo)

    print(f"\n{'='*72}")
    print(f"  완료")
    print(f"  메인 리포트: {main_path}")
    print(f"  원본:        {out_dir / 'raw'}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
