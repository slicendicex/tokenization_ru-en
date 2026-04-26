#!/usr/bin/env python3
"""
Layer 06 v2: create full and prose_only Markdown variants.

No structure_only comparison is generated.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


LANG_SUFFIX_RE = re.compile(r"^(?P<sample_id>.+)_(?P<language>ru|en|mixed)\.md$")

URL_RE = re.compile(r"https?://\S+|www\.\S+")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
PATH_RE = re.compile(
    r"(?:(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+|"
    r"(?:[\w.-]+/)+[\w.-]+|"
    r"[\w.-]+\.(?:py|ts|tsx|js|jsx|json|md|txt|yaml|yml|toml|env|csv|html|css|sh|bash|zsh|lock|log))"
)
IDENTIFIER_RE = re.compile(
    r"\b(?:[A-Za-z]+_[A-Za-z0-9_]+|[A-Za-z]+[A-Z][A-Za-z0-9]*|[A-Z]{2,}[A-Z0-9_]*|[a-z]+-[a-z0-9-]+)\b"
)
COMMAND_PREFIX_RE = re.compile(
    r"^\s*(?:\$|>|python\b|pip\b|npm\b|pnpm\b|yarn\b|git\b|cd\b|mkdir\b|cp\b|mv\b|rm\b|grep\b|curl\b|export\b|source\b|pytest\b|uv\b|docker\b|npx\b|node\b|bun\b|poetry\b)"
)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


def split_fenced_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "\n", text, flags=re.DOTALL)


def strip_markdown_syntax(line: str) -> str:
    line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    line = re.sub(r"^\s{0,3}>\s?", "", line)
    line = re.sub(r"^\s*[-*+]\s+", "", line)
    line = re.sub(r"^\s*\d+[.)]\s+", "", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"\*([^*]+)\*", r"\1", line)
    line = re.sub(r"__([^_]+)__", r"\1", line)
    line = re.sub(r"_([^_]+)_", r"\1", line)
    line = line.replace("|", " ")
    return line


def prose_only(text: str) -> str:
    text = split_fenced_blocks(text)

    # Markdown links: keep visible text, drop URL.
    text = MARKDOWN_LINK_RE.sub(r"\1", text)

    # Drop inline code content.
    text = INLINE_CODE_RE.sub(" ", text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            lines.append("")
            continue

        if TABLE_SEPARATOR_RE.match(line):
            continue

        if COMMAND_PREFIX_RE.match(line):
            continue

        line = URL_RE.sub(" ", line)
        line = PATH_RE.sub(" ", line)
        line = IDENTIFIER_RE.sub(" ", line)

        line = strip_markdown_syntax(line)
        line = re.sub(r"[`*_~<>#{}\[\]();]", " ", line)
        line = re.sub(r"\s+", " ", line).strip()

        if line:
            lines.append(line)

    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result + "\n" if result else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/samples")
    parser.add_argument("--output-dir", default="data/decomposed_samples_v2")
    parser.add_argument("--exclude-sample", action="append", default=[])
    parser.add_argument("--metadata-output", default="results/markdown_decomposition_v2_metadata.json")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    metadata_path = Path(args.metadata_output)

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    excluded = set(args.exclude_sample)
    written: list[dict] = []

    for path in sorted(input_dir.glob("*.md")):
        match = LANG_SUFFIX_RE.match(path.name)
        if not match:
            continue

        sample_id = match.group("sample_id")
        language = match.group("language")

        if sample_id in excluded:
            continue

        text = path.read_text(encoding="utf-8")
        variants = {
            "full": text if text.endswith("\n") else text + "\n",
            "prose_only": prose_only(text),
        }

        for variant, variant_text in variants.items():
            out_path = output_dir / f"{sample_id}_{variant}_{language}.md"
            out_path.write_text(variant_text, encoding="utf-8")

            written.append(
                {
                    "source_path": str(path),
                    "output_path": str(out_path),
                    "sample_id": sample_id,
                    "language": language,
                    "variant": variant,
                    "source_chars": len(text),
                    "output_chars": len(variant_text),
                    "empty": not bool(variant_text.strip()),
                }
            )

    metadata = {
        "layer": "06_markdown_decomposition_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "excluded_samples": args.exclude_sample,
        "written_count": len(written),
        "written": written,
        "note": "Heuristic full/prose_only decomposition. No structure_only ratio comparison.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved decomposed samples to: {output_dir}")
    print(f"Saved metadata: {metadata_path}")
    print()
    print("| Sample | Lang | Variant | Chars | Empty | Output |")
    print("|---|---|---|---:|---|---|")
    for item in written:
        print(
            f"| {item['sample_id']} | {item['language']} | {item['variant']} | "
            f"{item['output_chars']} | {item['empty']} | {item['output_path']} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
