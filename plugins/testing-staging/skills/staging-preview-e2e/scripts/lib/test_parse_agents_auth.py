#!/usr/bin/env python3
"""Unit tests for parse_agents_auth."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_agents_auth import (  # noqa: E402
    AuthParseError,
    parse_agents_file,
    parse_simple_yaml,
    validate_manifest,
)


STREAMING_DOC = """# E2E

## Authentication

```yaml
auth_mode: machine_headers
inject_auth_on_requests: true
credentials:
  - key: API_KEY
    required: true
    maps_to: apiKey
    notes: Company key
  - key: SECRET_KEY
    required: true
    maps_to: apiSecret
    notes: Company secret
  - key: AUTH_HEADER_KEY
    required: false
    maps_to: authHeaderKey
    default: X-Api-Key
    notes: Header name
  - key: AUTH_HEADER_SECRET
    required: false
    maps_to: authHeaderSecret
    default: X-Api-Secret
    notes: Header name for secret
smoke:
  headers:
    - name_from: authHeaderKey
      value_from: apiKey
    - name_from: authHeaderSecret
      value_from: apiSecret
      when: set
```

## Auth procedure

No login.
"""

MANAGEMENT_DOC = """# E2E

## Authentication

```yaml
auth_mode: user_basic
inject_auth_on_requests: true
credentials:
  - key: OWNER_EMAIL
    required: true
    maps_to: ownerEmail
    notes: Owner email
  - key: OWNER_AUTH_TOKEN
    required: true
    maps_to: ownerAuthToken
    notes: authentication_token
default_headers:
  - name: Accept
    value: application/vnd.loyalguru-v1
smoke:
  basic:
    user_from: ownerEmail
    password_from: ownerAuthToken
```

## Auth procedure

Basic Auth.
"""


class ParseAgentsAuthTest(unittest.TestCase):
    def test_streaming_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(STREAMING_DOC, encoding="utf-8")
            manifest = parse_agents_file(path)
            self.assertEqual(len(manifest["credentials"]), 4)
            self.assertIn("headers", manifest["smoke"])

    def test_management_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(MANAGEMENT_DOC, encoding="utf-8")
            manifest = parse_agents_file(path)
            self.assertEqual(
                manifest["smoke"]["basic"]["user_from"], "ownerEmail"
            )
            self.assertEqual(
                manifest["default_headers"][0]["value"],
                "application/vnd.loyalguru-v1",
            )

    def test_missing_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("# hi\n", encoding="utf-8")
            with self.assertRaises(AuthParseError):
                parse_agents_file(path)

    def test_simple_yaml_list(self) -> None:
        data = parse_simple_yaml(
            "credentials:\n  - key: A\n    required: true\n    maps_to: a\n"
        )
        self.assertEqual(data["credentials"][0]["key"], "A")

    def test_rejects_reserved_credential_key(self) -> None:
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "PATH",
                            "required": False,
                            "maps_to": "apiKey",
                            "default": "/evil",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )

    def test_rejects_reserved_maps_to(self) -> None:
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "API_KEY",
                            "required": True,
                            "maps_to": "LD_PRELOAD",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )

    def test_rejects_header_crlf_injection(self) -> None:
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {"key": "API_KEY", "required": True, "maps_to": "apiKey"}
                    ],
                    "default_headers": [
                        {
                            "name": "Accept",
                            "value": "application/json\r\nX-Injected: evil",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
