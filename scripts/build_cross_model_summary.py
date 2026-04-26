#!/usr/bin/env python3
"""
Build cross-model summary tables from Layer 02-04 result CSVs.

Inputs:
- results/openai_tiktoken_counts.csv
- results/openai_current_model_input_token_counts.csv
- results/gemini_official_token_counts.csv

Outputs:
- results/cross_model_summary.csv
- results/cross_model_summary.md
- results/cross_model_summary_metadata.json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def first_rows_by_key(rows: Iterable[dict], key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict]:
    result: dict[tuple[str, ...], dict] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key not in result:
            result[key] = row
    return result


def collect_openai_tiktoken(path: Path) -> list[dict]:
    rows = read_csv(path)
    collected: list[dict] = []

    seen = set()
    for row in rows:
        sample_id = row.get("sample_id", "")
        comparison = row.get("comparison", "")
        encoding = row.get("encoding", "")

        key = (sample_id, comparison, encoding)
        if key in seen:
            continue
        seen.add(key)

        collected.append(
            {
                "sample_id": sample_id,
                "comparison": comparison,
                "source": "openai_tiktoken",
                "model_or_encoding": encoding,
                "measurement_level": "local_raw_tokenizer_count",
                "baseline_tokens": int(row["baseline_token_count"]),
                "compared_tokens": int(row["compared_token_count"]),
                "ratio": float(row["comparison_ratio"]),
                "notes": "Local tiktoken raw count; not API usage.",
            }
        )

    return collected


def collect_openai_current(path: Path, representative_model: str) -> list[dict]:
    rows = read_csv(path)
    collected: list[dict] = []

    seen = set()
    for row in rows:
        if row.get("model") != representative_model:
            continue

        sample_id = row.get("sample_id", "")
        comparison = row.get("comparison", "")
        model = row.get("model", "")

        key = (sample_id, comparison, model)
        if key in seen:
            continue
        seen.add(key)

        collected.append(
            {
                "sample_id": sample_id,
                "comparison": comparison,
                "source": "openai_current_api",
                "model_or_encoding": model,
                "measurement_level": "responses_input_token_count",
                "baseline_tokens": int(row["baseline_input_tokens"]),
                "compared_tokens": int(row["compared_input_tokens"]),
                "ratio": float(row["comparison_ratio"]),
                "notes": "OpenAI Responses input token count API; not full billable usage.",
            }
        )

    return collected


def collect_gemini(path: Path, representative_model: str) -> list[dict]:
    rows = read_csv(path)
    collected: list[dict] = []

    seen = set()
    for row in rows:
        if row.get("model") != representative_model:
            continue

        sample_id = row.get("sample_id", "")
        comparison = row.get("comparison", "")
        model = row.get("model", "")

        key = (sample_id, comparison, model)
        if key in seen:
            continue
        seen.add(key)

        collected.append(
            {
                "sample_id": sample_id,
                "comparison": comparison,
                "source": "gemini_official",
                "model_or_encoding": model,
                "measurement_level": "official_count_tokens",
                "baseline_tokens": int(row["baseline_total_tokens"]),
                "compared_tokens": int(row["compared_total_tokens"]),
                "ratio": float(row["comparison_ratio"]),
                "notes": "Gemini official countTokens; not full billable usage.",
            }
        )

    return collected


def build_ratio_matrix(detailed_rows: list[dict]) -> list[dict]:
    by_sample: dict[tuple[str, str], dict] = {}

    for row in detailed_rows:
        key = (row["sample_id"], row["comparison"])
        target = by_sample.setdefault(
            key,
            {
                "sample_id": row["sample_id"],
                "comparison": row["comparison"],
                "openai_cl100k_base_ratio": "",
                "openai_o200k_base_ratio": "",
                "openai_current_api_ratio": "",
                "gemini_official_ratio": "",
                "claude_official_ratio": "not_measured",
            },
        )

        source = row["source"]
        model_or_encoding = row["model_or_encoding"]

        if source == "openai_tiktoken" and model_or_encoding == "cl100k_base":
            target["openai_cl100k_base_ratio"] = f"{row['ratio']:.6f}"
        elif source == "openai_tiktoken" and model_or_encoding == "o200k_base":
            target["openai_o200k_base_ratio"] = f"{row['ratio']:.6f}"
        elif source == "openai_current_api":
            target["openai_current_api_ratio"] = f"{row['ratio']:.6f}"
        elif source == "gemini_official":
            target["gemini_official_ratio"] = f"{row['ratio']:.6f}"

    order = {
        "dev_prompt": 1,
        "project_rules": 2,
        "system_prompt": 3,
        "implementation_plan": 4,
        "flores": 5,
    }

    return sorted(
        by_sample.values(),
        key=lambda r: (order.get(r["sample_id"], 99), r["comparison"]),
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_ratio_matrix(rows: list[dict]) -> str:
    lines = []
    lines.append("## Ratio matrix")
    lines.append("")
    lines.append("| Sample | Comparison | OpenAI cl100k | OpenAI o200k | OpenAI current API | Gemini official | Claude |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for r in rows:
        def fmt(value: str) -> str:
            if value in ("", "not_measured"):
                return value or "n/a"
            return f"{float(value):.3f}x"

        lines.append(
            f"| {r['sample_id']} | {r['comparison']} | "
            f"{fmt(r['openai_cl100k_base_ratio'])} | "
            f"{fmt(r['openai_o200k_base_ratio'])} | "
            f"{fmt(r['openai_current_api_ratio'])} | "
            f"{fmt(r['gemini_official_ratio'])} | "
            f"{r['claude_official_ratio']} |"
        )
    return "\n".join(lines)


def md_detailed_table(rows: list[dict]) -> str:
    lines = []
    lines.append("## Detailed token counts")
    lines.append("")
    lines.append("| Sample | Comparison | Source | Model / encoding | Baseline tokens | Compared tokens | Ratio | Measurement level |")
    lines.append("|---|---|---|---|---:|---:|---:|---|")
    for r in rows:
        lines.append(
            f"| {r['sample_id']} | {r['comparison']} | {r['source']} | {r['model_or_encoding']} | "
            f"{r['baseline_tokens']} | {r['compared_tokens']} | {r['ratio']:.6f}x | {r['measurement_level']} |"
        )
    return "\n".join(lines)


def write_markdown(path: Path, ratio_rows: list[dict], detailed_rows: list[dict], args: argparse.Namespace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Cross-model tokenization summary

Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`

## Representative sources

| Source | Representative |
|---|---|
| OpenAI local historical baseline | `cl100k_base` |
| OpenAI local modern baseline | `o200k_base` |
| OpenAI current API input count | `{args.openai_current_model}` |
| Gemini official countTokens | `{args.gemini_model}` |
| Claude official token count | not measured |

## Methodological warning

These rows are not all the same measurement type.

- `cl100k_base` and `o200k_base` are local raw tokenizer counts through `tiktoken`.
- OpenAI current API is Responses input token count.
- Gemini is official `countTokens`.
- Claude is not measured because API credits are not available.

Do not interpret this table as final price or billable usage.

{md_ratio_matrix(ratio_rows)}

{md_detailed_table(detailed_rows)}

## Draft interpretation

1. The old OpenAI `cl100k_base` baseline shows the largest RU/EN gap.
2. The newer OpenAI `o200k_base` baseline is much closer to current OpenAI API input counts.
3. Current OpenAI API input counts are nearly identical to local `o200k_base` ratios on this dataset.
4. Gemini official `countTokens` shows slightly lower RU/EN ratios than current OpenAI API count on these samples.
5. FLORES shows a larger gap than practical Markdown samples across both OpenAI and Gemini.
6. Claude remains unmeasured and should be marked as skipped, not estimated.

## Article-safe wording

On this dataset, the practical Markdown files show a much smaller RU/EN gap than the neutral FLORES corpus baseline. The old `cl100k_base` tokenizer is useful as a historical baseline, but current OpenAI input token counting is much closer to `o200k_base`. Gemini official `countTokens` shows even slightly lower RU/EN ratios on the same samples, although absolute token counts and pricing still need separate analysis.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai-tiktoken-csv", default="results/openai_tiktoken_counts.csv")
    parser.add_argument("--openai-current-csv", default="results/openai_current_model_input_token_counts.csv")
    parser.add_argument("--gemini-csv", default="results/gemini_official_token_counts.csv")
    parser.add_argument("--openai-current-model", default="gpt-5.5")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash")
    parser.add_argument("--output-csv", default="results/cross_model_summary.csv")
    parser.add_argument("--output-md", default="results/cross_model_summary.md")
    parser.add_argument("--metadata-output", default="results/cross_model_summary_metadata.json")
    args = parser.parse_args()

    detailed_rows: list[dict] = []
    detailed_rows.extend(collect_openai_tiktoken(Path(args.openai_tiktoken_csv)))
    detailed_rows.extend(collect_openai_current(Path(args.openai_current_csv), args.openai_current_model))
    detailed_rows.extend(collect_gemini(Path(args.gemini_csv), args.gemini_model))

    if not detailed_rows:
        raise SystemExit("ERROR: no rows collected. Check input CSV paths.")

    order_source = {
        "openai_tiktoken": 1,
        "openai_current_api": 2,
        "gemini_official": 3,
    }
    order_sample = {
        "dev_prompt": 1,
        "project_rules": 2,
        "system_prompt": 3,
        "implementation_plan": 4,
        "flores": 5,
    }
    order_encoding = {
        "cl100k_base": 1,
        "o200k_base": 2,
    }

    detailed_rows = sorted(
        detailed_rows,
        key=lambda r: (
            order_sample.get(r["sample_id"], 99),
            r["comparison"],
            order_source.get(r["source"], 99),
            order_encoding.get(r["model_or_encoding"], 99),
            r["model_or_encoding"],
        ),
    )

    ratio_rows = build_ratio_matrix(detailed_rows)

    write_csv(Path(args.output_csv), detailed_rows)
    write_markdown(Path(args.output_md), ratio_rows, detailed_rows, args)

    metadata = {
        "layer": "05_cross_model_summary",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "openai_tiktoken_csv": args.openai_tiktoken_csv,
            "openai_current_csv": args.openai_current_csv,
            "gemini_csv": args.gemini_csv,
        },
        "representatives": {
            "openai_current_model": args.openai_current_model,
            "gemini_model": args.gemini_model,
            "claude": "not_measured",
        },
        "outputs": {
            "csv": args.output_csv,
            "markdown": args.output_md,
        },
        "row_count": len(detailed_rows),
        "ratio_row_count": len(ratio_rows),
        "note": "This summary combines different measurement levels. It is not final billable usage or pricing.",
    }

    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {args.output_csv}")
    print(f"Saved Markdown: {args.output_md}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print(md_ratio_matrix(ratio_rows))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
