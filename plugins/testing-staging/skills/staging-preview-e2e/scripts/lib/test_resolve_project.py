#!/usr/bin/env python3
"""Unit tests for resolve_project."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resolve_project import repo_slug_from_origin  # noqa: E402


class ResolveProjectTest(unittest.TestCase):
    def test_ssh_github(self) -> None:
        self.assertEqual(
            repo_slug_from_origin(
                "git@github.com:loyalguru/loyal-guru-api-streaming-v2.git"
            ),
            "loyal-guru-api-streaming-v2",
        )

    def test_https_github(self) -> None:
        self.assertEqual(
            repo_slug_from_origin(
                "https://github.com/loyalguru/loyal-guru-api-streaming-v2.git"
            ),
            "loyal-guru-api-streaming-v2",
        )

    def test_https_without_git_suffix(self) -> None:
        self.assertEqual(
            repo_slug_from_origin(
                "https://github.com/loyalguru/loyal-guru-api-streaming-v2"
            ),
            "loyal-guru-api-streaming-v2",
        )

    def test_ssh_scheme(self) -> None:
        self.assertEqual(
            repo_slug_from_origin(
                "ssh://git@github.com/loyalguru/loyal-guru-api-streaming-v2.git"
            ),
            "loyal-guru-api-streaming-v2",
        )

    def test_empty_rejected(self) -> None:
        with self.assertRaises(ValueError):
            repo_slug_from_origin("")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
