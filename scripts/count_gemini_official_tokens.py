#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


@dataclass(frozen=True)
class SampleFile:
    sample_id: str
    language: str
    path: Path
    source_format: str


def find_sample_files(samples_dir: Path, extension: str) -> list[SampleFile]:
    ext = extension.lstrip(".")
    pattern = re.compile(rf"^(?P<sample_id>.+)_(?P<language>ru|en|mixed)\.{re.escape(ext)}$")
    result = []
    for path in sorted(samples_dir.glob(f"*.{ext}")):
        match = pattern.match(path.name)
        if match:
            result.append(SampleFile(match.group("sample_id"), match.group("language"), path, ext))
    return result


def group_by_sample(files: list[SampleFile]) -> dict[str, dict[str, SampleFile]]:
    grouped: dict[str, dict[str, SampleFile]] = {}
    for file in files:
        grouped.setdefault(file.sample_id, {})[file.language] = file
    return grouped


def collect_comparisons(grouped: dict[str, dict[str, SampleFile]]) -> list[tuple[str, str, str, str]]:
    comparisons = []
    for sample_id, langs in sorted(grouped.items()):
        if "en" in langs and "ru" in langs:
            comparisons.append((sample_id, "ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            comparisons.append((sample_id, "mixed_en", "en", "mixed"))
    return comparisons


def response_to_dict(response: Any) -> dict:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    if isinstance(response, dict):
        return response
    return {"repr": repr(response)}


def extract_total_tokens(response: Any) -> int:
    value = getattr(response, "total_tokens", None)
    if value is not None:
        return int(value)
    data = response_to_dict(response)
    for key in ("total_tokens", "totalTokens"):
        if key in data and data[key] is not None:
            return int(data[key])
    raise ValueError(f"Could not extract total_tokens from response: {response!r}")


def count_tokens(client: genai.Client, model: str, text: str, payload_style: str) -> tuple[int, dict]:
    if payload_style == "contents":
        response = client.models.count_tokens(model=model, contents=text)
    elif payload_style == "system_instruction":
        response = client.models.count_tokens(
            model=model,
            contents="ok",
            config=types.GenerateContentConfig(system_instruction=text),
        )
    else:
        raise ValueError(f"Unsupported payload_style: {payload_style}")
    return extract_total_tokens(response), response_to_dict(response)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--extension", default="md")
    parser.add_argument("--payload-style", choices=["contents", "system_instruction"], default="contents")
    parser.add_argument("--output", default="results/gemini_official_token_counts.csv")
    parser.add_argument("--metadata-output", default="results/gemini_official_token_counts_metadata.json")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set.", file=sys.stderr)
        return 1

    client = genai.Client(api_key=api_key)
    samples_dir = Path(args.samples_dir)
    files = find_sample_files(samples_dir, args.extension)
    if not files:
        print(f"ERROR: no '*.{args.extension}' sample files found in {samples_dir}", file=sys.stderr)
        return 1

    grouped = group_by_sample(files)
    comparisons = collect_comparisons(grouped)
    rows = []
    errors = []

    for model in args.models:
        for sample_id, comparison, baseline_lang, compared_lang in comparisons:
            langs = grouped[sample_id]
            baseline_path = langs[baseline_lang].path
            compared_path = langs[compared_lang].path
            baseline_text = baseline_path.read_text(encoding="utf-8")
            compared_text = compared_path.read_text(encoding="utf-8")

            try:
                baseline_tokens, baseline_raw = count_tokens(client, model, baseline_text, args.payload_style)
                if args.sleep:
                    time.sleep(args.sleep)
                compared_tokens, compared_raw = count_tokens(client, model, compared_text, args.payload_style)
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
            for lang, token_count, path, is_baseline, raw in [
                (baseline_lang, baseline_tokens, baseline_path, True, baseline_raw),
                (compared_lang, compared_tokens, compared_path, False, compared_raw),
            ]:
                text = path.read_text(encoding="utf-8")
                rows.append({
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
                    "total_tokens": token_count,
                    "baseline_language": baseline_lang,
                    "baseline_total_tokens": baseline_tokens,
                    "compared_language": compared_lang,
                    "compared_total_tokens": compared_tokens,
                    "comparison_ratio": round(ratio, 6),
                    "raw_count_response_json": json.dumps(raw, ensure_ascii=False, sort_keys=True),
                })

    if not rows:
        print("ERROR: no rows generated.", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    metadata_path = Path(args.metadata_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "layer": "04_gemini_official_count_tokens",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "payload_style": args.payload_style,
        "samples_dir": str(samples_dir),
        "source_extension": args.extension,
        "output_csv": str(output_path),
        "comparisons": [
            {"sample_id": s, "comparison": c, "baseline_language": b, "compared_language": x}
            for s, c, b, x in comparisons
        ],
        "errors": errors,
        "note": "Uses Gemini official countTokens via google-genai. Not local tokenizer emulation and not final billable usage.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {output_path}")
    print(f"Saved metadata: {metadata_path}")
    print()
    print("| Sample | Comparison | Model | Baseline tokens | Compared tokens | Ratio |")
    print("|---|---|---|---:|---:|---:|")
    seen = set()
    for row in rows:
        key = (row["sample_id"], row["comparison"], row["model"])
        if key in seen:
            continue
        seen.add(key)
        print(
            f"| {row['sample_id']} | {row['comparison']} | {row['model']} | "
            f"{row['baseline_total_tokens']} | {row['compared_total_tokens']} | {row['comparison_ratio']}x |"
        )

    if errors:
        print()
        print("Errors were recorded in metadata:")
        for error in errors:
            print(f"- {error['model']} / {error['sample_id']} / {error['comparison']}: {error['error']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
