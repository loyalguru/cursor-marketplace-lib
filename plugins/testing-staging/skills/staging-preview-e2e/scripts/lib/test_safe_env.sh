#!/usr/bin/env bash
# Reserved env names must match exactly (Unix case-sensitive), not via uppercasing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/safe_env.sh"

fail=0
assert_reserved() {
  local key="$1"
  if ! e2e_is_reserved_env_key "$key"; then
    echo "FAIL: expected reserved: ${key}" >&2
    fail=1
  fi
}

assert_allowed() {
  local key="$1"
  if e2e_is_reserved_env_key "$key"; then
    echo "FAIL: expected allowed: ${key}" >&2
    fail=1
  fi
}

assert_reserved PATH
assert_reserved USER
assert_reserved HOME
assert_reserved TMP
assert_reserved ENV
assert_reserved LD_PRELOAD
assert_reserved LD_LIBRARY_PATH
assert_reserved DYLD_INSERT_LIBRARIES

assert_allowed user
assert_allowed home
assert_allowed tmp
assert_allowed env
assert_allowed path
assert_allowed Path
assert_allowed User
assert_allowed ld_preload
assert_allowed baseUrl
assert_allowed apiKey

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

echo "ok: safe_env case-sensitive reserved check"
