#!/usr/bin/env python3
"""
Count OpenAI/tiktoken tokens for Markdown sample pairs.

Supported comparisons:
- strict RU/EN: *_ru.md vs *_en.md
- mixed/EN: *_mixed.md vs *_en.md

This script measures raw tokenizer count only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import tiktoken


DEFAULT_ENCODINGS = ("cl100k_base", "o200k_base")


@dataclass(frozen=True)
class SampleFile:
    sample_id: str
    language: str
    path: Path
    source_format: str


@dataclass(frozen=True)
class CountRow:
    sample_id: str
    sample_type: str
    comparison: str
    language: str
    is_baseline: str
    source_format: str
    encoding: str
    source_path: str
    char_count: int
    byte_count: int
    word_count: int
    line_count: int
    token_count: int
    tokens_per_char: float
    chars_per_token: float
    bytes_per_token: float
    baseline_language: str
    baseline_token_count: int
    compared_language: str
    compared_token_count: int
    comparison_ratio: float


def get_package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def derive_sample_type(sample_id: str) -> str:
    mapping = {
        "flores": "parallel_corpus",
        "dev_prompt": "dev_task_instruction",
        "project_rules": "agent_project_rules",
        "system_prompt": "system_prompt",
        "implementation_plan": "mixed_implementation_plan",
    }
    return mapping.get(sample_id, "unknown")


def find_sample_files(samples_dir: Path, extension: str) -> List[SampleFile]:
    ext = extension.lstrip(".")
    pattern = re.compile(rf"^(?P<sample_id>.+)_(?P<language>ru|en|mixed)\.{re.escape(ext)}$")

    sample_files: List[SampleFile] = []
    for path in sorted(samples_dir.glob(f"*.{ext}")):
        match = pattern.match(path.name)
        if not match:
            continue
        sample_files.append(
            SampleFile(
                sample_id=match.group("sample_id"),
                language=match.group("language"),
                path=path,
                source_format=ext,
            )
        )
    return sample_files


def group_by_sample(sample_files: Iterable[SampleFile]) -> Dict[str, Dict[str, SampleFile]]:
    grouped: Dict[str, Dict[str, SampleFile]] = {}
    for sample_file in sample_files:
        grouped.setdefault(sample_file.sample_id, {})[sample_file.language] = sample_file
    return grouped


def rough_word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def count_lines(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def safe_ratio(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def count_tokens(text: str, encoding_name: str) -> int:
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def collect_comparisons(grouped: Dict[str, Dict[str, SampleFile]]) -> List[Tuple[str, str, str, str]]:
    comparisons: List[Tuple[str, str, str, str]] = []
    for sample_id, langs in sorted(grouped.items()):
        if "en" in langs and "ru" in langs:
            comparisons.append((sample_id, "ru_en", "en", "ru"))
        if "en" in langs and "mixed" in langs:
            comparisons.append((sample_id, "mixed_en", "en", "mixed"))
    return comparisons


def build_rows(grouped: Dict[str, Dict[str, SampleFile]], encodings: Tuple[str, ...]) -> List[CountRow]:
    rows: List[CountRow] = []

    for sample_id, comparison, baseline_lang, compared_lang in collect_comparisons(grouped):
        langs = grouped[sample_id]
        texts = {
            baseline_lang: langs[baseline_lang].path.read_text(encoding="utf-8"),
            compared_lang: langs[compared_lang].path.read_text(encoding="utf-8"),
        }

        for encoding in encodings:
            token_counts = {lang: count_tokens(text, encoding) for lang, text in texts.items()}
            baseline_tokens = token_counts[baseline_lang]
            compared_tokens = token_counts[compared_lang]
            comparison_ratio = round(safe_ratio(compared_tokens, baseline_tokens), 6)

            for lang in (baseline_lang, compared_lang):
                text = texts[lang]
                sample_file = langs[lang]
                char_count = len(text)
                byte_count = len(text.encode("utf-8"))
                word_count = rough_word_count(text)
                line_count = count_lines(text)
                token_count = token_counts[lang]

                rows.append(
                    CountRow(
                        sample_id=sample_id,
                        sample_type=derive_sample_type(sample_id),
                        comparison=comparison,
                        language=lang,
                        is_baseline="true" if lang == baseline_lang else "false",
                        source_format=sample_file.source_format,
                        encoding=encoding,
                        source_path=str(sample_file.path),
                        char_count=char_count,
                        byte_count=byte_count,
                        word_count=word_count,
                        line_count=line_count,
                        token_count=token_count,
                        tokens_per_char=round(safe_ratio(token_count, char_count), 6),
                        chars_per_token=round(safe_ratio(char_count, token_count), 6),
                        bytes_per_token=round(safe_ratio(byte_count, token_count), 6),
                        baseline_language=baseline_lang,
                        baseline_token_count=baseline_tokens,
                        compared_language=compared_lang,
                        compared_token_count=compared_tokens,
                        comparison_ratio=comparison_ratio,
                    )
                )

    return rows


def write_csv(rows: List[CountRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(CountRow.__dataclass_fields__.keys())

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_metadata(
    metadata_path: Path,
    samples_dir: Path,
    extension: str,
    output_path: Path,
    grouped: Dict[str, Dict[str, SampleFile]],
    rows: List[CountRow],
    encodings: Tuple[str, ...],
) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    comparisons = collect_comparisons(grouped)
    expected_strict = {"dev_prompt", "project_rules", "system_prompt", "flores"}
    found_strict = {sample_id for sample_id, comparison, _, _ in comparisons if comparison == "ru_en"}
    missing_strict = sorted(expected_strict - found_strict)

    payload = {
        "layer": "02_openai_tiktoken_count_markdown_best_practice_samples",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "samples_dir": str(samples_dir),
        "source_extension": extension.lstrip("."),
        "output_csv": str(output_path),
        "encodings": list(encodings),
        "tiktoken_version": get_package_version("tiktoken"),
        "available_samples": {sample_id: sorted(langs.keys()) for sample_id, langs in sorted(grouped.items())},
        "comparisons": [
            {
                "sample_id": sample_id,
                "comparison": comparison,
                "baseline_language": baseline_lang,
                "compared_language": compared_lang,
            }
            for sample_id, comparison, baseline_lang, compared_lang in comparisons
        ],
        "missing_expected_strict_ru_en_pairs": missing_strict,
        "row_count": len(rows),
        "note": (
            "Raw OpenAI/tiktoken tokenizer count for Markdown samples. "
            "Strict RU/EN and mixed/EN comparisons are kept separate."
        ),
    }
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_summary(rows: List[CountRow]) -> None:
    print("Generated rows:", len(rows))
    print()
    print("Ratios by sample, comparison and encoding:")

    seen = set()
    for row in rows:
        key = (row.sample_id, row.comparison, row.encoding)
        if key in seen:
            continue
        seen.add(key)
        print(
            f"- {row.sample_id:24s} {row.comparison:9s} {row.encoding:12s} "
            f"ratio={row.comparison_ratio:.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--extension", default="md")
    parser.add_argument("--output", default="results/openai_tiktoken_counts.csv")
    parser.add_argument("--metadata-output", default="results/openai_tiktoken_counts_metadata.json")
    parser.add_argument("--encodings", nargs="+", default=list(DEFAULT_ENCODINGS))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_path = Path(args.output)
    metadata_path = Path(args.metadata_output)
    encodings = tuple(args.encodings)
    extension = args.extension.lstrip(".")

    if not samples_dir.exists():
        print(f"ERROR: samples dir does not exist: {samples_dir}", file=sys.stderr)
        return 1

    sample_files = find_sample_files(samples_dir, extension)
    if not sample_files:
        print(f"ERROR: no '.{extension}' sample files found in {samples_dir}", file=sys.stderr)
        return 1

    grouped = group_by_sample(sample_files)

    for encoding in encodings:
        try:
            tiktoken.get_encoding(encoding)
        except Exception as exc:
            print(f"ERROR: cannot load tiktoken encoding '{encoding}': {exc}", file=sys.stderr)
            return 1

    comparisons = collect_comparisons(grouped)
    if not comparisons:
        print("ERROR: no valid comparisons found.", file=sys.stderr)
        return 1

    expected_strict = {"dev_prompt", "project_rules", "system_prompt", "flores"}
    found_strict = {sample_id for sample_id, comparison, _, _ in comparisons if comparison == "ru_en"}
    missing_strict = sorted(expected_strict - found_strict)
    if missing_strict:
        message = "WARNING: missing expected strict RU/EN Markdown pairs: " + ", ".join(missing_strict)
        if args.strict:
            print("ERROR:", message, file=sys.stderr)
            return 1
        print(message, file=sys.stderr)

    rows = build_rows(grouped, encodings)
    write_csv(rows, output_path)
    write_metadata(metadata_path, samples_dir, extension, output_path, grouped, rows, encodings)
    print_summary(rows)
    print()
    print(f"Saved CSV: {output_path}")
    print(f"Saved metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
