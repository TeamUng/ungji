"""
글자수 위반 사례를 시나리오별로 정리한 마크다운 보고서를 생성한다.

scripts/results/model_comparison/<날짜>/raw/<모델>.md 들을 파싱해서
시나리오별 [최단 응답 1건 + 최장 응답 3건] + 모델별 평균/최대를 한 페이지에 모은다.

실행:
    uv run python scripts/summarize_length_violations.py [--date 2026-04-29]
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# 시나리오별 한도 (현재 personas.py 와 동일)
SCENARIO_LIMITS = {
    "TP1_뽀롱쌤_인사_저학년_불성실":   (1, 60),
    "TP1_뽀롱쌤_인사_고학년_성실":     (60, 150),
    "TP2_단원완료_피드백_저학년":      (1, 60),
    "TP3_이탈방지_저학년_불성실":      (1, 60),
    "TP4_막힘_원인선택지_고학년":      (60, 150),
    "TP4_막힘_코칭응답_고학년":        (60, 150),
    "TP5_학습종료_피드백_저학년":      (1, 60),
}

ITER_RE = re.compile(
    r"### (\d+)회차\s*\n\s*\n"
    r"- 메타:[^\n]*\n"
    r"- 지연:[^\n]*\n"
    r"- 자동 지표: 글자 (\d+) · 길이OK=(True|False)[^\n]*\n"
    r"\s*\n\*\*응답\*\*\s*\n\s*\n"
    r"((?:> [^\n]*\n)+)",
    re.MULTILINE,
)


def parse_raw(path: Path) -> list[dict]:
    """한 raw 파일에서 (시나리오, 회차, 글자수, 응답텍스트) 추출."""
    text = path.read_text(encoding="utf-8")
    out: list[dict] = []

    sections = re.split(r"^## (TP[^\n]+)$", text, flags=re.MULTILINE)
    # sections: [pre, scenario, body, scenario, body, ...]
    for i in range(1, len(sections), 2):
        scenario = sections[i].strip()
        body = sections[i + 1]
        for m in ITER_RE.finditer(body):
            iter_num = int(m.group(1))
            chars = int(m.group(2))
            length_ok = m.group(3) == "True"
            response = m.group(4)
            response = "\n".join(line[2:] if line.startswith("> ") else line for line in response.splitlines()).strip()
            out.append({
                "scenario": scenario,
                "iteration": iter_num,
                "chars": chars,
                "length_ok": length_ok,
                "response": response,
                "model": path.stem,
            })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-04-29")
    args = parser.parse_args()

    raw_dir = ROOT / "scripts" / "results" / "model_comparison" / args.date / "raw"
    if not raw_dir.exists():
        print(f"[오류] {raw_dir} 없음")
        sys.exit(1)

    rows: list[dict] = []
    for f in sorted(raw_dir.glob("*.md")):
        rows.extend(parse_raw(f))

    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_scenario[r["scenario"]].append(r)

    out_lines: list[str] = [
        "# 글자수 위반 사례 정리",
        "",
        f"실험 날짜: {args.date} · 총 {len(rows)} 응답 분석.",
        "한도는 페르소나 톤 가이드 기준. 각 시나리오별로 **가장 짧은 응답 1건**과 **가장 긴 응답 3건**의 실제 텍스트를 보여줍니다.",
        "",
    ]

    for scenario in SCENARIO_LIMITS:
        scenario_rows = by_scenario.get(scenario, [])
        if not scenario_rows:
            continue
        lo, hi = SCENARIO_LIMITS[scenario]

        violations = [r for r in scenario_rows if not r["length_ok"]]
        all_chars = [r["chars"] for r in scenario_rows]
        avg = sum(all_chars) / len(all_chars)
        violation_rate = len(violations) / len(scenario_rows) * 100

        # 모델별 평균
        per_model: dict[str, list[int]] = defaultdict(list)
        for r in scenario_rows:
            per_model[r["model"]].append(r["chars"])

        out_lines.extend([
            f"## {scenario}",
            "",
            f"**한도**: {lo}~{hi}자 · **평균**: {avg:.0f}자 · **위반율**: "
            f"{len(violations)}/{len(scenario_rows)} ({violation_rate:.0f}%)",
            "",
            "### 모델별 평균 글자수",
            "",
            "| 모델 | 평균 | 최소 | 최대 | 한도 초과 배수(평균/한도상한) |",
            "|---|---|---|---|---|",
        ])
        for model, chars in sorted(per_model.items()):
            m_avg = sum(chars) / len(chars)
            ratio = m_avg / hi
            out_lines.append(
                f"| {model} | {m_avg:.0f} | {min(chars)} | {max(chars)} | ×{ratio:.1f} |"
            )
        out_lines.append("")

        # 최단 응답
        sorted_rows = sorted(scenario_rows, key=lambda r: r["chars"])
        shortest = sorted_rows[0]
        out_lines.extend([
            "### 최단 응답 (참고용)",
            "",
            f"**{shortest['model']} · {shortest['iteration']}회차 · {shortest['chars']}자**"
            + (" ✓ 한도 OK" if shortest["length_ok"] else f" ✗ 한도 초과 (한도 {lo}~{hi})"),
            "",
        ])
        for line in shortest["response"].splitlines():
            out_lines.append(f"> {line}")
        out_lines.append("")

        # 최장 응답 3개
        out_lines.extend([
            "### 최장 응답 TOP 3",
            "",
        ])
        for r in sorted_rows[-3:][::-1]:
            out_lines.append(
                f"**{r['model']} · {r['iteration']}회차 · {r['chars']}자** "
                f"(한도 상한 {hi}의 ×{r['chars']/hi:.1f}배)"
            )
            out_lines.append("")
            for line in r["response"].splitlines():
                out_lines.append(f"> {line}")
            out_lines.append("")

        out_lines.append("---")
        out_lines.append("")

    out_path = ROOT / "scripts" / "results" / "model_comparison" / args.date / "length_violations.md"
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"생성: {out_path}")


if __name__ == "__main__":
    main()
