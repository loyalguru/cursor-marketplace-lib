#!/usr/bin/env python3
"""Unit tests for decide_preview (run: python3 scripts/lib/test_decide_preview.py)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Allow running as a script from any cwd.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decide_preview import decide, parse_instant, shutdown_instant  # noqa: E402


class DecidePreviewTest(unittest.TestCase):
    TZ = "Europe/Madrid"

    def test_no_deploy_redeploys(self) -> None:
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:00:00Z"),
            deploy_at=None,
            now=parse_instant("2026-08-03T12:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
        )
        self.assertEqual(d.action, "redeploy")
        self.assertEqual(d.reason, "no_deploy_comment")

    def test_commits_after_deploy_redeploys(self) -> None:
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:44:00Z"),
            deploy_at=parse_instant("2026-08-03T07:30:00Z"),
            now=parse_instant("2026-08-03T12:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
        )
        self.assertEqual(d.action, "redeploy")
        self.assertEqual(d.reason, "commits_after_deploy")

    def test_preview_covers_head_reuses_before_shutdown(self) -> None:
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:44:00Z"),
            deploy_at=parse_instant("2026-08-03T10:00:00Z"),
            now=parse_instant("2026-08-03T12:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
        )
        self.assertEqual(d.action, "reuse")
        self.assertEqual(d.reason, "preview_covers_head")

    def test_after_shutdown_without_post_shutdown_deploy_redeploys(self) -> None:
        # 19:00 Madrid in August = 17:00 UTC
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:44:00Z"),
            deploy_at=parse_instant("2026-08-03T10:00:00Z"),  # before 18:00 Madrid
            now=parse_instant("2026-08-03T17:00:00Z"),  # 19:00 Madrid
            tz_name=self.TZ,
            shutdown_hour=18,
        )
        self.assertEqual(d.action, "redeploy")
        self.assertEqual(d.reason, "post_shutdown_required")

    def test_after_shutdown_with_fresh_deploy_reuses(self) -> None:
        # Deploy at 18:30 Madrid = 16:30 UTC; now 19:00 Madrid = 17:00 UTC
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:44:00Z"),
            deploy_at=parse_instant("2026-08-03T16:30:00Z"),
            now=parse_instant("2026-08-03T17:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
        )
        self.assertEqual(d.action, "reuse")
        self.assertEqual(d.reason, "preview_covers_head")

    def test_smoke_failed_forces_redeploy(self) -> None:
        d = decide(
            last_commit_at=parse_instant("2026-08-03T09:44:00Z"),
            deploy_at=parse_instant("2026-08-03T10:00:00Z"),
            now=parse_instant("2026-08-03T12:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
            smoke_failed=True,
        )
        self.assertEqual(d.action, "redeploy")
        self.assertEqual(d.reason, "smoke_failed")

    def test_force_reuse_skips_timestamps(self) -> None:
        d = decide(
            last_commit_at=parse_instant("2026-08-03T12:00:00Z"),
            deploy_at=parse_instant("2026-08-03T07:00:00Z"),
            now=parse_instant("2026-08-03T12:30:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
            force_reuse=True,
        )
        self.assertEqual(d.action, "reuse")
        self.assertEqual(d.reason, "force_reuse")

    def test_force_reuse_still_respects_smoke_failed(self) -> None:
        d = decide(
            last_commit_at=None,
            deploy_at=None,
            now=parse_instant("2026-08-03T12:00:00Z"),
            tz_name=self.TZ,
            shutdown_hour=18,
            force_reuse=True,
            smoke_failed=True,
        )
        self.assertEqual(d.action, "redeploy")
        self.assertEqual(d.reason, "smoke_failed")

    def test_shutdown_instant_madrid_summer(self) -> None:
        now = parse_instant("2026-08-03T12:00:00Z")
        shutdown = shutdown_instant(now, self.TZ, 18)
        local = shutdown.astimezone(ZoneInfo(self.TZ))
        self.assertEqual(local.hour, 18)
        self.assertEqual(local.minute, 0)
        self.assertEqual(local.date().isoformat(), "2026-08-03")


if __name__ == "__main__":
    unittest.main()
