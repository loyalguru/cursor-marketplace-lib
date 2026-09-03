#!/usr/bin/env python3
"""Decide whether to reuse an existing preview or trigger a redeploy.

Prints KEY=value lines for the agent / bash. Does not call GitHub or gcloud.

Rules (see references/preview-deployment.md):
  - Redeploy if there is no successful deploy timestamp.
  - Redeploy if deploy_at < last_commit_at (preview missing newer commits).
  - Redeploy if now is on/after today's PREVIEW_SHUTDOWN_HOUR in PREVIEW_TZ
    and deploy_at is before that shutdown instant (daily preview teardown).
  - Redeploy if --smoke-failed (L0 already proved the candidate URL is down).
  - Otherwise reuse.

--force-reuse skips timestamp rules (user said preview is already up); smoke
still decides via --smoke-failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


def parse_instant(raw: str) -> datetime:
    """Parse an ISO-8601 instant to aware UTC datetime."""
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def shutdown_instant(now_utc: datetime, tz_name: str, hour: int) -> datetime:
    """Return today's shutdown boundary as UTC for the local calendar day of now."""
    if not (0 <= hour <= 23):
        raise ValueError(f"shutdown hour must be 0-23, got {hour}")
    local_tz = ZoneInfo(tz_name)
    local_now = now_utc.astimezone(local_tz)
    local_shutdown = datetime.combine(
        local_now.date(), time(hour=hour), tzinfo=local_tz
    )
    return local_shutdown.astimezone(timezone.utc)


@dataclass(frozen=True)
class Decision:
    action: str  # reuse | redeploy
    reason: str
    last_commit_at: str | None
    deploy_at: str | None
    shutdown_at: str | None
    now: str


def decide(
    *,
    last_commit_at: datetime | None,
    deploy_at: datetime | None,
    now: datetime,
    tz_name: str,
    shutdown_hour: int,
    force_reuse: bool = False,
    smoke_failed: bool = False,
) -> Decision:
    now_utc = now.astimezone(timezone.utc)
    shutdown_at = shutdown_instant(now_utc, tz_name, shutdown_hour)
    fmt = lambda dt: dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    base = dict(
        last_commit_at=fmt(last_commit_at) if last_commit_at else None,
        deploy_at=fmt(deploy_at) if deploy_at else None,
        shutdown_at=fmt(shutdown_at),
        now=fmt(now_utc),
    )

    if smoke_failed:
        return Decision(action="redeploy", reason="smoke_failed", **base)

    if force_reuse:
        return Decision(action="reuse", reason="force_reuse", **base)

    if deploy_at is None:
        return Decision(action="redeploy", reason="no_deploy_comment", **base)

    if last_commit_at is not None and deploy_at < last_commit_at:
        return Decision(action="redeploy", reason="commits_after_deploy", **base)

    if now_utc >= shutdown_at and deploy_at < shutdown_at:
        return Decision(action="redeploy", reason="post_shutdown_required", **base)

    return Decision(action="reuse", reason="preview_covers_head", **base)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--last-commit-at",
        help="ISO-8601 time of the PR head commit (UTC preferred)",
    )
    parser.add_argument(
        "--deploy-at",
        help="ISO-8601 time of the latest successful preview deploy comment",
    )
    parser.add_argument(
        "--now",
        help="ISO-8601 'now' override (tests); default: current UTC",
    )
    parser.add_argument(
        "--tz",
        default="Europe/Madrid",
        help="IANA timezone for the daily shutdown clock (default Europe/Madrid)",
    )
    parser.add_argument(
        "--shutdown-hour",
        type=int,
        default=18,
        help="Local hour (0-23) when previews are torn down (default 18)",
    )
    parser.add_argument(
        "--force-reuse",
        action="store_true",
        help="User confirmed preview is already deployed; skip timestamp rules",
    )
    parser.add_argument(
        "--smoke-failed",
        action="store_true",
        help="L0 smoke against the candidate URL already failed",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of KEY=value lines",
    )
    args = parser.parse_args(argv)

    last_commit = (
        parse_instant(args.last_commit_at) if args.last_commit_at else None
    )
    deploy = parse_instant(args.deploy_at) if args.deploy_at else None
    now = parse_instant(args.now) if args.now else datetime.now(timezone.utc)

    try:
        decision = decide(
            last_commit_at=last_commit,
            deploy_at=deploy,
            now=now,
            tz_name=args.tz,
            shutdown_hour=args.shutdown_hour,
            force_reuse=args.force_reuse,
            smoke_failed=args.smoke_failed,
        )
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    payload = {
        "ACTION": decision.action,
        "REASON": decision.reason,
        "LAST_COMMIT_AT": decision.last_commit_at or "",
        "DEPLOY_AT": decision.deploy_at or "",
        "SHUTDOWN_AT": decision.shutdown_at or "",
        "NOW": decision.now,
    }

    if args.json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        for key in (
            "ACTION",
            "REASON",
            "LAST_COMMIT_AT",
            "DEPLOY_AT",
            "SHUTDOWN_AT",
            "NOW",
        ):
            print(f"{key}={payload[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
