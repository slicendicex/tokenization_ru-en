#!/usr/bin/env python3
"""
Layer 07 — Gemini language-conditioned generation usage.

Requires:
    GEMINI_API_KEY
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

from google import genai
from google.genai import types


SYSTEM_TEXT = {
    "en": "You are a careful technical assistant. Follow the requested output format exactly. Do not add extra commentary.",
    "ru": "Ты внимательный технический ассистент. Точно соблюдай запрошенный формат ответа. Не добавляй лишние комментарии.",
}

CONDITIONS = [
    ("en_sys_en_in_en_out", "en", "en", "en"),
    ("ru_sys_en_in_en_out", "ru", "en", "en"),
    ("en_sys_ru_in_en_out", "en", "ru", "en"),
    ("en_sys_en_in_ru_out", "en", "en", "ru"),
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
            return "Напиши ровно 5 пунктов на русском языке. Каждый пункт должен содержать 12–18 слов. Не добавляй вступление, заключение и пояснения."
        return "Write exactly 5 bullet points in English. Each bullet must contain 12-18 words. Do not add an introduction, conclusion, or extra notes."

    if mode == "hidden_reasoning_json":
        if output_language == "ru":
            return 'Проанализируй документ и выбери 3 наиболее важных ограничения. Верни только JSON по схеме: {"constraints":["кратко","кратко","кратко"],"risk_level":"low|medium|high"}. Не добавляй пояснения вне JSON.'
        return 'Analyze the document and select the 3 most important constraints. Return only JSON using this schema: {"constraints":["short","short","short"],"risk_level":"low|medium|high"}. Do not add explanations outside JSON.'

    raise ValueError(f"Unsupported mode: {mode}")


def build_user_prompt(sample_text: str, input_language: str, output_language: str, mode: str) -> str:
    if output_language == "ru":
        doc_label = "ДОКУМЕНТ"
        intro = "Прочитай документ ниже."
    else:
        doc_label = "DOCUMENT"
        intro = "Read the document below."
    return f"{intro}\n\n{doc_label}:\n{sample_text}\n\n{output_instruction(output_language, mode)}"


def obj_to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    data = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if isinstance(value, (str, int, float, bool, type(None), list, dict)):
            data[name] = value
    return data or {"repr": repr(obj)}


def get_int(data: dict, *names: str) -> int:
    for name in names:
        value = data.get(name)
        if value is not None:
            try:
                return int(value)
            except Exception:
                pass
    return 0


def extract_usage(response: Any) -> dict:
    usage = getattr(response, "usage_metadata", None)
    data = obj_to_dict(usage)

    input_tokens = get_int(data, "prompt_token_count", "promptTokenCount")
    cached_input_tokens = get_int(data, "cached_content_token_count", "cachedContentTokenCount")
    visible_output_tokens = get_int(data, "candidates_token_count", "candidatesTokenCount")
    thinking_tokens = get_int(data, "thoughts_token_count", "thoughtsTokenCount")
    total_tokens = get_int(data, "total_token_count", "totalTokenCount")

    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "visible_output_tokens": visible_output_tokens,
        "hidden_reasoning_tokens": 0,
        "hidden_thinking_tokens": thinking_tokens,
        "output_tokens_total": visible_output_tokens + thinking_tokens,
        "total_tokens": total_tokens,
        "raw_usage_json": json.dumps(data, ensure_ascii=False, sort_keys=True),
    }


def ratios(row: dict) -> dict:
    visible = row.get("visible_output_tokens", 0) or 0
    input_tokens = row.get("input_tokens", 0) or 0
    reasoning = row.get("hidden_reasoning_tokens", 0) or 0
    thinking = row.get("hidden_thinking_tokens", 0) or 0
    total = row.get("total_tokens", 0) or 0
    return {
        "reasoning_to_visible_output": round(reasoning / visible, 6) if visible else "",
        "thinking_to_visible_output": round(thinking / visible, 6) if visible else "",
        "total_to_input": round(total / input_tokens, 6) if input_tokens else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="data/samples")
    parser.add_argument("--samples", nargs="+", default=["project_rules", "system_prompt"])
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--modes", nargs="+", choices=["fixed_output", "controlled_summary", "hidden_reasoning_json"], default=["fixed_output", "controlled_summary", "hidden_reasoning_json"])
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--thinking-budget", type=int, default=None, help="Optional Gemini thinking budget. Omit to use model default.")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--output", default="results/gemini_language_conditioned_usage_runs.csv")
    parser.add_argument("--metadata-output", default="results/gemini_language_conditioned_usage_metadata.json")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    samples_dir = Path(args.samples_dir)

    config_kwargs = {"max_output_tokens": args.max_output_tokens}
    if args.thinking_budget is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=args.thinking_budget)
    config = types.GenerateContentConfig(**config_kwargs)

    rows: list[dict] = []
    errors: list[dict] = []

    for model in args.models:
        for sample_id in args.samples:
            for condition, system_lang, input_lang, output_lang in CONDITIONS:
                sample_text = read_sample(samples_dir, sample_id, input_lang)
                if sample_text is None:
                    continue

                system_text = SYSTEM_TEXT[system_lang]

                for mode in args.modes:
                    user_prompt = build_user_prompt(sample_text, input_lang, output_lang, mode)

                    for run_index in range(args.runs):
                        try:
                            response = client.models.generate_content(
                                model=model,
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_text,
                                    max_output_tokens=args.max_output_tokens,
                                    thinking_config=types.ThinkingConfig(thinking_budget=args.thinking_budget) if args.thinking_budget is not None else None,
                                ),
                            )
                            usage = extract_usage(response)
                            output_text = getattr(response, "text", "") or ""
                        except Exception as exc:
                            err = {
                                "provider": "gemini",
                                "model": model,
                                "sample_id": sample_id,
                                "condition": condition,
                                "mode": mode,
                                "run_index": run_index,
                                "error": repr(exc),
                            }
                            errors.append(err)
                            print(f"ERROR: {err}")
                            if not args.continue_on_error:
                                raise
                            continue

                        row = {
                            "provider": "gemini",
                            "model": model,
                            "sample_id": sample_id,
                            "condition": condition,
                            "mode": mode,
                            "system_language": system_lang,
                            "input_language": input_lang,
                            "output_language": output_lang,
                            "run_index": run_index,
                            "thinking_budget": "" if args.thinking_budget is None else args.thinking_budget,
                            "prompt_chars": len(user_prompt) + len(system_text),
                            "prompt_words": word_count(user_prompt) + word_count(system_text),
                            "output_chars": len(output_text),
                            "output_words": word_count(output_text),
                            "output_preview": output_text[:500].replace("\n", "\\n"),
                            **usage,
                        }
                        row.update(ratios(row))
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
        "layer": "07_language_conditioned_usage_gemini",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": args.models,
        "samples": args.samples,
        "modes": args.modes,
        "runs": args.runs,
        "thinking_budget": args.thinking_budget,
        "errors": errors,
        "note": "Compares observable generation usage across system/input/output language conditions. Does not reveal language of hidden thinking.",
    }
    Path(args.metadata_output).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved runs: {args.output}")
    print(f"Saved metadata: {args.metadata_output}")
    print()
    print("| Provider | Model | Sample | Condition | Mode | Run | Input | Visible output | Thinking | Total |")
    print("|---|---|---|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| gemini | {r['model']} | {r['sample_id']} | {r['condition']} | {r['mode']} | {r['run_index']} | "
            f"{r['input_tokens']} | {r['visible_output_tokens']} | {r['hidden_thinking_tokens']} | {r['total_tokens']} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
