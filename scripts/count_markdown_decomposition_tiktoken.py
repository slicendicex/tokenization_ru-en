#!/usr/bin/env python3
"""
Count tiktoken ratios for decomposed Markdown samples.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import tiktoken


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


def build_markdown_summary(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Markdown decomposition tiktoken summary")
    lines.append("")
    lines.append("## Ratio table")
    lines.append("")
    lines.append("| Base sample | Variant | Comparison | Encoding | EN tokens | RU/mixed tokens | Ratio |")
    lines.append("|---|---|---|---|---:|---:|---:|")

    seen = set()
    for row in rows:
        key = (row["base_sample"], row["variant"], row["comparison"], row["encoding"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"| {row['base_sample']} | {row['variant']} | {row['comparison']} | {row['encoding']} | "
            f"{row['baseline_tokens']} | {row['compared_tokens']} | {float(row['ratio']):.6f}x |"
        )

    lines.append("")
    lines.append("## Compact o200k view")
    lines.append("")
    lines.append("| Base sample | full | prose_only | structure_only |")
    lines.append("|---|---:|---:|---:|")

    matrix: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["encoding"] != "o200k_base":
            continue
        matrix.setdefault(row["base_sample"], {})[row["variant"]] = f"{float(row['ratio']):.3f}x"

    order = ["dev_prompt", "project_rules", "system_prompt", "implementation_plan"]
    for sample in sorted(matrix, key=lambda x: order.index(x) if x in order else 99):
        values = matrix[sample]
        lines.append(
            f"| {sample} | {values.get('full', 'n/a')} | "
            f"{values.get('prose_only', 'n/a')} | {values.get('structure_only', 'n/a')} |"
        )

    lines.append("")
    lines.append("## Interpretation checklist")
    lines.append("")
    lines.append("- If `prose_only` > `full`, Markdown/code structure likely lowers the gap.")
    lines.append("- If `structure_only` is close to 1.0, structural/code-like fragments are language-neutral.")
    lines.append("- If `structure_only` is empty or unstable, do not overinterpret it.")
    lines.append("- If the pattern is not visible, the hypothesis should be weakened.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/decomposed_samples")
    parser.add_argument("--encodings", nargs="+", default=["cl100k_base", "o200k_base"])
    parser.add_argument("--output", default="results/markdown_decomposition_tiktoken_counts.csv")
    parser.add_argument("--summary-output", default="results/markdown_decomposition_tiktoken_summary.md")
    parser.add_argument("--metadata-output", default="results/markdown_decomposition_tiktoken_metadata.json")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    grouped = find_files(samples_dir)
    if not grouped:
        raise SystemExit(f"ERROR: no decomposed sample files found in {samples_dir}")

    encoders = {name: tiktoken.get_encoding(name) for name in args.encodings}

    rows: list[dict] = []
    comparisons: list[dict] = []

    for (base_sample, variant), langs in sorted(grouped.items()):
        pairs: list[tuple[str, str, str]] = []
        if "en" in langs and "ru" in langs:
            pairs.append(("ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            pairs.append(("mixed_en", "en", "mixed"))

        for comparison, baseline_lang, compared_lang in pairs:
            baseline_text = langs[baseline_lang].read_text(encoding="utf-8")
            compared_text = langs[compared_lang].read_text(encoding="utf-8")

            comparisons.append(
                {
                    "base_sample": base_sample,
                    "variant": variant,
                    "comparison": comparison,
                    "baseline_language": baseline_lang,
                    "compared_language": compared_lang,
                }
            )

            for enc_name, enc in encoders.items():
                baseline_tokens = len(enc.encode(baseline_text))
                compared_tokens = len(enc.encode(compared_text))
                ratio = compared_tokens / baseline_tokens if baseline_tokens else 0.0

                rows.append(
                    {
                        "base_sample": base_sample,
                        "variant": variant,
                        "comparison": comparison,
                        "encoding": enc_name,
                        "baseline_language": baseline_lang,
                        "compared_language": compared_lang,
                        "baseline_path": str(langs[baseline_lang]),
                        "compared_path": str(langs[compared_lang]),
                        "baseline_chars": len(baseline_text),
                        "compared_chars": len(compared_text),
                        "baseline_tokens": baseline_tokens,
                        "compared_tokens": compared_tokens,
                        "ratio": round(ratio, 6),
                    }
                )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    build_markdown_summary(rows, Path(args.summary_output))

    metadata = {
        "layer": "06_markdown_decomposition_tiktoken_count",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "samples_dir": str(samples_dir),
        "encodings": args.encodings,
        "output_csv": args.output,
        "summary_output": args.summary_output,
        "comparisons": comparisons,
        "note": "Local tiktoken counts on heuristic decomposed Markdown variants.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {args.output}")
    print(f"Saved summary: {args.summary_output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("| Base sample | Variant | Comparison | Encoding | EN tokens | RU/mixed tokens | Ratio |")
    print("|---|---|---|---|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row['base_sample']} | {row['variant']} | {row['comparison']} | {row['encoding']} | "
            f"{row['baseline_tokens']} | {row['compared_tokens']} | {row['ratio']}x |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
