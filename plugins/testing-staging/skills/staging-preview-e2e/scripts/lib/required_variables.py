#!/usr/bin/env python3
"""List non-auth {{variables}} referenced by allowlisted .http files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

# Always treated as supplied by runner / skill defaults (not fixtures).
BASE_AUTH_VARS = frozenset(
    {
        "baseUrl",
        "smokePath",
        "URL",
    }
)


def load_manifest_maps(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for cred in data.get("credentials") or []:
        maps_to = cred.get("maps_to")
        key = cred.get("key")
        if isinstance(maps_to, str):
            out.add(maps_to)
        if isinstance(key, str):
            out.add(key)
    for name in data.get("session_variables") or []:
        if isinstance(name, str):
            out.add(name)
    return out


def main() -> int:
    args = sys.argv[1:]
    manifest_path: Path | None = None
    if len(args) >= 2 and args[0] == "--manifest":
        manifest_path = Path(args[1])
        args = args[2:]

    if not args:
        print(
            "usage: required_variables.py [--manifest auth.manifest.json] <file.http>...",
            file=sys.stderr,
        )
        return 2

    auth_vars = set(BASE_AUTH_VARS) | load_manifest_maps(manifest_path)

    names: set[str] = set()
    for raw in args:
        path = Path(raw)
        text = path.read_text(encoding="utf-8")
        names.update(VAR_RE.findall(text))

    for name in sorted(names - auth_vars):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
