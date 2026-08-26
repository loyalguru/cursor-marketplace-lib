#!/usr/bin/env python3
"""Build curl auth flags from auth.manifest.json + process env.

Output lines (tab-separated), no secrets beyond the values needed for curl:
  H<TAB>Header-Name<TAB>Header-Value
  U<TAB>user:password

Used by preflight (L0) and run.sh (optional inject on every request).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def resolve(name: str) -> str:
    return os.environ.get(name, "")


def emit_auth(
    manifest: dict,
    *,
    include_default_headers: bool = True,
    include_smoke: bool = True,
    skip_header_names: set[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Return list of (kind, a, b) where kind is H or U."""
    skip = {n.lower() for n in (skip_header_names or set())}
    out: list[tuple[str, str, str]] = []

    if include_default_headers:
        for h in manifest.get("default_headers") or []:
            name = h["name"]
            if name.lower() in skip:
                continue
            out.append(("H", name, h["value"]))
            skip.add(name.lower())

    if not include_smoke:
        return out

    smoke = manifest.get("smoke") or {}
    basic = smoke.get("basic")
    if basic:
        # Skip -u if caller already set Authorization
        if "authorization" not in skip:
            user = resolve(basic["user_from"])
            password = resolve(basic["password_from"])
            if not user or not password:
                raise SystemExit("basic auth user/password empty in env")
            out.append(("U", f"{user}:{password}", ""))

    for item in smoke.get("headers") or []:
        if "name_from" in item:
            header_name = resolve(item["name_from"])
        else:
            header_name = item.get("name", "")
        if "value_from" in item:
            raw_val = resolve(item["value_from"])
        else:
            raw_val = item.get("value", "")
        prefix = item.get("value_prefix") or ""
        header_value = f"{prefix}{raw_val}"
        when = item.get("when")
        if when == "set" and not raw_val:
            continue
        if not header_name:
            raise SystemExit("missing smoke header name")
        if header_name.lower() in skip:
            continue
        if not header_value and when != "set":
            raise SystemExit(f"empty smoke header {header_name!r}")
        out.append(("H", header_name, header_value))
        skip.add(header_name.lower())

    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: build_curl_auth.py <auth.manifest.json> "
            "[--no-defaults] [--skip-names name1,name2]",
            file=sys.stderr,
        )
        return 2

    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    include_defaults = True
    skip: set[str] = set()
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--no-defaults":
            include_defaults = False
            i += 1
        elif args[i] == "--skip-names" and i + 1 < len(args):
            skip = {n.strip() for n in args[i + 1].split(",") if n.strip()}
            i += 2
        else:
            print(f"unknown arg: {args[i]}", file=sys.stderr)
            return 2

    try:
        rows = emit_auth(
            manifest,
            include_default_headers=include_defaults,
            include_smoke=True,
            skip_header_names=skip,
        )
    except SystemExit as error:
        print(f"ERROR\t{error}", file=sys.stderr)
        return 1

    for kind, a, b in rows:
        if kind == "H":
            print(f"H\t{a}\t{b}")
        else:
            print(f"U\t{a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
