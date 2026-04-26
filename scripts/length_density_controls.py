#!/usr/bin/env python3
"""
Layer 06.5 — Length and density controls.

Computes:
- char/byte/word/token counts
- RU/EN char ratio
- RU/EN token ratio
- tokens-per-char ratio
- tokens-per-word ratio
- FLORES aligned chunks matched to Markdown sample sizes

This script does not call any external API.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import tiktoken


SAMPLE_RE = re.compile(r"^(?P<sample_id>.+)_(?P<language>ru|en|mixed)\.md$")
DECOMP_RE = re.compile(r"^(?P<sample_id>.+)_(?P<variant>full|prose_only)_(?P<language>ru|en|mixed)\.md$")


@dataclass(frozen=True)
class TextStats:
    char_count: int
    byte_count: int
    word_count: int
    token_count: int
    tokens_per_char: float
    tokens_per_word: float


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def word_count(text: str) -> int:
    # Unicode-ish word counting: letters/digits chunks.
    # Good enough for density control; not a linguistic tokenizer.
    return len(re.findall(r"[^\W_]+(?:[-'][^\W_]+)?", text, flags=re.UNICODE))


def compute_stats(text: str, enc) -> TextStats:
    chars = len(text)
    bytes_ = len(text.encode("utf-8"))
    words = word_count(text)
    tokens = len(enc.encode(text))
    return TextStats(
        char_count=chars,
        byte_count=bytes_,
        word_count=words,
        token_count=tokens,
        tokens_per_char=safe_div(tokens, chars),
        tokens_per_word=safe_div(tokens, words),
    )


def read_pairs(samples_dir: Path) -> dict[str, dict[str, Path]]:
    grouped: dict[str, dict[str, Path]] = {}
    for path in sorted(samples_dir.glob("*.md")):
        match = SAMPLE_RE.match(path.name)
        if not match:
            continue
        grouped.setdefault(match.group("sample_id"), {})[match.group("language")] = path
    return grouped


def read_decomposed_pairs(decomposed_dir: Path) -> dict[tuple[str, str], dict[str, Path]]:
    grouped: dict[tuple[str, str], dict[str, Path]] = {}
    if not decomposed_dir.exists():
        return grouped
    for path in sorted(decomposed_dir.glob("*.md")):
        match = DECOMP_RE.match(path.name)
        if not match:
            continue
        key = (match.group("sample_id"), match.group("variant"))
        grouped.setdefault(key, {})[match.group("language")] = path
    return grouped


def pair_rows_for_texts(
    *,
    dataset: str,
    sample_id: str,
    variant: str,
    comparison: str,
    baseline_language: str,
    compared_language: str,
    baseline_text: str,
    compared_text: str,
    encoding_name: str,
    enc,
) -> dict:
    baseline = compute_stats(baseline_text, enc)
    compared = compute_stats(compared_text, enc)

    char_ratio = safe_div(compared.char_count, baseline.char_count)
    byte_ratio = safe_div(compared.byte_count, baseline.byte_count)
    word_ratio = safe_div(compared.word_count, baseline.word_count)
    token_ratio = safe_div(compared.token_count, baseline.token_count)

    return {
        "dataset": dataset,
        "sample_id": sample_id,
        "variant": variant,
        "comparison": comparison,
        "encoding": encoding_name,
        "baseline_language": baseline_language,
        "compared_language": compared_language,
        "baseline_chars": baseline.char_count,
        "compared_chars": compared.char_count,
        "char_ratio": round(char_ratio, 6),
        "baseline_bytes": baseline.byte_count,
        "compared_bytes": compared.byte_count,
        "byte_ratio": round(byte_ratio, 6),
        "baseline_words": baseline.word_count,
        "compared_words": compared.word_count,
        "word_ratio": round(word_ratio, 6),
        "baseline_tokens": baseline.token_count,
        "compared_tokens": compared.token_count,
        "token_ratio": round(token_ratio, 6),
        "baseline_tokens_per_char": round(baseline.tokens_per_char, 8),
        "compared_tokens_per_char": round(compared.tokens_per_char, 8),
        "tokens_per_char_ratio": round(safe_div(compared.tokens_per_char, baseline.tokens_per_char), 6),
        "baseline_tokens_per_word": round(baseline.tokens_per_word, 8),
        "compared_tokens_per_word": round(compared.tokens_per_word, 8),
        "tokens_per_word_ratio": round(safe_div(compared.tokens_per_word, baseline.tokens_per_word), 6),
        "token_ratio_minus_char_ratio": round(token_ratio - char_ratio, 6),
    }


def collect_pair_rows(samples_dir: Path, encoders: dict[str, object]) -> list[dict]:
    grouped = read_pairs(samples_dir)
    rows: list[dict] = []

    for sample_id, langs in sorted(grouped.items()):
        pairs: list[tuple[str, str, str]] = []
        if "en" in langs and "ru" in langs:
            pairs.append(("ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            pairs.append(("mixed_en", "en", "mixed"))

        for comparison, baseline_lang, compared_lang in pairs:
            baseline_text = langs[baseline_lang].read_text(encoding="utf-8")
            compared_text = langs[compared_lang].read_text(encoding="utf-8")

            for enc_name, enc in encoders.items():
                rows.append(
                    pair_rows_for_texts(
                        dataset="samples",
                        sample_id=sample_id,
                        variant="full",
                        comparison=comparison,
                        baseline_language=baseline_lang,
                        compared_language=compared_lang,
                        baseline_text=baseline_text,
                        compared_text=compared_text,
                        encoding_name=enc_name,
                        enc=enc,
                    )
                )

    return rows


def collect_decomposed_rows(decomposed_dir: Path, encoders: dict[str, object]) -> list[dict]:
    grouped = read_decomposed_pairs(decomposed_dir)
    rows: list[dict] = []

    for (sample_id, variant), langs in sorted(grouped.items()):
        pairs: list[tuple[str, str, str]] = []
        if "en" in langs and "ru" in langs:
            pairs.append(("ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            pairs.append(("mixed_en", "en", "mixed"))

        for comparison, baseline_lang, compared_lang in pairs:
            baseline_text = langs[baseline_lang].read_text(encoding="utf-8")
            compared_text = langs[compared_lang].read_text(encoding="utf-8")

            for enc_name, enc in encoders.items():
                rows.append(
                    pair_rows_for_texts(
                        dataset="decomposed",
                        sample_id=sample_id,
                        variant=variant,
                        comparison=comparison,
                        baseline_language=baseline_lang,
                        compared_language=compared_lang,
                        baseline_text=baseline_text,
                        compared_text=compared_text,
                        encoding_name=enc_name,
                        enc=enc,
                    )
                )

    return rows


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def sentence_fallback(text: str) -> list[str]:
    # Fallback only. Alignment is not guaranteed if original FLORES files are not line-aligned.
    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def get_aligned_units(en_text: str, compared_text: str) -> tuple[list[str], list[str], str]:
    en_lines = nonempty_lines(en_text)
    compared_lines = nonempty_lines(compared_text)

    if len(en_lines) == len(compared_lines) and len(en_lines) >= 5:
        return en_lines, compared_lines, "line_aligned"

    en_sentences = sentence_fallback(en_text)
    compared_sentences = sentence_fallback(compared_text)

    if len(en_sentences) == len(compared_sentences) and len(en_sentences) >= 5:
        return en_sentences, compared_sentences, "sentence_fallback_aligned"

    min_len = min(len(en_lines), len(compared_lines))
    if min_len >= 5:
        return en_lines[:min_len], compared_lines[:min_len], "line_truncated_alignment"

    raise ValueError(
        "Could not create aligned FLORES units. Make sure flores_en.md and flores_ru.md are line-aligned."
    )


def target_sizes_from_markdown(samples_dir: Path) -> list[dict]:
    grouped = read_pairs(samples_dir)
    targets = []

    for sample_id, langs in sorted(grouped.items()):
        if sample_id == "flores":
            continue
        if "en" not in langs:
            continue
        en_text = langs["en"].read_text(encoding="utf-8")
        targets.append(
            {
                "target_sample": sample_id,
                "target_en_chars": len(en_text),
                "target_en_words": word_count(en_text),
            }
        )

    # Avoid duplicates and tiny targets.
    targets = [t for t in targets if t["target_en_chars"] >= 100]
    return targets


def build_flores_chunks(
    *,
    en_units: list[str],
    compared_units: list[str],
    target_chars: int,
    min_target_ratio: float,
) -> list[tuple[str, str, int, int]]:
    chunks: list[tuple[str, str, int, int]] = []
    en_acc: list[str] = []
    compared_acc: list[str] = []
    start_idx = 0
    current_chars = 0

    for idx, (en_unit, comp_unit) in enumerate(zip(en_units, compared_units)):
        if not en_acc:
            start_idx = idx
        en_acc.append(en_unit)
        compared_acc.append(comp_unit)
        current_chars += len(en_unit) + 1

        if current_chars >= target_chars:
            chunks.append(("\n".join(en_acc), "\n".join(compared_acc), start_idx, idx))
            en_acc = []
            compared_acc = []
            current_chars = 0

    # Keep last chunk only if it is not too tiny.
    if en_acc and current_chars >= target_chars * min_target_ratio:
        chunks.append(("\n".join(en_acc), "\n".join(compared_acc), start_idx, len(en_units) - 1))

    return chunks


def collect_flores_chunk_rows(
    samples_dir: Path,
    encoders: dict[str, object],
    min_target_ratio: float,
) -> tuple[list[dict], list[dict], dict]:
    grouped = read_pairs(samples_dir)
    if "flores" not in grouped or "en" not in grouped["flores"] or "ru" not in grouped["flores"]:
        return [], [], {"warning": "flores_en.md/flores_ru.md not found; chunk control skipped."}

    en_text = grouped["flores"]["en"].read_text(encoding="utf-8")
    ru_text = grouped["flores"]["ru"].read_text(encoding="utf-8")
    en_units, ru_units, alignment_mode = get_aligned_units(en_text, ru_text)

    targets = target_sizes_from_markdown(samples_dir)

    chunk_rows: list[dict] = []
    summary_rows: list[dict] = []

    for target in targets:
        chunks = build_flores_chunks(
            en_units=en_units,
            compared_units=ru_units,
            target_chars=target["target_en_chars"],
            min_target_ratio=min_target_ratio,
        )

        for chunk_idx, (chunk_en, chunk_ru, start_idx, end_idx) in enumerate(chunks):
            for enc_name, enc in encoders.items():
                row = pair_rows_for_texts(
                    dataset="flores_chunks",
                    sample_id="flores",
                    variant=f"chunked_like_{target['target_sample']}",
                    comparison="ru_en",
                    baseline_language="en",
                    compared_language="ru",
                    baseline_text=chunk_en,
                    compared_text=chunk_ru,
                    encoding_name=enc_name,
                    enc=enc,
                )
                row.update(
                    {
                        "target_sample": target["target_sample"],
                        "target_en_chars": target["target_en_chars"],
                        "chunk_index": chunk_idx,
                        "unit_start_index": start_idx,
                        "unit_end_index": end_idx,
                        "alignment_mode": alignment_mode,
                    }
                )
                chunk_rows.append(row)

    # Summary aggregation.
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in chunk_rows:
        groups.setdefault((row["target_sample"], row["encoding"]), []).append(row)

    for (target_sample, enc_name), rows in sorted(groups.items()):
        token_ratios = [float(r["token_ratio"]) for r in rows]
        char_ratios = [float(r["char_ratio"]) for r in rows]
        tpc_ratios = [float(r["tokens_per_char_ratio"]) for r in rows]

        summary_rows.append(
            {
                "target_sample": target_sample,
                "encoding": enc_name,
                "n_chunks": len(rows),
                "median_token_ratio": round(statistics.median(token_ratios), 6),
                "mean_token_ratio": round(statistics.mean(token_ratios), 6),
                "min_token_ratio": round(min(token_ratios), 6),
                "max_token_ratio": round(max(token_ratios), 6),
                "median_char_ratio": round(statistics.median(char_ratios), 6),
                "median_tokens_per_char_ratio": round(statistics.median(tpc_ratios), 6),
            }
        )

    meta = {
        "alignment_mode": alignment_mode,
        "flores_units": len(en_units),
        "targets": targets,
    }
    return chunk_rows, summary_rows, meta


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    # Make stable fieldnames across rows with possible extra chunk columns.
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(path: Path, pair_rows: list[dict], chunk_summary_rows: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# Layer 06.5 — Length and density controls")
    lines.append("")
    lines.append("## Pair density controls")
    lines.append("")
    lines.append("| Sample | Variant | Comparison | Encoding | Char ratio | Token ratio | Tokens/char ratio | Token ratio - char ratio |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|")

    order_sample = {"dev_prompt": 1, "project_rules": 2, "system_prompt": 3, "implementation_plan": 4, "flores": 5}
    filtered = [r for r in pair_rows if r["dataset"] == "samples"]
    filtered.sort(key=lambda r: (order_sample.get(r["sample_id"], 99), r["encoding"]))

    for row in filtered:
        lines.append(
            f"| {row['sample_id']} | {row['variant']} | {row['comparison']} | {row['encoding']} | "
            f"{float(row['char_ratio']):.3f}x | {float(row['token_ratio']):.3f}x | "
            f"{float(row['tokens_per_char_ratio']):.3f}x | {float(row['token_ratio_minus_char_ratio']):+.3f}x |"
        )

    lines.append("")
    lines.append("## FLORES chunk-size control")
    lines.append("")
    lines.append("| Target size like | Encoding | n chunks | Median token ratio | Mean token ratio | Min | Max | Median char ratio | Median tokens/char ratio |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in chunk_summary_rows:
        lines.append(
            f"| {row['target_sample']} | {row['encoding']} | {row['n_chunks']} | "
            f"{float(row['median_token_ratio']):.3f}x | {float(row['mean_token_ratio']):.3f}x | "
            f"{float(row['min_token_ratio']):.3f}x | {float(row['max_token_ratio']):.3f}x | "
            f"{float(row['median_char_ratio']):.3f}x | {float(row['median_tokens_per_char_ratio']):.3f}x |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `Char ratio` estimates how much longer RU/mixed text is by characters.")
    lines.append("- `Tokens/char ratio` estimates tokenizer-density difference after partially controlling for raw character length.")
    lines.append("- If FLORES chunks remain high at Markdown-like sizes, FLORES is not high merely because the full FLORES file is longer.")
    lines.append("- This is a control, not a perfect causal isolation.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--decomposed-dir", default="data/decomposed_samples_v2")
    parser.add_argument("--include-decomposed", action="store_true")
    parser.add_argument("--encodings", nargs="+", default=["cl100k_base", "o200k_base"])
    parser.add_argument("--min-target-ratio", type=float, default=0.75)
    parser.add_argument("--pairs-output", default="results/length_density_controls_pairs.csv")
    parser.add_argument("--summary-md-output", default="results/length_density_controls_summary.md")
    parser.add_argument("--chunks-output", default="results/flores_chunk_size_control.csv")
    parser.add_argument("--chunks-summary-output", default="results/flores_chunk_size_control_summary.csv")
    parser.add_argument("--metadata-output", default="results/length_density_controls_metadata.json")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    decomposed_dir = Path(args.decomposed_dir)

    encoders = {name: tiktoken.get_encoding(name) for name in args.encodings}

    pair_rows = collect_pair_rows(samples_dir, encoders)

    if args.include_decomposed:
        pair_rows.extend(collect_decomposed_rows(decomposed_dir, encoders))

    chunk_rows, chunk_summary_rows, chunk_meta = collect_flores_chunk_rows(
        samples_dir=samples_dir,
        encoders=encoders,
        min_target_ratio=args.min_target_ratio,
    )

    write_csv(Path(args.pairs_output), pair_rows)
    write_csv(Path(args.chunks_output), chunk_rows)
    write_csv(Path(args.chunks_summary_output), chunk_summary_rows)
    write_markdown_summary(Path(args.summary_md_output), pair_rows, chunk_summary_rows)

    metadata = {
        "layer": "06_5_length_density_controls",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "samples_dir": str(samples_dir),
        "decomposed_dir": str(decomposed_dir),
        "include_decomposed": args.include_decomposed,
        "encodings": args.encodings,
        "outputs": {
            "pairs": args.pairs_output,
            "summary_md": args.summary_md_output,
            "chunks": args.chunks_output,
            "chunks_summary": args.chunks_summary_output,
        },
        "flores_chunk_control": chunk_meta,
        "note": "Length/density controls and aligned FLORES chunks. No external API calls.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved pair controls: {args.pairs_output}")
    print(f"Saved FLORES chunks: {args.chunks_output}")
    print(f"Saved FLORES chunk summary: {args.chunks_summary_output}")
    print(f"Saved summary MD: {args.summary_md_output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("## Pair density controls")
    print("| Sample | Comparison | Encoding | Char ratio | Token ratio | Tokens/char ratio | Token ratio - char ratio |")
    print("|---|---|---|---:|---:|---:|---:|")
    for row in [r for r in pair_rows if r["dataset"] == "samples"]:
        print(
            f"| {row['sample_id']} | {row['comparison']} | {row['encoding']} | "
            f"{float(row['char_ratio']):.3f}x | {float(row['token_ratio']):.3f}x | "
            f"{float(row['tokens_per_char_ratio']):.3f}x | {float(row['token_ratio_minus_char_ratio']):+.3f}x |"
        )

    print()
    print("## FLORES chunk-size control")
    print("| Target size like | Encoding | n chunks | Median token ratio | Mean token ratio | Min | Max | Median char ratio | Median tokens/char ratio |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in chunk_summary_rows:
        print(
            f"| {row['target_sample']} | {row['encoding']} | {row['n_chunks']} | "
            f"{float(row['median_token_ratio']):.3f}x | {float(row['mean_token_ratio']):.3f}x | "
            f"{float(row['min_token_ratio']):.3f}x | {float(row['max_token_ratio']):.3f}x | "
            f"{float(row['median_char_ratio']):.3f}x | {float(row['median_tokens_per_char_ratio']):.3f}x |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
