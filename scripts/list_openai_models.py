#!/usr/bin/env python3
"""
List OpenAI models available to the current API key.

Usage:
    python scripts/list_openai_models.py --contains gpt-5
"""

from __future__ import annotations

import argparse
from openai import OpenAI


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contains", default="", help="Only print model IDs containing this substring.")
    args = parser.parse_args()

    client = OpenAI()
    models = client.models.list()

    ids = sorted(m.id for m in models.data)
    if args.contains:
        ids = [model_id for model_id in ids if args.contains in model_id]

    for model_id in ids:
        print(model_id)


if __name__ == "__main__":
    main()
