#!/usr/bin/env python3
"""
Layer 06 v2: count full vs prose_only ratios and structural token share.
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
    r"^(?P<base_sample>.+)_(?P<variant>full|prose_only)_(?P<language>ru|en|mixed)\.md$"
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


def token_count(enc, path: Path) -> int:
    return len(enc.encode(path.read_text(encoding="utf-8")))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary_rows: list[dict]) -> None:
    lines = []
    lines.append("# Markdown decomposition v2 summary")
    lines.append("")
    lines.append("## Full vs prose-only")
    lines.append("")
    lines.append("| Sample | Comparison | Encoding | Full ratio | Prose-only ratio | Ratio delta | EN structural share | RU/mixed structural share |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| {row['base_sample']} | {row['comparison']} | {row['encoding']} | "
            f"{row['full_ratio']:.6f}x | {row['prose_only_ratio']:.6f}x | "
            f"{row['ratio_delta']:+.6f}x | {row['baseline_structural_share']:.2%} | "
            f"{row['compared_structural_share']:.2%} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Positive `ratio_delta` means prose-only has a higher RU/EN gap than full Markdown.")
    lines.append("- That supports the idea that Markdown/code-like fragments dilute the language gap.")
    lines.append("- Structural shares are computed as removed token share: `(full - prose_only) / full`.")
    lines.append("- No `structure_only` RU/EN ratio is used, because extracted structure is not a semantic translation pair.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/decomposed_samples")
    parser.add_argument("--encodings", nargs="+", default=["cl100k_base", "o200k_base"])
    parser.add_argument("--counts-output", default="results/markdown_decomposition_v2_tiktoken_counts.csv")
    parser.add_argument("--summary-output", default="results/markdown_decomposition_v2_summary.csv")
    parser.add_argument("--summary-md-output", default="results/markdown_decomposition_v2_summary.md")
    parser.add_argument("--metadata-output", default="results/markdown_decomposition_v2_tiktoken_metadata.json")
    args = parser.parse_args()

    grouped = find_files(Path(args.samples_dir))
    if not grouped:
        raise SystemExit(f"ERROR: no decomposed sample files found in {args.samples_dir}")

    encoders = {name: tiktoken.get_encoding(name) for name in args.encodings}

    count_rows: list[dict] = []
    summary_rows: list[dict] = []

    base_samples = sorted({key[0] for key in grouped.keys()})
    for base_sample in base_samples:
        full_langs = grouped.get((base_sample, "full"), {})
        prose_langs = grouped.get((base_sample, "prose_only"), {})

        pairs: list[tuple[str, str, str]] = []
        if "en" in full_langs and "ru" in full_langs and "en" in prose_langs and "ru" in prose_langs:
            pairs.append(("ru_en", "en", "ru"))
        if "en" in full_langs and "mixed" in full_langs and "en" in prose_langs and "mixed" in prose_langs:
            pairs.append(("mixed_en", "en", "mixed"))

        for comparison, baseline_lang, compared_lang in pairs:
            for enc_name, enc in encoders.items():
                full_baseline = token_count(enc, full_langs[baseline_lang])
                full_compared = token_count(enc, full_langs[compared_lang])
                prose_baseline = token_count(enc, prose_langs[baseline_lang])
                prose_compared = token_count(enc, prose_langs[compared_lang])

                full_ratio = full_compared / full_baseline if full_baseline else 0.0
                prose_ratio = prose_compared / prose_baseline if prose_baseline else 0.0
                ratio_delta = prose_ratio - full_ratio

                baseline_removed = max(full_baseline - prose_baseline, 0)
                compared_removed = max(full_compared - prose_compared, 0)

                baseline_share = baseline_removed / full_baseline if full_baseline else 0.0
                compared_share = compared_removed / full_compared if full_compared else 0.0

                for variant, lang, tokens, path in [
                    ("full", baseline_lang, full_baseline, full_langs[baseline_lang]),
                    ("full", compared_lang, full_compared, full_langs[compared_lang]),
                    ("prose_only", baseline_lang, prose_baseline, prose_langs[baseline_lang]),
                    ("prose_only", compared_lang, prose_compared, prose_langs[compared_lang]),
                ]:
                    count_rows.append(
                        {
                            "base_sample": base_sample,
                            "variant": variant,
                            "comparison": comparison,
                            "language": lang,
                            "encoding": enc_name,
                            "path": str(path),
                            "tokens": tokens,
                            "chars": len(path.read_text(encoding="utf-8")),
                        }
                    )

                summary_rows.append(
                    {
                        "base_sample": base_sample,
                        "comparison": comparison,
                        "encoding": enc_name,
                        "baseline_language": baseline_lang,
                        "compared_language": compared_lang,
                        "full_baseline_tokens": full_baseline,
                        "full_compared_tokens": full_compared,
                        "prose_baseline_tokens": prose_baseline,
                        "prose_compared_tokens": prose_compared,
                        "full_ratio": round(full_ratio, 6),
                        "prose_only_ratio": round(prose_ratio, 6),
                        "ratio_delta": round(ratio_delta, 6),
                        "baseline_structural_tokens_removed": baseline_removed,
                        "compared_structural_tokens_removed": compared_removed,
                        "baseline_structural_share": round(baseline_share, 6),
                        "compared_structural_share": round(compared_share, 6),
                    }
                )

    order_sample = {"dev_prompt": 1, "project_rules": 2, "system_prompt": 3, "implementation_plan": 4}
    summary_rows.sort(key=lambda r: (order_sample.get(r["base_sample"], 99), r["encoding"]))
    count_rows.sort(key=lambda r: (order_sample.get(r["base_sample"], 99), r["encoding"], r["variant"], r["language"]))

    write_csv(Path(args.counts_output), count_rows)
    write_csv(Path(args.summary_output), summary_rows)
    write_markdown(Path(args.summary_md_output), summary_rows)

    metadata = {
        "layer": "06_markdown_decomposition_v2_tiktoken",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "samples_dir": args.samples_dir,
        "encodings": args.encodings,
        "counts_output": args.counts_output,
        "summary_output": args.summary_output,
        "summary_md_output": args.summary_md_output,
        "note": "Full vs prose-only decomposition. No structure-only ratio comparison.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved counts: {args.counts_output}")
    print(f"Saved summary CSV: {args.summary_output}")
    print(f"Saved summary MD: {args.summary_md_output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("| Sample | Comparison | Encoding | Full ratio | Prose-only ratio | Delta | EN structural share | RU/mixed structural share |")
    print("|---|---|---|---:|---:|---:|---:|---:|")
    for row in summary_rows:
        print(
            f"| {row['base_sample']} | {row['comparison']} | {row['encoding']} | "
            f"{row['full_ratio']:.6f}x | {row['prose_only_ratio']:.6f}x | "
            f"{row['ratio_delta']:+.6f}x | {row['baseline_structural_share']:.2%} | "
            f"{row['compared_structural_share']:.2%} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
