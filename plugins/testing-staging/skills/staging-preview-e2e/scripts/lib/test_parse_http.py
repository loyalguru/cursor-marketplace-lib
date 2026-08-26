#!/usr/bin/env python3
"""Unit tests for parse_http."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_http import parse_file  # noqa: E402


class ParseHttpTest(unittest.TestCase):
    def _parse(self, content: str) -> list:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".http", encoding="utf-8", delete=False
        ) as handle:
            handle.write(content)
            path = Path(handle.name)
        try:
            return parse_file(path)
        finally:
            path.unlink(missing_ok=True)

    def test_streaming_placeholder_header_names_parse_as_headers(self) -> None:
        cases = self._parse(
            """### streaming_auth_headers
# @expect status 200
POST {{baseUrl}}/example/resource
{{authHeaderKey}}: {{apiKey}}
{{authHeaderSecret}}: {{apiSecret}}
Content-Type: application/json
Accept: application/json

{
  "id": {{resourceId}}
}
"""
        )
        case = cases[0]
        self.assertEqual(
            case.headers,
            [
                ["{{authHeaderKey}}", "{{apiKey}}"],
                ["{{authHeaderSecret}}", "{{apiSecret}}"],
                ["Content-Type", "application/json"],
                ["Accept", "application/json"],
            ],
        )
        self.assertEqual(case.body, '{\n  "id": {{resourceId}}\n}')


if __name__ == "__main__":
    raise SystemExit(unittest.main())
