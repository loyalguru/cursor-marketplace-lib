#!/usr/bin/env python3
"""Security-focused unit tests for e2e helper libs."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import flatten_variables as fv
import substitute_and_assert as sa


class FlattenSecurityTests(unittest.TestCase):
    def test_rejects_unsafe_key_segment(self) -> None:
        with self.assertRaises(ValueError):
            fv.flatten({"x;rm": 1})

    def test_rejects_path_injection_key(self) -> None:
        with self.assertRaises(ValueError):
            fv.flatten({"a": {"b`id`": 1}})

    def test_flattens_safe_keys(self) -> None:
        self.assertEqual(fv.flatten({"account": {"id": 12}}), {"accountId": "12"})

    def test_null_mode_writes_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preview.json"
            path.write_text(json.dumps({"resource": {"code": "ABC"}}), encoding="utf-8")
            out = Path(tmp) / "out.bin"
            import subprocess
            import sys

            proc = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("flatten_variables.py")), str(path), "--null"],
                check=True,
                capture_output=True,
            )
            self.assertEqual(proc.stdout, b"resourceCode\0ABC\0")
            out.write_bytes(proc.stdout)


class SubstituteSecurityTests(unittest.TestCase):
    def test_subst_env_ignores_path(self) -> None:
        env = {
            "PATH": "/evil",
            "baseUrl": "https://preview.example/app",
            "apiKey": "k",
            "E2E_SUBST_ALLOW": "accountId",
            "accountId": "9",
            "SSH_AUTH_SOCK": "/tmp/sock",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            got = sa.subst_env()
        self.assertEqual(got["baseUrl"], "https://preview.example/app")
        self.assertEqual(got["accountId"], "9")
        self.assertNotIn("PATH", got)
        self.assertNotIn("SSH_AUTH_SOCK", got)

    def test_same_origin_rejects_other_host(self) -> None:
        with self.assertRaises(ValueError):
            sa.same_origin(
                "https://preview.example/app",
                "https://169.254.169.254/latest/meta-data",
            )

    def test_same_origin_allows_base_path(self) -> None:
        sa.same_origin(
            "https://preview.example/app",
            "https://preview.example/app/orders/1",
        )

    def test_same_origin_rejects_credentials_in_url(self) -> None:
        with self.assertRaises(ValueError):
            sa.same_origin(
                "https://preview.example",
                "https://user:pass@preview.example/x",
            )

    def test_redact_log_omits_body(self) -> None:
        text = sa.redact_for_log('{"token":"secret-value"}')
        self.assertNotIn("secret-value", text)
        self.assertIn("omitted", text)

    def test_rejects_header_crlf(self) -> None:
        with self.assertRaises(ValueError):
            sa.validate_http_header(
                "Accept", "application/json\r\nX-Injected: evil"
            )

    def test_rejects_at_file_body(self) -> None:
        with self.assertRaises(ValueError):
            sa.reject_curl_file_body("@/etc/passwd")


class BuildCurlAuthSecurityTests(unittest.TestCase):
    def test_emit_rejects_injected_default_header(self) -> None:
        import build_curl_auth as bca

        with self.assertRaises(SystemExit):
            bca.emit_auth(
                {
                    "default_headers": [
                        {
                            "name": "Accept",
                            "value": "ok\r\nX-Injected: evil",
                        }
                    ],
                    "smoke": {},
                },
                include_smoke=False,
            )


if __name__ == "__main__":
    unittest.main()
