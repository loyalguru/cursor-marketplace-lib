#!/usr/bin/env python3
"""Parse ## Authentication YAML (stdlib subset) from e2e_tests/AGENTS.md."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HEADING_RE = re.compile(r"^##\s+Authentication\s*$", re.IGNORECASE | re.MULTILINE)
FENCE_RE = re.compile(
    r"```(?:yaml|yml)?\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# RFC 7230 token — no separators, CR, LF, or whitespace.
HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.0-9A-Z^_`a-z|~]+$")

# Names that must never be exported into the runner process from AGENTS.md /
# preview.json (hijack PATH/LD_PRELOAD/etc.).
RESERVED_ENV_NAMES = frozenset(
    {
        "PATH",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "LD_AUDIT",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "DYLD_FRAMEWORK_PATH",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "BASH_ENV",
        "ENV",
        "IFS",
        "CDPATH",
        "SHELLOPTS",
        "BASHOPTS",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "CURL_CA_BUNDLE",
        "REQUESTS_CA_BUNDLE",
        # OpenSSL / curl process identity (config, providers, TLS key log).
        "OPENSSL_CONF",
        "OPENSSL_MODULES",
        "OPENSSL_ENGINES",
        "SSLKEYLOGFILE",
        # curl proxy / config routing (case variants: curl reads both).
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
        "NODE_OPTIONS",
        "NODE_PATH",
        "PERL5LIB",
        "PERL5OPT",
        "RUBYLIB",
        "RUBYOPT",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_OBJECT_DIRECTORY",
        "GH_TOKEN",
        "GH_HOST",
        "GITHUB_TOKEN",
        "PROMPT_COMMAND",
        "PS4",
        "TERMCAP",
        "TERMINFO",
        # Runner-internal paths / knobs — overwriting SCRIPT_DIR makes later
        # python3 "${SCRIPT_DIR}/lib/..." execute attacker-controlled helpers.
        "SCRIPT_DIR",
        "SKILL_ROOT",
        "STATE_DIR",
        "STATE_ROOT",
        "_E2E_LIB_DIR",
        # glibc iconv module search path (remaining loader knob).
        "GCONV_PATH",
    }
)
# E2E_ covers E2E_AUTH_MANIFEST, E2E_ENV_FILE, E2E_SUBST_ALLOW, etc.
RESERVED_ENV_PREFIXES = ("DYLD_", "BASH_FUNC_", "LD_", "E2E_")


class AuthParseError(ValueError):
    pass


def is_reserved_env_name(name: str) -> bool:
    # Exact match only: Unix env names are case-sensitive, so fixture / maps_to
    # ids like user, home, tmp, env, path must not be treated as USER/HOME/etc.
    if name in RESERVED_ENV_NAMES:
        return True
    return name.startswith(RESERVED_ENV_PREFIXES)


def assert_safe_header_name(name: str, where: str) -> str:
    if (
        not name
        or "\r" in name
        or "\n" in name
        or "\0" in name
        or not HEADER_NAME_RE.fullmatch(name)
    ):
        raise AuthParseError(f"{where}: unsafe header name")
    return name


def assert_safe_header_value(value: str, where: str) -> str:
    if "\r" in value or "\n" in value or "\0" in value:
        raise AuthParseError(f"{where}: unsafe header value")
    return value


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
        elif ch == "#" and not in_single and not in_double:
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return ""
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null" or low == "~":
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_simple_yaml(text: str) -> Any:
    """Minimal YAML subset: maps, lists of maps, scalars. No anchors."""
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        cleaned = _strip_comment(raw)
        if not cleaned.strip():
            continue
        if cleaned.lstrip().startswith("-") and cleaned.lstrip() != cleaned:
            # keep
            pass
        lines.append((_indent(cleaned), cleaned.strip()))

    def parse_block(index: int, min_indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return None, index
        ind, content = lines[index]
        if ind < min_indent:
            return None, index

        # list
        if content.startswith("- "):
            items: list[Any] = []
            while index < len(lines):
                ind, content = lines[index]
                if ind < min_indent:
                    break
                if not content.startswith("- "):
                    break
                item_body = content[2:].strip()
                index += 1
                if ":" in item_body and not item_body.startswith("{"):
                    # inline key: value start of a map item
                    key, _, rest = item_body.partition(":")
                    key = key.strip()
                    rest = rest.strip()
                    item: dict[str, Any] = {}
                    if rest:
                        item[key] = _parse_scalar(rest)
                    else:
                        # nested under this key
                        nested, index = parse_block(index, ind + 1)
                        item[key] = nested
                    # more keys of same map item at ind+2 typically (2 spaces under "- ")
                    child_min = ind + 1
                    while index < len(lines):
                        cind, ccontent = lines[index]
                        if cind < child_min:
                            break
                        if ccontent.startswith("- "):
                            break
                        if ":" not in ccontent:
                            raise AuthParseError(f"invalid list item line: {ccontent}")
                        ck, _, cv = ccontent.partition(":")
                        ck = ck.strip()
                        cv = cv.strip()
                        index += 1
                        if cv:
                            item[ck] = _parse_scalar(cv)
                        else:
                            nested, index = parse_block(index, cind + 1)
                            item[ck] = nested
                    items.append(item)
                elif item_body:
                    items.append(_parse_scalar(item_body))
                else:
                    nested, index = parse_block(index, ind + 1)
                    items.append(nested)
            return items, index

        # map
        result: dict[str, Any] = {}
        while index < len(lines):
            ind, content = lines[index]
            if ind < min_indent:
                break
            if content.startswith("- "):
                break
            if ":" not in content:
                raise AuthParseError(f"expected key: value, got: {content}")
            key, _, rest = content.partition(":")
            key = key.strip()
            rest = rest.strip()
            index += 1
            if rest:
                result[key] = _parse_scalar(rest)
            else:
                nested, index = parse_block(index, ind + 1)
                result[key] = nested if nested is not None else {}
        return result, index

    data, _ = parse_block(0, 0)
    return data if data is not None else {}


def extract_auth_yaml(agents_text: str) -> str:
    match = HEADING_RE.search(agents_text)
    if not match:
        raise AuthParseError("missing ## Authentication heading")
    rest = agents_text[match.end() :]
    # Stop at next ## heading
    next_h = re.search(r"^##\s+\S", rest, re.MULTILINE)
    section = rest[: next_h.start()] if next_h else rest
    fence = FENCE_RE.search(section)
    if not fence:
        raise AuthParseError(
            "missing fenced yaml/yml (or unlabeled) block under ## Authentication"
        )
    return fence.group(1).strip()


def validate_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AuthParseError("Authentication YAML root must be a mapping")

    credentials = data.get("credentials")
    if not isinstance(credentials, list) or not credentials:
        raise AuthParseError("credentials must be a non-empty list")

    normalized_creds: list[dict[str, Any]] = []
    maps: set[str] = set()
    for i, item in enumerate(credentials):
        if not isinstance(item, dict):
            raise AuthParseError(f"credentials[{i}] must be a mapping")
        key = item.get("key")
        maps_to = item.get("maps_to")
        if not isinstance(key, str) or not SAFE_IDENT.fullmatch(key):
            raise AuthParseError(f"credentials[{i}].key must be a safe identifier")
        if is_reserved_env_name(key):
            raise AuthParseError(f"credentials[{i}].key is a reserved env name: {key}")
        if not isinstance(maps_to, str) or not SAFE_IDENT.fullmatch(maps_to):
            raise AuthParseError(f"credentials[{i}].maps_to must be a safe identifier")
        if is_reserved_env_name(maps_to):
            raise AuthParseError(
                f"credentials[{i}].maps_to is a reserved env name: {maps_to}"
            )
        if maps_to in maps:
            raise AuthParseError(f"duplicate maps_to: {maps_to}")
        maps.add(maps_to)
        required = bool(item.get("required", False))
        entry: dict[str, Any] = {
            "key": key,
            "required": required,
            "maps_to": maps_to,
            "notes": str(item.get("notes") or ""),
        }
        if "default" in item and item["default"] is not None:
            entry["default"] = str(item["default"])
        normalized_creds.append(entry)

    default_headers: list[dict[str, str]] = []
    raw_headers = data.get("default_headers") or []
    if raw_headers is None:
        raw_headers = []
    if not isinstance(raw_headers, list):
        raise AuthParseError("default_headers must be a list")
    for i, item in enumerate(raw_headers):
        if not isinstance(item, dict):
            raise AuthParseError(f"default_headers[{i}] must be a mapping")
        name = item.get("name")
        value = item.get("value")
        if not isinstance(name, str) or not name.strip():
            raise AuthParseError(f"default_headers[{i}].name required")
        if not isinstance(value, str):
            raise AuthParseError(f"default_headers[{i}].value must be a string")
        assert_safe_header_name(name, f"default_headers[{i}].name")
        assert_safe_header_value(value, f"default_headers[{i}].value")
        default_headers.append({"name": name, "value": value})

    smoke = data.get("smoke") or {}
    if not isinstance(smoke, dict):
        raise AuthParseError("smoke must be a mapping")

    smoke_out: dict[str, Any] = {}
    if "basic" in smoke and smoke["basic"] is not None:
        basic = smoke["basic"]
        if not isinstance(basic, dict):
            raise AuthParseError("smoke.basic must be a mapping")
        user_from = basic.get("user_from")
        password_from = basic.get("password_from")
        if not isinstance(user_from, str) or not SAFE_IDENT.fullmatch(user_from):
            raise AuthParseError("smoke.basic.user_from must be a safe maps_to name")
        if is_reserved_env_name(user_from):
            raise AuthParseError(
                f"smoke.basic.user_from is a reserved env name: {user_from}"
            )
        if not isinstance(password_from, str) or not SAFE_IDENT.fullmatch(
            password_from
        ):
            raise AuthParseError(
                "smoke.basic.password_from must be a safe maps_to name"
            )
        if is_reserved_env_name(password_from):
            raise AuthParseError(
                f"smoke.basic.password_from is a reserved env name: {password_from}"
            )
        smoke_out["basic"] = {
            "user_from": user_from,
            "password_from": password_from,
        }

    if "headers" in smoke and smoke["headers"] is not None:
        headers = smoke["headers"]
        if not isinstance(headers, list):
            raise AuthParseError("smoke.headers must be a list")
        out_h: list[dict[str, Any]] = []
        for i, item in enumerate(headers):
            if not isinstance(item, dict):
                raise AuthParseError(f"smoke.headers[{i}] must be a mapping")
            entry_h: dict[str, Any] = {}
            if "name" in item:
                entry_h["name"] = assert_safe_header_name(
                    str(item["name"]), f"smoke.headers[{i}].name"
                )
            if "name_from" in item:
                nf = item["name_from"]
                if not isinstance(nf, str) or not SAFE_IDENT.fullmatch(nf):
                    raise AuthParseError(
                        f"smoke.headers[{i}].name_from must be a safe identifier"
                    )
                if is_reserved_env_name(nf):
                    raise AuthParseError(
                        f"smoke.headers[{i}].name_from is a reserved env name: {nf}"
                    )
                entry_h["name_from"] = nf
            if "value" in item:
                entry_h["value"] = assert_safe_header_value(
                    str(item["value"]), f"smoke.headers[{i}].value"
                )
            if "value_from" in item:
                vf = item["value_from"]
                if not isinstance(vf, str) or not SAFE_IDENT.fullmatch(vf):
                    raise AuthParseError(
                        f"smoke.headers[{i}].value_from must be a safe identifier"
                    )
                if is_reserved_env_name(vf):
                    raise AuthParseError(
                        f"smoke.headers[{i}].value_from is a reserved env name: {vf}"
                    )
                entry_h["value_from"] = vf
            if "value_prefix" in item:
                entry_h["value_prefix"] = assert_safe_header_value(
                    str(item["value_prefix"]), f"smoke.headers[{i}].value_prefix"
                )
            if item.get("when"):
                entry_h["when"] = str(item["when"])
            if "name" not in entry_h and "name_from" not in entry_h:
                raise AuthParseError(
                    f"smoke.headers[{i}] needs name or name_from"
                )
            if "value" not in entry_h and "value_from" not in entry_h:
                raise AuthParseError(
                    f"smoke.headers[{i}] needs value or value_from"
                )
            out_h.append(entry_h)
        smoke_out["headers"] = out_h

    if "basic" not in smoke_out and "headers" not in smoke_out:
        raise AuthParseError("smoke must define headers and/or basic")

    session_variables: list[str] = []
    raw_session = data.get("session_variables") or []
    if raw_session is None:
        raw_session = []
    if not isinstance(raw_session, list):
        raise AuthParseError("session_variables must be a list")
    for i, name in enumerate(raw_session):
        if not isinstance(name, str) or not SAFE_IDENT.fullmatch(name):
            raise AuthParseError(f"session_variables[{i}] must be a safe identifier")
        if is_reserved_env_name(name):
            raise AuthParseError(
                f"session_variables[{i}] is a reserved env name: {name}"
            )
        session_variables.append(name)

    # When true, run.sh adds smoke auth + default_headers to every request
    # (skips header names already present on the case).
    inject = data.get("inject_auth_on_requests")
    if inject is None:
        inject_auth_on_requests = True
    elif isinstance(inject, bool):
        inject_auth_on_requests = inject
    else:
        raise AuthParseError("inject_auth_on_requests must be a boolean")

    auth_mode = data.get("auth_mode")
    if auth_mode is None:
        auth_mode_out = ""
    elif isinstance(auth_mode, str) and auth_mode in (
        "machine_headers",
        "user_basic",
        "user_bearer_session",
    ):
        auth_mode_out = auth_mode
    else:
        raise AuthParseError(
            "auth_mode must be machine_headers|user_basic|user_bearer_session"
        )

    return {
        "credentials": normalized_creds,
        "default_headers": default_headers,
        "smoke": smoke_out,
        "session_variables": session_variables,
        "inject_auth_on_requests": inject_auth_on_requests,
        "auth_mode": auth_mode_out,
    }


def parse_agents_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    yaml_text = extract_auth_yaml(text)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(yaml_text)
    except Exception:
        data = parse_simple_yaml(yaml_text)
    return validate_manifest(data)


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: parse_agents_auth.py <AGENTS.md> [--write-manifest PATH]",
            file=sys.stderr,
        )
        return 2
    agents = Path(sys.argv[1])
    if not agents.is_file():
        print(f"SETUP_INCOMPLETE: missing {agents}", file=sys.stderr)
        return 1
    try:
        manifest = parse_agents_file(agents)
    except AuthParseError as error:
        print(f"SETUP_INCOMPLETE: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"SETUP_INCOMPLETE: {error}", file=sys.stderr)
        return 1

    if len(sys.argv) >= 4 and sys.argv[2] == "--write-manifest":
        out = Path(sys.argv[3])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(str(out))
        return 0

    json.dump(manifest, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
