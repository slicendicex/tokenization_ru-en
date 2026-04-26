#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from google import genai


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contains", default="", help="Only print model names containing this substring.")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    try:
        models = client.models.list()
    except Exception as exc:
        print(f"Could not list models: {exc}")
        print("Try documented model IDs instead:")
        print("gemini-2.5-flash")
        print("gemini-2.5-flash-lite")
        print("gemini-3-flash-preview")
        print("gemini-3.1-flash-lite-preview")
        return

    names = []
    for model in models:
        name = getattr(model, "name", None) or getattr(model, "id", None)
        if not name:
            continue
        if name.startswith("models/"):
            name = name.removeprefix("models/")
        names.append(name)

    names = sorted(set(names))
    if args.contains:
        names = [name for name in names if args.contains in name]

    for name in names:
        print(name)


if __name__ == "__main__":
    main()
