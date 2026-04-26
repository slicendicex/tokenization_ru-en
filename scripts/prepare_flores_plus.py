#!/usr/bin/env python3
"""
Prepare RU/EN FLORES+ samples for tokenization experiments.

Default output:
- data/samples/flores_ru.md
- data/samples/flores_en.md
- data/samples/flores_ru_en.jsonl
- data/samples/flores_metadata.json

Prerequisites:
    pip install datasets huggingface_hub
    hf auth login

Or set:
    export HF_TOKEN="..."
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List

from datasets import load_dataset


DATASET_NAME = "openlanguagedata/flores_plus"
EN_CONFIG = "eng_Latn"
RU_CONFIG = "rus_Cyrl"


def load_lang(config: str, split: str, token: str | bool | None):
    return load_dataset(DATASET_NAME, config, split=split, token=token)


def build_by_id(rows: Iterable[dict]) -> Dict[str, dict]:
    return {str(row["id"]): row for row in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["dev", "devtest"])
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out-dir", default="data/samples")
    parser.add_argument("--format", default="md", choices=["md", "txt"])
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    token_env = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    token: str | bool | None = token_env if token_env else True

    print(f"Loading {DATASET_NAME} / {EN_CONFIG} / split={args.split}")
    en_rows = list(load_lang(EN_CONFIG, args.split, token))
    print(f"Loading {DATASET_NAME} / {RU_CONFIG} / split={args.split}")
    ru_rows = list(load_lang(RU_CONFIG, args.split, token))

    en_by_id = build_by_id(en_rows)
    ru_by_id = build_by_id(ru_rows)

    common_ids = sorted(set(en_by_id) & set(ru_by_id), key=lambda x: int(x) if x.isdigit() else x)
    selected_ids = common_ids[: args.limit]

    pairs: List[dict] = []
    for row_id in selected_ids:
        en = en_by_id[row_id]
        ru = ru_by_id[row_id]
        pairs.append(
            {
                "id": row_id,
                "split": args.split,
                "en": en["text"],
                "ru": ru["text"],
                "en_domain": en.get("domain"),
                "en_topic": en.get("topic"),
                "ru_domain": ru.get("domain"),
                "ru_topic": ru.get("topic"),
            }
        )

    ext = args.format
    (out_dir / f"flores_en.{ext}").write_text("\n".join(pair["en"] for pair in pairs) + "\n", encoding="utf-8")
    (out_dir / f"flores_ru.{ext}").write_text("\n".join(pair["ru"] for pair in pairs) + "\n", encoding="utf-8")

    with (out_dir / "flores_ru_en.jsonl").open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    metadata = {
        "dataset": DATASET_NAME,
        "version_note": "Record the exact dataset version from Hugging Face at article publication time.",
        "split": args.split,
        "limit": args.limit,
        "format": ext,
        "en_config": EN_CONFIG,
        "ru_config": RU_CONFIG,
        "pair_count": len(pairs),
        "first_id": selected_ids[0] if selected_ids else None,
        "last_id": selected_ids[-1] if selected_ids else None,
        "outputs": [f"flores_en.{ext}", f"flores_ru.{ext}", "flores_ru_en.jsonl"],
    }
    (out_dir / "flores_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved {len(pairs)} aligned pairs to {out_dir}")


if __name__ == "__main__":
    main()
