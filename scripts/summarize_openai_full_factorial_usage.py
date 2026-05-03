#!/usr/bin/env python3
"""
Summarize Layer 07.1 full factorial OpenAI usage.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASELINE_CONDITION = "en_sys_en_in_en_out"

METRICS = [
    "input_tokens",
    "visible_output_tokens",
    "hidden_reasoning_tokens",
    "output_tokens_total",
    "total_tokens",
    "output_chars",
    "output_words",
    "reasoning_to_visible_output",
    "total_to_input",
]


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
    values = sorted(values)
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def summarize_group(rows: list[dict]) -> dict:
    out = {"n_runs": len(rows)}
    for metric in METRICS:
        values = [to_float(row.get(metric)) for row in rows]
        values = [v for v in values if v is not None]
        if not values:
            continue
        out[f"median_{metric}"] = round(statistics.median(values), 6)
        out[f"p25_{metric}"] = round(percentile(values, 0.25), 6)
        out[f"p75_{metric}"] = round(percentile(values, 0.75), 6)
        out[f"min_{metric}"] = round(min(values), 6)
        out[f"max_{metric}"] = round(max(values), 6)
    return out


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


def build_summary(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = (
            row["provider"],
            row["model"],
            row["sample_id"],
            row["mode"],
            row["condition"],
            row["system_language"],
            row["input_language"],
            row["output_language"],
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
        }
        row.update(summarize_group(group_rows))
        out.append(row)

    return out


def build_ratios(summary_rows: list[dict]) -> list[dict]:
    groups = defaultdict(dict)
    for row in summary_rows:
        key = (row["provider"], row["model"], row["sample_id"], row["mode"])
        groups[key][row["condition"]] = row

    out_rows = []

    for key, conditions in sorted(groups.items()):
        baseline = conditions.get(BASELINE_CONDITION)
        if not baseline:
            continue

        for condition, row in sorted(conditions.items()):
            out = {
                "provider": row["provider"],
                "model": row["model"],
                "sample_id": row["sample_id"],
                "mode": row["mode"],
                "condition": condition,
                "baseline_condition": BASELINE_CONDITION,
                "system_language": row["system_language"],
                "input_language": row["input_language"],
                "output_language": row["output_language"],
                "n_runs": row["n_runs"],
            }

            for metric in METRICS:
                b = to_float(baseline.get(f"median_{metric}"))
                c = to_float(row.get(f"median_{metric}"))
                out[f"{metric}_baseline"] = "" if b is None else b
                out[f"{metric}_condition"] = "" if c is None else c
                out[f"{metric}_ratio"] = round(c / b, 6) if b not in (None, 0) and c is not None else ""

            out_rows.append(out)

    return out_rows


def fmt(value) -> str:
    if value in ("", None):
        return "n/a"
    return f"{float(value):.3f}x"


def write_markdown(path: Path, summary_rows: list[dict], ratio_rows: list[dict]) -> None:
    lines = []

    lines.append("# Layer 07.1 — Full factorial OpenAI usage summary")
    lines.append("")
    lines.append("Baseline: `en_sys_en_in_en_out`.")
    lines.append("")
    lines.append("## Ratios vs baseline")
    lines.append("")
    lines.append("| Condition | System | Input | Output | Input | Visible output | Reasoning | Output total | Total |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|")

    condition_order = [
        "en_sys_en_in_en_out",
        "ru_sys_en_in_en_out",
        "en_sys_ru_in_en_out",
        "en_sys_en_in_ru_out",
        "ru_sys_ru_in_en_out",
        "ru_sys_en_in_ru_out",
        "en_sys_ru_in_ru_out",
        "ru_sys_ru_in_ru_out",
    ]

    ratio_rows_sorted = sorted(
        ratio_rows,
        key=lambda r: condition_order.index(r["condition"]) if r["condition"] in condition_order else 99,
    )

    for row in ratio_rows_sorted:
        lines.append(
            f"| {row['condition']} | {row['system_language']} | {row['input_language']} | {row['output_language']} | "
            f"{fmt(row.get('input_tokens_ratio'))} | "
            f"{fmt(row.get('visible_output_tokens_ratio'))} | "
            f"{fmt(row.get('hidden_reasoning_tokens_ratio'))} | "
            f"{fmt(row.get('output_tokens_total_ratio'))} | "
            f"{fmt(row.get('total_tokens_ratio'))} |"
        )

    lines.append("")
    lines.append("## Absolute medians and p25/p75")
    lines.append("")
    lines.append("| Condition | Runs | Input med | Output med | Reasoning med | Output total med | Total med | Reasoning p25-p75 | Total p25-p75 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    summary_rows_sorted = sorted(
        summary_rows,
        key=lambda r: condition_order.index(r["condition"]) if r["condition"] in condition_order else 99,
    )

    for row in summary_rows_sorted:
        lines.append(
            f"| {row['condition']} | {row['n_runs']} | "
            f"{row.get('median_input_tokens','')} | "
            f"{row.get('median_visible_output_tokens','')} | "
            f"{row.get('median_hidden_reasoning_tokens','')} | "
            f"{row.get('median_output_tokens_total','')} | "
            f"{row.get('median_total_tokens','')} | "
            f"{row.get('p25_hidden_reasoning_tokens','')}-{row.get('p75_hidden_reasoning_tokens','')} | "
            f"{row.get('p25_total_tokens','')}-{row.get('p75_total_tokens','')} |"
        )

    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- If only `ru_sys_ru_in_ru_out` is high, it suggests a triple interaction.")
    lines.append("- If one double-RU condition is high, it identifies a likely interaction pair.")
    lines.append("- This experiment measures observable usage, not the language of hidden reasoning.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default="results/openai_full_factorial_usage_runs.csv")
    parser.add_argument("--summary-output", default="results/openai_full_factorial_summary.csv")
    parser.add_argument("--ratios-output", default="results/openai_full_factorial_ratios.csv")
    parser.add_argument("--md-output", default="results/openai_full_factorial_summary.md")
    parser.add_argument("--metadata-output", default="results/openai_full_factorial_summary_metadata.json")
    args = parser.parse_args()

    rows = read_csv(Path(args.runs))
    if not rows:
        raise SystemExit(f"ERROR: no rows found in {args.runs}")

    summary_rows = build_summary(rows)
    ratio_rows = build_ratios(summary_rows)

    write_csv(Path(args.summary_output), summary_rows)
    write_csv(Path(args.ratios_output), ratio_rows)
    write_markdown(Path(args.md_output), summary_rows, ratio_rows)

    metadata = {
        "layer": "07_1_full_factorial_openai_usage_summary",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_runs": args.runs,
        "outputs": {
            "summary": args.summary_output,
            "ratios": args.ratios_output,
            "markdown": args.md_output,
        },
        "baseline_condition": BASELINE_CONDITION,
        "note": "Summarizes full-factorial OpenAI language-conditioned usage.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved summary: {args.summary_output}")
    print(f"Saved ratios: {args.ratios_output}")
    print(f"Saved markdown: {args.md_output}")
    print()
    print("## Ratios vs baseline")
    print("| Condition | System | Input | Output | Input | Visible output | Reasoning | Output total | Total |")
    print("|---|---|---|---|---:|---:|---:|---:|---:|")

    condition_order = [
        "en_sys_en_in_en_out",
        "ru_sys_en_in_en_out",
        "en_sys_ru_in_en_out",
        "en_sys_en_in_ru_out",
        "ru_sys_ru_in_en_out",
        "ru_sys_en_in_ru_out",
        "en_sys_ru_in_ru_out",
        "ru_sys_ru_in_ru_out",
    ]
    ratio_rows_sorted = sorted(
        ratio_rows,
        key=lambda r: condition_order.index(r["condition"]) if r["condition"] in condition_order else 99,
    )
    for row in ratio_rows_sorted:
        print(
            f"| {row['condition']} | {row['system_language']} | {row['input_language']} | {row['output_language']} | "
            f"{fmt(row.get('input_tokens_ratio'))} | "
            f"{fmt(row.get('visible_output_tokens_ratio'))} | "
            f"{fmt(row.get('hidden_reasoning_tokens_ratio'))} | "
            f"{fmt(row.get('output_tokens_total_ratio'))} | "
            f"{fmt(row.get('total_tokens_ratio'))} |"
        )

    print()
    print("## Absolute medians and p25/p75")
    print("| Condition | Runs | Input med | Output med | Reasoning med | Output total med | Total med | Reasoning p25-p75 | Total p25-p75 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    summary_rows_sorted = sorted(
        summary_rows,
        key=lambda r: condition_order.index(r["condition"]) if r["condition"] in condition_order else 99,
    )
    for row in summary_rows_sorted:
        print(
            f"| {row['condition']} | {row['n_runs']} | "
            f"{row.get('median_input_tokens','')} | "
            f"{row.get('median_visible_output_tokens','')} | "
            f"{row.get('median_hidden_reasoning_tokens','')} | "
            f"{row.get('median_output_tokens_total','')} | "
            f"{row.get('median_total_tokens','')} | "
            f"{row.get('p25_hidden_reasoning_tokens','')}-{row.get('p75_hidden_reasoning_tokens','')} | "
            f"{row.get('p25_total_tokens','')}-{row.get('p75_total_tokens','')} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
