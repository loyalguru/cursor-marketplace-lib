#!/usr/bin/env python3
"""Flatten nested e2e variables JSON to KEY/VALUE pairs for bash export.

Security:
  - JSON object keys / path segments must be safe identifiers
  - Output uses NUL-delimited records (no shell eval)
  - --dotenv mode still rejects unsafe keys
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

SAFE_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def path_to_var(parts: list[str]) -> str:
    if not parts:
        return ""
    for part in parts:
        if not SAFE_SEGMENT.fullmatch(part):
            raise ValueError(
                f"unsafe variables JSON key segment: {part!r} "
                "(use letters, digits, underscore only)"
            )
    out = parts[0]
    for part in parts[1:]:
        if part:
            out += part[0].upper() + part[1:]
    if not SAFE_KEY.fullmatch(out):
        raise ValueError(f"unsafe flattened variable name: {out!r}")
    return out


def flatten(obj: Any, parts: list[str] | None = None) -> dict[str, str]:
    parts = parts or []
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.update(flatten(value, parts + [str(key)]))
        return out

    name = path_to_var(parts)
    if not name:
        return out
    if obj is None:
        out[name] = ""
    elif isinstance(obj, bool):
        out[name] = "true" if obj else "false"
    elif isinstance(obj, (dict, list)):
        raise ValueError(f"unsupported nested container at {name}")
    else:
        # Scalars only; reject embedded NULs for shell/env safety.
        text = str(obj)
        if "\0" in text:
            raise ValueError(f"NUL byte in variable {name}")
        out[name] = text
    return out


def main() -> int:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(
            "usage: flatten_variables.py <preview.json> [--dotenv|--null]",
            file=sys.stderr,
        )
        return 2

    mode = "assign"
    if len(sys.argv) == 3:
        if sys.argv[2] == "--dotenv":
            mode = "dotenv"
        elif sys.argv[2] == "--null":
            mode = "null"
        else:
            print("unknown mode; use --dotenv or --null", file=sys.stderr)
            return 2

    with open(sys.argv[1], encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        print("variables JSON root must be an object", file=sys.stderr)
        return 2

    try:
        flat = flatten(data)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    for key, value in sorted(flat.items()):
        if mode == "dotenv":
            safe = value.replace("\n", "\\n")
            print(f"{key}={safe}")
        elif mode == "null":
            sys.stdout.buffer.write(key.encode("utf-8") + b"\0")
            sys.stdout.buffer.write(value.encode("utf-8") + b"\0")
        else:
            # Legacy quoted form kept for debugging; prefer --null in bash.
            escaped = value.replace("'", "'\"'\"'")
            print(f"{key}='{escaped}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
