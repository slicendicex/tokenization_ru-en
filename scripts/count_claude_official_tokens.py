#!/usr/bin/env python3
"""
Count Claude official input tokens for Markdown sample pairs.

This script uses Anthropic's official Token Counting API:
    client.messages.count_tokens(...)

It does NOT imitate Claude's tokenizer locally.

Supported comparisons:
- strict RU/EN: *_ru.md vs *_en.md
- mixed/EN: *_mixed.md vs *_en.md

Payload styles:
- message: messages=[{"role": "user", "content": text}]
- system: system=text, messages=[{"role": "user", "content": "ok"}]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from anthropic import Anthropic


@dataclass(frozen=True)
class SampleFile:
    sample_id: str
    language: str
    path: Path
    source_format: str


def find_sample_files(samples_dir: Path, extension: str) -> List[SampleFile]:
    ext = extension.lstrip(".")
    pattern = re.compile(rf"^(?P<sample_id>.+)_(?P<language>ru|en|mixed)\.{re.escape(ext)}$")

    result: List[SampleFile] = []
    for path in sorted(samples_dir.glob(f"*.{ext}")):
        match = pattern.match(path.name)
        if not match:
            continue
        result.append(
            SampleFile(
                sample_id=match.group("sample_id"),
                language=match.group("language"),
                path=path,
                source_format=ext,
            )
        )
    return result


def group_by_sample(files: Iterable[SampleFile]) -> Dict[str, Dict[str, SampleFile]]:
    grouped: Dict[str, Dict[str, SampleFile]] = {}
    for file in files:
        grouped.setdefault(file.sample_id, {})[file.language] = file
    return grouped


def collect_comparisons(grouped: Dict[str, Dict[str, SampleFile]]) -> List[Tuple[str, str, str, str]]:
    comparisons: List[Tuple[str, str, str, str]] = []

    for sample_id, langs in sorted(grouped.items()):
        if "en" in langs and "ru" in langs:
            comparisons.append((sample_id, "ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            comparisons.append((sample_id, "mixed_en", "en", "mixed"))

    return comparisons


def count_claude_tokens(client: Anthropic, model: str, text: str, payload_style: str) -> int:
    if payload_style == "message":
        response = client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )
    elif payload_style == "system":
        response = client.messages.count_tokens(
            model=model,
            system=text,
            messages=[{"role": "user", "content": "ok"}],
        )
    else:
        raise ValueError(f"Unsupported payload_style: {payload_style}")

    return int(response.input_tokens)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Claude model IDs, e.g. claude-opus-4-7 claude-sonnet-4-6 claude-haiku-4-5",
    )
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--extension", default="md")
    parser.add_argument("--payload-style", choices=["message", "system"], default="message")
    parser.add_argument("--output", default="results/claude_official_token_counts.csv")
    parser.add_argument("--metadata-output", default="results/claude_official_token_counts_metadata.json")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    client = Anthropic()
    samples_dir = Path(args.samples_dir)
    output_path = Path(args.output)
    metadata_path = Path(args.metadata_output)

    files = find_sample_files(samples_dir, args.extension)
    if not files:
        print(f"ERROR: no '*.{args.extension}' sample files found in {samples_dir}", file=sys.stderr)
        return 1

    grouped = group_by_sample(files)
    comparisons = collect_comparisons(grouped)
    if not comparisons:
        print("ERROR: no valid comparisons found.", file=sys.stderr)
        return 1

    rows: List[dict] = []
    errors: List[dict] = []

    for model in args.models:
        for sample_id, comparison, baseline_lang, compared_lang in comparisons:
            langs = grouped[sample_id]
            baseline_path = langs[baseline_lang].path
            compared_path = langs[compared_lang].path

            baseline_text = baseline_path.read_text(encoding="utf-8")
            compared_text = compared_path.read_text(encoding="utf-8")

            try:
                baseline_tokens = count_claude_tokens(client, model, baseline_text, args.payload_style)
                if args.sleep:
                    time.sleep(args.sleep)

                compared_tokens = count_claude_tokens(client, model, compared_text, args.payload_style)
                if args.sleep:
                    time.sleep(args.sleep)
            except Exception as exc:
                error = {
                    "model": model,
                    "sample_id": sample_id,
                    "comparison": comparison,
                    "payload_style": args.payload_style,
                    "error": repr(exc),
                }
                errors.append(error)
                print(f"ERROR for {model} / {sample_id} / {comparison}: {exc}", file=sys.stderr)
                if not args.continue_on_error:
                    return 1
                continue

            ratio = compared_tokens / baseline_tokens if baseline_tokens else 0.0

            for lang, token_count, path, is_baseline in [
                (baseline_lang, baseline_tokens, baseline_path, True),
                (compared_lang, compared_tokens, compared_path, False),
            ]:
                text = path.read_text(encoding="utf-8")
                rows.append(
                    {
                        "sample_id": sample_id,
                        "comparison": comparison,
                        "language": lang,
                        "is_baseline": str(is_baseline).lower(),
                        "model": model,
                        "payload_style": args.payload_style,
                        "source_format": args.extension,
                        "source_path": str(path),
                        "char_count": len(text),
                        "byte_count": len(text.encode("utf-8")),
                        "input_tokens": token_count,
                        "baseline_language": baseline_lang,
                        "baseline_input_tokens": baseline_tokens,
                        "compared_language": compared_lang,
                        "compared_input_tokens": compared_tokens,
                        "comparison_ratio": round(ratio, 6),
                    }
                )

    if not rows:
        print("ERROR: no rows generated.", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "layer": "04_claude_official_token_count",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "payload_style": args.payload_style,
        "samples_dir": str(samples_dir),
        "source_extension": args.extension,
        "output_csv": str(output_path),
        "comparisons": [
            {
                "sample_id": sample_id,
                "comparison": comparison,
                "baseline_language": baseline_lang,
                "compared_language": compared_lang,
            }
            for sample_id, comparison, baseline_lang, compared_lang in comparisons
        ],
        "errors": errors,
        "note": (
            "This uses Anthropic's official Token Counting API. "
            "Anthropic documents token counts as estimates; actual input tokens during message creation "
            "may differ by a small amount, and system-added tokens may be included in counts but not billed."
        ),
    }

    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {output_path}")
    print(f"Saved metadata: {metadata_path}")
    print()
    print("| Sample | Comparison | Model | Baseline input tokens | Compared input tokens | Ratio |")
    print("|---|---|---|---:|---:|---:|")

    seen = set()
    for row in rows:
        key = (row["sample_id"], row["comparison"], row["model"])
        if key in seen:
            continue
        seen.add(key)
        print(
            f"| {row['sample_id']} | {row['comparison']} | {row['model']} | "
            f"{row['baseline_input_tokens']} | {row['compared_input_tokens']} | "
            f"{row['comparison_ratio']}x |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
