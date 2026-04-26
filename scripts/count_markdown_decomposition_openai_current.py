#!/usr/bin/env python3
"""
Optional: count current OpenAI input tokens for decomposed Markdown samples.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI


FILE_RE = re.compile(
    r"^(?P<base_sample>.+)_(?P<variant>full|prose_only|structure_only)_(?P<language>ru|en|mixed)\.md$"
)


def find_files(samples_dir: Path) -> dict[tuple[str, str], dict[str, Path]]:
    grouped: dict[tuple[str, str], dict[str, Path]] = {}
    for path in sorted(samples_dir.glob("*.md")):
        match = FILE_RE.match(path.name)
        if not match:
            continue
        key = (match.group("base_sample"), match.group("variant"))
        grouped.setdefault(key, {})[match.group("language")] = path
    return grouped


def count_openai(client: OpenAI, model: str, text: str) -> int:
    response = client.responses.input_tokens.count(model=model, input=text)
    return int(response.input_tokens)


def build_summary(rows: list[dict], output_path: Path) -> None:
    lines = []
    lines.append("# Markdown decomposition OpenAI current summary")
    lines.append("")
    lines.append("| Base sample | Variant | Comparison | Model | EN tokens | RU/mixed tokens | Ratio |")
    lines.append("|---|---|---|---|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['base_sample']} | {row['variant']} | {row['comparison']} | {row['model']} | "
            f"{row['baseline_tokens']} | {row['compared_tokens']} | {float(row['ratio']):.6f}x |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/decomposed_samples")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--output", default="results/markdown_decomposition_openai_current_counts.csv")
    parser.add_argument("--summary-output", default="results/markdown_decomposition_openai_current_summary.md")
    parser.add_argument("--metadata-output", default="results/markdown_decomposition_openai_current_metadata.json")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    client = OpenAI()
    grouped = find_files(Path(args.samples_dir))
    rows = []
    errors = []

    for model in args.models:
        for (base_sample, variant), langs in sorted(grouped.items()):
            pairs = []
            if "en" in langs and "ru" in langs:
                pairs.append(("ru_en", "en", "ru"))
            if "en" in langs and "mixed" in langs:
                pairs.append(("mixed_en", "en", "mixed"))

            for comparison, baseline_lang, compared_lang in pairs:
                baseline_text = langs[baseline_lang].read_text(encoding="utf-8")
                compared_text = langs[compared_lang].read_text(encoding="utf-8")
                try:
                    baseline_tokens = count_openai(client, model, baseline_text)
                    compared_tokens = count_openai(client, model, compared_text)
                except Exception as exc:
                    errors.append(
                        {
                            "model": model,
                            "base_sample": base_sample,
                            "variant": variant,
                            "comparison": comparison,
                            "error": repr(exc),
                        }
                    )
                    print(f"ERROR: {model} / {base_sample} / {variant}: {exc}")
                    if not args.continue_on_error:
                        raise
                    continue

                ratio = compared_tokens / baseline_tokens if baseline_tokens else 0.0
                rows.append(
                    {
                        "base_sample": base_sample,
                        "variant": variant,
                        "comparison": comparison,
                        "model": model,
                        "baseline_language": baseline_lang,
                        "compared_language": compared_lang,
                        "baseline_tokens": baseline_tokens,
                        "compared_tokens": compared_tokens,
                        "ratio": round(ratio, 6),
                    }
                )

    if not rows:
        raise SystemExit("ERROR: no rows generated.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    build_summary(rows, Path(args.summary_output))

    metadata = {
        "layer": "06_markdown_decomposition_openai_current",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "errors": errors,
        "note": "OpenAI Responses input token count API on decomposed Markdown variants.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {args.output}")
    print(f"Saved summary: {args.summary_output}")
    print()
    print("| Base sample | Variant | Comparison | Model | EN tokens | RU/mixed tokens | Ratio |")
    print("|---|---|---|---|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row['base_sample']} | {row['variant']} | {row['comparison']} | {row['model']} | "
            f"{row['baseline_tokens']} | {row['compared_tokens']} | {row['ratio']}x |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
