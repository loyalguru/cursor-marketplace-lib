#!/usr/bin/env python3
"""Resolve per-project state slug from a git remote origin URL.

Slug is the repository name only (no owner), without .git.
"""

from __future__ import annotations

import re
import sys


def repo_slug_from_origin(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("empty origin URL")

    # git@host:owner/repo.git  |  ssh://git@host/owner/repo.git
    # https://host/owner/repo.git  |  https://host/owner/repo
    cleaned = raw.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[: -len(".git")]

    # Prefer last path segment after / or :
    match = re.search(r"[:/]([^:/]+)$", cleaned)
    if not match:
        raise ValueError(f"cannot parse repo name from origin: {url!r}")

    slug = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", slug):
        raise ValueError(f"unsafe repo slug: {slug!r}")
    if slug in (".", ".."):
        raise ValueError(f"unsafe repo slug: {slug!r}")
    return slug


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: resolve_project.py <origin-url>", file=sys.stderr)
        return 2
    try:
        print(repo_slug_from_origin(sys.argv[1]))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
