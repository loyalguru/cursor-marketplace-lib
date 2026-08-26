#!/usr/bin/env python3
"""Substitute {{vars}} and evaluate @expect rules against an HTTP response.

Substitution uses an allowlisted env subset only (never full os.environ).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlparse, urljoin

VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Always eligible for {{var}} substitution when present in the process env.
# Project auth maps_to names arrive via E2E_SUBST_ALLOW / E2E_AUTH_SUBST_ALLOW.
CORE_KEYS = frozenset(
    {
        "baseUrl",
        "smokePath",
        "URL",
        "SMOKE_PATH",
    }
)


def subst_env() -> dict[str, str]:
    """Build the map used for {{var}} replacement (allowlist only)."""
    allow: set[str] = set(CORE_KEYS)
    for env_name in ("E2E_SUBST_ALLOW", "E2E_AUTH_SUBST_ALLOW"):
        raw = os.environ.get(env_name, "")
        if raw.strip():
            for part in raw.split(","):
                name = part.strip()
                if SAFE_NAME.fullmatch(name):
                    allow.add(name)

    out: dict[str, str] = {}
    for name in allow:
        if name in os.environ:
            out[name] = os.environ[name]
    return out


def substitute(template: str, env: dict[str, str]) -> str:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in env or env[name] == "":
            missing.append(name)
            return match.group(0)
        return env[name]

    output = VAR_RE.sub(replace, template)
    if missing:
        names = ", ".join(sorted(set(missing)))
        raise ValueError(f"unresolved or empty variables: {names}")
    return output


def jsonpath_get(data: Any, path: str) -> Any:
    if not path.startswith("$"):
        raise ValueError(f"jsonpath must start with $: {path}")
    current = data
    if path == "$":
        return current
    tokens = re.findall(
        r"\.(?P<key>[A-Za-z_][A-Za-z0-9_]*)|\[(?P<idx>\d+)\]", path
    )
    if not tokens:
        raise ValueError(f"unsupported jsonpath: {path}")
    for key, index in tokens:
        if key:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(path)
            current = current[key]
            continue
        item = int(index)
        if not isinstance(current, list) or item >= len(current):
            raise KeyError(path)
        current = current[item]
    return current


def parse_literal(raw: str) -> Any:
    raw = raw.strip()
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    raise ValueError(f"unsupported literal: {raw}")


def check_expects(status: int, body: str, expects: list[dict]) -> tuple[bool, str]:
    try:
        data = json.loads(body) if body.strip() else None
    except json.JSONDecodeError as error:
        return False, f"response is not JSON: {error}"

    for expect in expects:
        kind = expect["kind"]
        if kind == "status":
            expected_status = int(expect["status"])
            if status != expected_status:
                return False, f"status {status} != {expected_status}"
            continue
        if data is None:
            return False, "empty JSON body"

        path = expect["path"]
        try:
            actual = jsonpath_get(data, path)
        except (KeyError, ValueError) as error:
            return False, f"jsonpath {path}: {error}"

        if kind == "length":
            expected_length = int(expect["length"])
            if not isinstance(actual, (list, dict)):
                return False, f"{path} length: not a list/object"
            if len(actual) != expected_length:
                return False, f"{path} length {len(actual)} != {expected_length}"
            continue
        if kind == "eq":
            expected = parse_literal(expect["value"])
            if actual != expected:
                return False, f"{path}: {actual!r} != {expected!r}"
            continue
        return False, f"unknown expect kind {kind}"
    return True, "ok"


def same_origin(base_url: str, request_url: str) -> None:
    """Reject URLs that are not http(s) under the configured preview base."""
    base = urlparse(base_url)
    if base.scheme not in ("http", "https") or not base.netloc:
        raise ValueError(f"invalid baseUrl: {base_url!r}")

    raw = request_url.strip()
    if raw.startswith("/"):
        resolved = urlparse(urljoin(base_url.rstrip("/") + "/", raw.lstrip("/")))
    else:
        resolved = urlparse(raw)

    if resolved.scheme not in ("http", "https"):
        raise ValueError(f"refusing non-http(s) URL: {request_url!r}")
    if resolved.username or resolved.password:
        raise ValueError("refusing URL with embedded credentials")
    if resolved.netloc.lower() != base.netloc.lower():
        raise ValueError(
            f"refusing URL host {resolved.netloc!r}; must match baseUrl host "
            f"{base.netloc!r}"
        )


def redact_for_log(text: str, limit: int = 160) -> str:
    """Omit response bodies from logs; keep a short non-sensitive marker."""
    if not text:
        return "(empty)"
    return f"(body {len(text)} bytes omitted)"


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "substitute":
        try:
            sys.stdout.write(substitute(sys.stdin.read(), subst_env()))
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        return 0
    if command == "assert":
        status = int(sys.argv[2])
        expects = json.loads(sys.argv[3])
        ok, message = check_expects(status, sys.stdin.read(), expects)
        print(message)
        return 0 if ok else 1
    if command == "check-url":
        if len(sys.argv) != 4:
            print("usage: check-url <baseUrl> <requestUrl>", file=sys.stderr)
            return 2
        try:
            same_origin(sys.argv[2], sys.argv[3])
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        return 0
    if command == "redact-log":
        print(redact_for_log(sys.stdin.read()))
        return 0
    print(
        "usage: substitute_and_assert.py substitute|assert|check-url|redact-log ...",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
