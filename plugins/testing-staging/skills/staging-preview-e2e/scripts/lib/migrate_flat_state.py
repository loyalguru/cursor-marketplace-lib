#!/usr/bin/env python3
"""One-shot migration: flat state/ → state/{repo}/."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ENV_KEYS = ("API_KEY", "SECRET_KEY", "AUTH_HEADER_KEY", "AUTH_HEADER_SECRET")
ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ENV_LINE.match(line.strip())
        if not match:
            continue
        out[match.group(1)] = match.group(2)
    return out


def write_project_env(path: Path, env: dict[str, str]) -> None:
    lines: list[str] = []
    for key in ENV_KEYS:
        if key not in env:
            if key in ("API_KEY", "SECRET_KEY"):
                lines.append(f"{key}=")
            continue
        lines.append(f"{key}={env[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_preview_json(fixtures: dict, env: dict[str, str]) -> dict:
    data = dict(fixtures) if isinstance(fixtures, dict) else {}
    url = env.get("URL", "").strip()
    if url:
        data["baseUrl"] = url

    gcp: dict[str, str] = {}
    for json_key, env_key in (
        ("project", "GCP_PROJECT"),
        ("region", "GCP_REGION"),
        ("service", "GCP_SERVICE"),
    ):
        value = env.get(env_key, "").strip()
        if value:
            gcp[json_key] = value
    if gcp:
        data["gcp"] = gcp
    return data


def remove_flat(state_root: Path) -> None:
    flat_env = state_root / ".env"
    flat_vars = state_root / "variables" / "preview.json"
    flat_preview_env = state_root / "preview.env"
    vars_dir = state_root / "variables"

    if flat_env.is_file():
        flat_env.unlink()
        print(f"Removed {flat_env}")
    if flat_vars.is_file():
        flat_vars.unlink()
        print(f"Removed {flat_vars}")
    if vars_dir.is_dir():
        try:
            next(vars_dir.iterdir())
        except StopIteration:
            vars_dir.rmdir()
            print(f"Removed {vars_dir}")
    if flat_preview_env.is_file():
        flat_preview_env.unlink()
        print(f"Removed {flat_preview_env}")


def migrate(state_root: Path, project_dir: Path) -> int:
    flat_env = state_root / ".env"
    flat_vars = state_root / "variables" / "preview.json"
    flat_preview_env = state_root / "preview.env"
    has_flat = flat_env.is_file() or flat_vars.is_file() or flat_preview_env.is_file()

    if not has_flat:
        return 0

    dest_env = project_dir / ".env"
    dest_vars = project_dir / "variables" / "preview.json"
    project_exists = dest_env.is_file() or dest_vars.is_file()

    if project_exists:
        # Do not overwrite project state; only drop leftover flat files.
        print(f"Project state already exists at {project_dir}; skipping overwrite")
        remove_flat(state_root)
        return 0

    env = parse_env(flat_env)
    fixtures: dict = {}
    if flat_vars.is_file():
        loaded = json.loads(flat_vars.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            fixtures = loaded

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "variables").mkdir(parents=True, exist_ok=True)

    write_project_env(dest_env, env)
    print(f"Migrated credentials → {dest_env}")

    merged = build_preview_json(fixtures, env)
    dest_vars.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Migrated variables → {dest_vars}")

    remove_flat(state_root)
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: migrate_flat_state.py <state-root> <project-state-dir>",
            file=sys.stderr,
        )
        return 2
    return migrate(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
