#!/usr/bin/env python3
"""Parse allowlisted simple .http files into JSON cases for run.sh."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

FORBIDDEN = [
    (re.compile(r"@name\b"), "@name"),
    (re.compile(r"\?\?"), "?? asserts"),
    (re.compile(r"\{\{\$"), "{{$…}} dynamic vars"),
    (re.compile(r"(?i)content-type:\s*multipart"), "multipart"),
    (re.compile(r"(?i)<\s*%"), "script blocks"),
    (re.compile(r"(?i)^\s*###\s*script", re.M), "script sections"),
]
METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s+(\S+)\s*$")
HEADER_RE = re.compile(r"^((?:\{\{[A-Za-z0-9_]+\}\}|[A-Za-z0-9\-]+)):\s*(.*)$")
EXPECT_STATUS_RE = re.compile(r"^#\s*@expect\s+status\s+(\d+)\s*$")
EXPECT_JSONPATH_EQ_RE = re.compile(
    r"^#\s*@expect\s+jsonpath\s+(\S+)\s+==\s+(.+?)\s*$"
)
EXPECT_JSONPATH_LEN_RE = re.compile(
    r"^#\s*@expect\s+jsonpath\s+(\S+)\s+length\s+(\d+)\s*$"
)
CASE_RE = re.compile(r"^###\s+(\S+)\s*$")


@dataclass
class Expect:
    kind: str
    path: str | None = None
    value: str | None = None
    length: int | None = None
    status: int | None = None


@dataclass
class Case:
    name: str
    method: str = ""
    url: str = ""
    headers: list[list[str]] = field(default_factory=list)
    body: str = ""
    expects: list[Expect] = field(default_factory=list)


def reject_forbidden(text: str, path: Path) -> None:
    for pattern, label in FORBIDDEN:
        if pattern.search(text):
            raise ValueError(f"{path}: forbidden construct: {label}")


def parse_file(path: Path) -> list[Case]:
    text = path.read_text(encoding="utf-8")
    reject_forbidden(text, path)
    cases: list[Case] = []
    current: Case | None = None
    phase = "meta"

    def finish() -> None:
        nonlocal current, phase
        if current is None:
            return
        if not current.method or not current.url:
            raise ValueError(f"{path}: case {current.name!r} missing METHOD URL")
        if not any(expect.kind == "status" for expect in current.expects):
            raise ValueError(f"{path}: case {current.name!r} missing # @expect status")
        cases.append(current)
        current = None
        phase = "meta"

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        case_match = CASE_RE.match(stripped)
        if case_match:
            finish()
            current = Case(name=case_match.group(1))
            continue

        if current is None:
            if not stripped or stripped.startswith(("#", "//")):
                continue
            raise ValueError(f"{path}:{line_number}: content outside a ### case")

        if stripped.startswith("//"):
            continue

        if stripped.startswith("#"):
            if phase == "body":
                if (
                    EXPECT_STATUS_RE.match(stripped)
                    or EXPECT_JSONPATH_EQ_RE.match(stripped)
                    or EXPECT_JSONPATH_LEN_RE.match(stripped)
                ):
                    raise ValueError(f"{path}:{line_number}: @expect after request body")
                current.body += ("\n" if current.body else "") + line
                continue

            status_match = EXPECT_STATUS_RE.match(stripped)
            if status_match:
                current.expects.append(
                    Expect(kind="status", status=int(status_match.group(1)))
                )
                continue
            length_match = EXPECT_JSONPATH_LEN_RE.match(stripped)
            if length_match:
                current.expects.append(
                    Expect(
                        kind="length",
                        path=length_match.group(1),
                        length=int(length_match.group(2)),
                    )
                )
                continue
            equality_match = EXPECT_JSONPATH_EQ_RE.match(stripped)
            if equality_match:
                current.expects.append(
                    Expect(
                        kind="eq",
                        path=equality_match.group(1),
                        value=equality_match.group(2).strip(),
                    )
                )
            continue

        if phase == "meta":
            request_match = METHOD_RE.match(stripped)
            if not request_match:
                raise ValueError(
                    f"{path}:{line_number}: expected METHOD URL, got {stripped!r}"
                )
            current.method = request_match.group(1)
            current.url = request_match.group(2)
            phase = "headers"
            continue

        if phase == "headers":
            if not stripped:
                phase = "body"
                continue
            header_match = HEADER_RE.match(line if not line.startswith(" ") else stripped)
            if not header_match:
                if stripped.startswith(("{", "[")):
                    phase = "body"
                    current.body = line
                    continue
                raise ValueError(f"{path}:{line_number}: invalid header {stripped!r}")
            current.headers.append([header_match.group(1), header_match.group(2)])
            continue

        if phase == "body":
            if not stripped and not current.body:
                continue
            current.body += ("\n" if current.body else "") + line

    finish()
    if not cases:
        raise ValueError(f"{path}: no ### cases found")
    return cases


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: parse_http.py <file.http>...", file=sys.stderr)
        return 2
    all_cases: list[dict] = []
    for argument in sys.argv[1:]:
        path = Path(argument)
        for case in parse_file(path):
            data = asdict(case)
            data["file"] = str(path)
            all_cases.append(data)
    json.dump(all_cases, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
