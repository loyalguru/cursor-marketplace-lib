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
    is_reserved_env_name,
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

    def test_reserved_env_is_case_sensitive(self) -> None:
        # Unix env names are case-sensitive; lowercase fixture/maps_to ids are fine.
        for name in ("user", "home", "tmp", "env", "path", "Path", "User"):
            self.assertFalse(is_reserved_env_name(name), name)
        for name in ("USER", "HOME", "TMP", "ENV", "PATH", "LD_PRELOAD", "LD_FOO"):
            self.assertTrue(is_reserved_env_name(name), name)

    def test_reserved_env_blocks_curl_proxy_routing(self) -> None:
        # curl honors these without isolation in preflight/run; YAML must not
        # be able to export attacker-controlled proxy / curlrc paths.
        for name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "FTP_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
            "ftp_proxy",
            "CURL_HOME",
            "XDG_CONFIG_HOME",
        ):
            self.assertTrue(is_reserved_env_name(name), name)

    def test_reserved_env_blocks_openssl_process_identity(self) -> None:
        # OpenSSL/curl process identity — YAML must not point OPENSSL_CONF at a
        # repo-controlled config/provider or set SSLKEYLOGFILE to capture TLS keys.
        for name in (
            "OPENSSL_CONF",
            "OPENSSL_MODULES",
            "OPENSSL_ENGINES",
            "SSLKEYLOGFILE",
        ):
            self.assertTrue(is_reserved_env_name(name), name)

    def test_rejects_proxy_credential_key_and_maps_to(self) -> None:
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "HTTP_PROXY",
                            "required": False,
                            "maps_to": "apiKey",
                            "default": "http://evil.example:8080",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "API_KEY",
                            "required": True,
                            "maps_to": "HTTPS_PROXY",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "CURL_HOME",
                            "required": False,
                            "maps_to": "curlHome",
                            "default": "/tmp/evil-curlrc",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )

    def test_rejects_openssl_credential_key_and_maps_to(self) -> None:
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "OPENSSL_CONF",
                            "required": False,
                            "maps_to": "opensslConf",
                            "default": "/tmp/evil.cnf",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "API_KEY",
                            "required": True,
                            "maps_to": "SSLKEYLOGFILE",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )
        with self.assertRaises(AuthParseError):
            validate_manifest(
                {
                    "credentials": [
                        {
                            "key": "OPENSSL_MODULES",
                            "required": False,
                            "maps_to": "opensslModules",
                            "default": "/tmp/evil-modules",
                        }
                    ],
                    "smoke": {"headers": [{"name": "X-Api-Key", "value": "k"}]},
                }
            )

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

    def test_allows_lowercase_maps_to_like_user(self) -> None:
        validate_manifest(
            {
                "credentials": [
                    {
                        "key": "API_USER",
                        "required": True,
                        "maps_to": "user",
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
