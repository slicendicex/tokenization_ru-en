#!/usr/bin/env python3
"""
Layer 07.1 — OpenAI full factorial language-conditioned usage.

Runs all 8 combinations:

system_language × input_language × output_language

Default:
- model: provided by --models
- sample: system_prompt
- mode: controlled_summary
- runs: 20
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


SYSTEM_TEXT = {
    "en": "You are a careful technical assistant. Follow the requested output format exactly. Do not add extra commentary.",
    "ru": "Ты внимательный технический ассистент. Точно соблюдай запрошенный формат ответа. Не добавляй лишние комментарии.",
}

# Full 2x2x2 factorial design.
CONDITIONS = [
    ("en_sys_en_in_en_out", "en", "en", "en"),
    ("ru_sys_en_in_en_out", "ru", "en", "en"),
    ("en_sys_ru_in_en_out", "en", "ru", "en"),
    ("en_sys_en_in_ru_out", "en", "en", "ru"),
    ("ru_sys_ru_in_en_out", "ru", "ru", "en"),
    ("ru_sys_en_in_ru_out", "ru", "en", "ru"),
    ("en_sys_ru_in_ru_out", "en", "ru", "ru"),
    ("ru_sys_ru_in_ru_out", "ru", "ru", "ru"),
]


def word_count(text: str) -> int:
    return len(re.findall(r"[^\W_]+(?:[-'][^\W_]+)?", text, flags=re.UNICODE))


def read_sample(samples_dir: Path, sample_id: str, lang: str) -> str | None:
    path = samples_dir / f"{sample_id}_{lang}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def output_instruction(output_language: str, mode: str) -> str:
    if mode == "fixed_output":
        return 'Return exactly this JSON and nothing else: {"ok":true}'

    if mode == "controlled_summary":
        if output_language == "ru":
            return (
                "Напиши ровно 5 пунктов на русском языке. "
                "Каждый пункт должен содержать 12–18 слов. "
                "Не добавляй вступление, заключение и пояснения."
            )
        return (
            "Write exactly 5 bullet points in English. "
            "Each bullet must contain 12-18 words. "
            "Do not add an introduction, conclusion, or extra notes."
        )

    if mode == "hidden_reasoning_json":
        if output_language == "ru":
            return (
                "Проанализируй документ и выбери 3 наиболее важных ограничения. "
                "Верни только JSON по схеме: "
                '{"constraints":["кратко","кратко","кратко"],"risk_level":"low|medium|high"}. '
                "Не добавляй пояснения вне JSON."
            )
        return (
            "Analyze the document and select the 3 most important constraints. "
            "Return only JSON using this schema: "
            '{"constraints":["short","short","short"],"risk_level":"low|medium|high"}. '
            "Do not add explanations outside JSON."
        )

    raise ValueError(f"Unsupported mode: {mode}")


def build_user_prompt(sample_text: str, output_language: str, mode: str) -> str:
    if output_language == "ru":
        return (
            "Прочитай документ ниже.\n\n"
            f"ДОКУМЕНТ:\n{sample_text}\n\n"
            f"{output_instruction(output_language, mode)}"
        )

    return (
        "Read the document below.\n\n"
        f"DOCUMENT:\n{sample_text}\n\n"
        f"{output_instruction(output_language, mode)}"
    )


def obj_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


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

    input_tokens = int(obj_get(usage, "input_tokens", 0) or 0)
    output_tokens_total = int(obj_get(usage, "output_tokens", 0) or 0)
    total_tokens = int(obj_get(usage, "total_tokens", 0) or 0)

    input_details = obj_get(usage, "input_tokens_details", None)
    cached_input_tokens = int(obj_get(input_details, "cached_tokens", 0) or 0)

    output_details = obj_get(usage, "output_tokens_details", None)
    reasoning_tokens = int(obj_get(output_details, "reasoning_tokens", 0) or 0)

    visible_output_tokens = max(output_tokens_total - reasoning_tokens, 0)

    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "visible_output_tokens": visible_output_tokens,
        "hidden_reasoning_tokens": reasoning_tokens,
        "hidden_thinking_tokens": 0,
        "output_tokens_total": output_tokens_total,
        "total_tokens": total_tokens,
        "raw_usage_json": json.dumps(obj_to_dict(usage), ensure_ascii=False, sort_keys=True),
    }


def ratio_fields(row: dict) -> dict:
    visible = row.get("visible_output_tokens", 0) or 0
    input_tokens = row.get("input_tokens", 0) or 0
    reasoning = row.get("hidden_reasoning_tokens", 0) or 0
    total = row.get("total_tokens", 0) or 0

    return {
        "reasoning_to_visible_output": round(reasoning / visible, 6) if visible else "",
        "total_to_input": round(total / input_tokens, 6) if input_tokens else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--samples", nargs="+", default=["system_prompt"])
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--mode", choices=["fixed_output", "controlled_summary", "hidden_reasoning_json"], default="controlled_summary")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--output", default="results/openai_full_factorial_usage_runs.csv")
    parser.add_argument("--metadata-output", default="results/openai_full_factorial_usage_metadata.json")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("ERROR: OPENAI_API_KEY is not set.")

    client = OpenAI()
    samples_dir = Path(args.samples_dir)

    rows: list[dict] = []
    errors: list[dict] = []

    for model in args.models:
        for sample_id in args.samples:
            for condition, system_lang, input_lang, output_lang in CONDITIONS:
                sample_text = read_sample(samples_dir, sample_id, input_lang)
                if sample_text is None:
                    errors.append(
                        {
                            "model": model,
                            "sample_id": sample_id,
                            "condition": condition,
                            "error": f"missing sample file for language: {input_lang}",
                        }
                    )
                    continue

                system_text = SYSTEM_TEXT[system_lang]
                user_prompt = build_user_prompt(sample_text, output_lang, args.mode)

                for run_index in range(args.runs):
                    try:
                        response = client.responses.create(
                            model=model,
                            instructions=system_text,
                            input=user_prompt,
                            reasoning={"effort": args.reasoning_effort},
                            max_output_tokens=args.max_output_tokens,
                        )
                        usage = extract_usage(response)
                        output_text = getattr(response, "output_text", "") or ""
                    except Exception as exc:
                        err = {
                            "provider": "openai",
                            "model": model,
                            "sample_id": sample_id,
                            "condition": condition,
                            "mode": args.mode,
                            "run_index": run_index,
                            "error": repr(exc),
                        }
                        errors.append(err)
                        print(f"ERROR: {err}")
                        if not args.continue_on_error:
                            raise
                        continue

                    row = {
                        "provider": "openai",
                        "model": model,
                        "sample_id": sample_id,
                        "condition": condition,
                        "mode": args.mode,
                        "system_language": system_lang,
                        "input_language": input_lang,
                        "output_language": output_lang,
                        "run_index": run_index,
                        "reasoning_effort": args.reasoning_effort,
                        "prompt_chars": len(user_prompt) + len(system_text),
                        "prompt_words": word_count(user_prompt) + word_count(system_text),
                        "output_chars": len(output_text),
                        "output_words": word_count(output_text),
                        "output_preview": output_text[:500].replace("\n", "\\n"),
                        **usage,
                    }
                    row.update(ratio_fields(row))
                    rows.append(row)

                    if args.sleep:
                        time.sleep(args.sleep)

    if not rows:
        raise SystemExit("ERROR: no rows generated.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "layer": "07_1_full_factorial_openai_usage",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "samples": args.samples,
        "mode": args.mode,
        "runs": args.runs,
        "reasoning_effort": args.reasoning_effort,
        "conditions": [
            {
                "condition": c,
                "system_language": s,
                "input_language": i,
                "output_language": o,
            }
            for c, s, i, o in CONDITIONS
        ],
        "errors": errors,
        "note": "Full 2x2x2 language-conditioned usage design. Does not reveal hidden reasoning language.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved runs: {args.output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("| Model | Sample | Mode | Condition | Run | Input | Visible output | Reasoning | Output total | Total |")
    print("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['model']} | {r['sample_id']} | {r['mode']} | {r['condition']} | {r['run_index']} | "
            f"{r['input_tokens']} | {r['visible_output_tokens']} | {r['hidden_reasoning_tokens']} | "
            f"{r['output_tokens_total']} | {r['total_tokens']} |"
        )

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
