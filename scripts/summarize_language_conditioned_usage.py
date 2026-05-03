#!/usr/bin/env python3
"""
Summarize Layer 07 language-conditioned usage.

Inputs:
- results/openai_language_conditioned_usage_runs.csv
- results/gemini_language_conditioned_usage_runs.csv
- results/claude_language_conditioned_usage_runs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


NUMERIC_METRICS = [
    "input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
    "visible_output_tokens",
    "hidden_reasoning_tokens",
    "hidden_thinking_tokens",
    "output_tokens_total",
    "total_tokens",
    "output_chars",
    "output_words",
    "reasoning_to_visible_output",
    "thinking_to_visible_output",
    "total_to_input",
]


BASELINE_CONDITION = "en_sys_en_in_en_out"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def summarize_values(rows: list[dict], metric: str) -> dict:
    values = [to_float(row.get(metric)) for row in rows]
    values = [v for v in values if v is not None]
    if not values:
        return {}
    return {
        f"median_{metric}": round(statistics.median(values), 6),
        f"p25_{metric}": round(percentile(values, 0.25), 6),
        f"p75_{metric}": round(percentile(values, 0.75), 6),
        f"min_{metric}": round(min(values), 6),
        f"max_{metric}": round(max(values), 6),
    }


def build_summary(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = (
            row.get("provider", ""),
            row.get("model", ""),
            row.get("sample_id", ""),
            row.get("mode", ""),
            row.get("condition", ""),
            row.get("system_language", ""),
            row.get("input_language", ""),
            row.get("output_language", ""),
        )
        groups[key].append(row)

    out = []
    for key, group_rows in sorted(groups.items()):
        provider, model, sample_id, mode, condition, system_language, input_language, output_language = key
        row = {
            "provider": provider,
            "model": model,
            "sample_id": sample_id,
            "mode": mode,
            "condition": condition,
            "system_language": system_language,
            "input_language": input_language,
            "output_language": output_language,
            "n_runs": len(group_rows),
        }
        for metric in NUMERIC_METRICS:
            row.update(summarize_values(group_rows, metric))
        out.append(row)
    return out


def build_condition_ratios(summary_rows: list[dict]) -> list[dict]:
    groups = defaultdict(dict)
    for row in summary_rows:
        key = (row["provider"], row["model"], row["sample_id"], row["mode"])
        groups[key][row["condition"]] = row

    ratio_rows = []
    for key, conditions in sorted(groups.items()):
        provider, model, sample_id, mode = key
        baseline = conditions.get(BASELINE_CONDITION)
        if not baseline:
            continue

        for condition, row in sorted(conditions.items()):
            out = {
                "provider": provider,
                "model": model,
                "sample_id": sample_id,
                "mode": mode,
                "condition": condition,
                "baseline_condition": BASELINE_CONDITION,
                "system_language": row.get("system_language", ""),
                "input_language": row.get("input_language", ""),
                "output_language": row.get("output_language", ""),
                "n_runs": row.get("n_runs", ""),
            }

            for metric in NUMERIC_METRICS:
                b = to_float(baseline.get(f"median_{metric}"))
                c = to_float(row.get(f"median_{metric}"))
                out[f"{metric}_baseline"] = "" if b is None else b
                out[f"{metric}_condition"] = "" if c is None else c
                out[f"{metric}_ratio_vs_baseline"] = round(c / b, 6) if b not in (None, 0) and c is not None else ""

            ratio_rows.append(out)

    return ratio_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt_ratio(value) -> str:
    if value in ("", None):
        return "n/a"
    return f"{float(value):.3f}x"


def write_markdown(path: Path, ratio_rows: list[dict], summary_rows: list[dict]) -> None:
    lines = []
    lines.append("# Layer 07 — Language-conditioned generation usage summary")
    lines.append("")
    lines.append("## Ratios vs baseline")
    lines.append("")
    lines.append("Baseline condition: `en_sys_en_in_en_out`.")
    lines.append("")
    lines.append("| Provider | Model | Sample | Mode | Condition | Input | Visible output | Reasoning | Thinking | Output total | Total |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|")

    for row in ratio_rows:
        lines.append(
            f"| {row['provider']} | {row['model']} | {row['sample_id']} | {row['mode']} | {row['condition']} | "
            f"{fmt_ratio(row.get('input_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('visible_output_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('hidden_reasoning_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('hidden_thinking_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('output_tokens_total_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('total_tokens_ratio_vs_baseline'))} |"
        )

    lines.append("")
    lines.append("## Median absolute usage")
    lines.append("")
    lines.append("| Provider | Model | Sample | Mode | Condition | Runs | Input | Visible output | Reasoning | Thinking | Output total | Total |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| {row['provider']} | {row['model']} | {row['sample_id']} | {row['mode']} | {row['condition']} | "
            f"{row.get('n_runs','')} | "
            f"{row.get('median_input_tokens','')} | "
            f"{row.get('median_visible_output_tokens','')} | "
            f"{row.get('median_hidden_reasoning_tokens','')} | "
            f"{row.get('median_hidden_thinking_tokens','')} | "
            f"{row.get('median_output_tokens_total','')} | "
            f"{row.get('median_total_tokens','')} |"
        )

    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("")
    lines.append("- This is a real generation usage scenario, not pure tokenization.")
    lines.append("- Baseline is EN system + EN input + EN output.")
    lines.append("- Fixed-output mode should keep visible output almost stable.")
    lines.append("- Controlled-summary mode measures practical output usage.")
    lines.append("- Hidden reasoning/thinking language is not observable through API.")
    lines.append("- Claude hidden reasoning is not exposed separately in this script.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai-runs", default="results/openai_language_conditioned_usage_runs.csv")
    parser.add_argument("--gemini-runs", default="results/gemini_language_conditioned_usage_runs.csv")
    parser.add_argument("--claude-runs", default="results/claude_language_conditioned_usage_runs.csv")
    parser.add_argument("--summary-output", default="results/language_conditioned_usage_summary.csv")
    parser.add_argument("--ratios-output", default="results/language_conditioned_usage_condition_ratios.csv")
    parser.add_argument("--md-output", default="results/language_conditioned_usage_summary.md")
    parser.add_argument("--metadata-output", default="results/language_conditioned_usage_summary_metadata.json")
    args = parser.parse_args()

    rows = []
    for p in [args.openai_runs, args.gemini_runs, args.claude_runs]:
        rows.extend(read_csv(Path(p)))

    if not rows:
        raise SystemExit("ERROR: no run rows found.")

    summary_rows = build_summary(rows)
    ratio_rows = build_condition_ratios(summary_rows)

    write_csv(Path(args.summary_output), summary_rows)
    write_csv(Path(args.ratios_output), ratio_rows)
    write_markdown(Path(args.md_output), ratio_rows, summary_rows)

    metadata = {
        "layer": "07_language_conditioned_usage_summary",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "openai": args.openai_runs,
            "gemini": args.gemini_runs,
            "claude": args.claude_runs,
        },
        "outputs": {
            "summary": args.summary_output,
            "ratios": args.ratios_output,
            "markdown": args.md_output,
        },
        "baseline_condition": BASELINE_CONDITION,
        "note": "Summarizes language-conditioned real generation usage. Not a pure tokenizer experiment.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved summary: {args.summary_output}")
    print(f"Saved ratios: {args.ratios_output}")
    print(f"Saved markdown: {args.md_output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("## Ratios vs baseline")
    print("| Provider | Model | Sample | Mode | Condition | Input | Visible output | Reasoning | Thinking | Output total | Total |")
    print("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for row in ratio_rows:
        print(
            f"| {row['provider']} | {row['model']} | {row['sample_id']} | {row['mode']} | {row['condition']} | "
            f"{fmt_ratio(row.get('input_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('visible_output_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('hidden_reasoning_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('hidden_thinking_tokens_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('output_tokens_total_ratio_vs_baseline'))} | "
            f"{fmt_ratio(row.get('total_tokens_ratio_vs_baseline'))} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
