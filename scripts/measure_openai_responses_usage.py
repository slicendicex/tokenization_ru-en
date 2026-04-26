#!/usr/bin/env python3
"""
Optional: measure real Responses API usage for selected samples and models.

WARNING:
This creates real model responses and may incur normal API usage.
Use input token counting as the primary tokenization metric.
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
from typing import Dict, Iterable, List, Tuple, Any

from openai import OpenAI


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
        result.append(SampleFile(match.group("sample_id"), match.group("language"), path, ext))
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


def obj_to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {"repr": repr(obj)}


def extract_usage(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    data = obj_to_dict(usage)
    return {
        "input_tokens": data.get("input_tokens"),
        "output_tokens": data.get("output_tokens"),
        "total_tokens": data.get("total_tokens"),
        "usage_json": json.dumps(data, ensure_ascii=False, sort_keys=True),
    }


def create_minimal_response(client: OpenAI, model: str, text: str, max_output_tokens: int, reasoning_effort: str | None):
    kwargs = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": (
                    "Return exactly one word: OK.\n\n"
                    "The following content is only provided to measure request usage:\n\n"
                    + text
                ),
            }
        ],
        "max_output_tokens": max_output_tokens,
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}

    return client.responses.create(**kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--extension", default="md")
    parser.add_argument("--max-output-tokens", type=int, default=16)
    parser.add_argument("--reasoning-effort", default=None, help="Optional: low, medium, high. Omit by default.")
    parser.add_argument("--output", default="results/openai_real_response_usage.csv")
    parser.add_argument("--metadata-output", default="results/openai_real_response_usage_metadata.json")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    client = OpenAI()
    samples_dir = Path(args.samples_dir)
    files = find_sample_files(samples_dir, args.extension)
    grouped = group_by_sample(files)
    comparisons = collect_comparisons(grouped)

    rows: List[dict] = []
    errors: List[dict] = []

    for model in args.models:
        for sample_id, comparison, baseline_lang, compared_lang in comparisons:
            for lang in (baseline_lang, compared_lang):
                path = grouped[sample_id][lang].path
                text = path.read_text(encoding="utf-8")
                try:
                    response = create_minimal_response(
                        client=client,
                        model=model,
                        text=text,
                        max_output_tokens=args.max_output_tokens,
                        reasoning_effort=args.reasoning_effort,
                    )
                    usage = extract_usage(response)
                except Exception as exc:
                    error = {"model": model, "sample_id": sample_id, "language": lang, "error": repr(exc)}
                    errors.append(error)
                    print(f"ERROR for {model} / {sample_id} / {lang}: {exc}", file=sys.stderr)
                    if not args.continue_on_error:
                        return 1
                    continue

                rows.append(
                    {
                        "sample_id": sample_id,
                        "comparison": comparison,
                        "language": lang,
                        "is_baseline": str(lang == baseline_lang).lower(),
                        "model": model,
                        "source_format": args.extension,
                        "source_path": str(path),
                        "char_count": len(text),
                        "byte_count": len(text.encode("utf-8")),
                        "input_tokens": usage["input_tokens"],
                        "output_tokens": usage["output_tokens"],
                        "total_tokens": usage["total_tokens"],
                        "usage_json": usage["usage_json"],
                    }
                )
                if args.sleep:
                    time.sleep(args.sleep)

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
        "layer": "03_optional_openai_real_response_usage",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "max_output_tokens": args.max_output_tokens,
        "reasoning_effort": args.reasoning_effort,
        "errors": errors,
        "warning": "This creates real responses and may include output/reasoning tokens. Do not use as the primary language-tokenization metric.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CSV: {output_path}")
    print(f"Saved metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
