#!/usr/bin/env python3
"""
List Anthropic Claude models available via the current API key.

Usage:
    python scripts/list_claude_models.py

Notes:
- Requires ANTHROPIC_API_KEY.
- If the SDK/account does not support listing, use model IDs from Anthropic docs.
"""

from __future__ import annotations

import argparse
from anthropic import Anthropic


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contains", default="", help="Only print model IDs containing this substring.")
    args = parser.parse_args()

    client = Anthropic()

    try:
        models = client.models.list()
    except Exception as exc:
        print(f"Could not list models: {exc}")
        print()
        print("Use documented model IDs instead, for example:")
        print("claude-opus-4-7")
        print("claude-sonnet-4-6")
        print("claude-haiku-4-5")
        return

    data = getattr(models, "data", models)
    ids = []
    for model in data:
        model_id = getattr(model, "id", None)
        if model_id:
            ids.append(model_id)

    ids = sorted(ids)
    if args.contains:
        ids = [model_id for model_id in ids if args.contains in model_id]

    for model_id in ids:
        print(model_id)


if __name__ == "__main__":
    main()
