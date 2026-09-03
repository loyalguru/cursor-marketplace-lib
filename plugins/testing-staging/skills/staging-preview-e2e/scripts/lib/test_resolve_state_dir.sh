#!/usr/bin/env bash
# Regression: migration failures must surface when called as `if ! e2e_resolve_state_dir`
# (bash disables set -e for the whole function body in that context).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/resolve_state_dir.sh"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

e2e_repo_slug_from_git() {
  printf 'test-repo\n'
}

# --- failure path: parent of STATE_DIR is a file → mkdir/mv fail ---
SKILL_ROOT="$tmpdir/skill-fail"
STABLE_ROOT="$tmpdir/stable-as-file"
legacy_dir="${SKILL_ROOT}/state/test-repo"
mkdir -p "$legacy_dir"
echo 'SECRET=1' >"${legacy_dir}/.env"
touch "$STABLE_ROOT"

e2e_default_state_root() {
  printf '%s\n' "$STABLE_ROOT"
}

failed=0
if ! e2e_resolve_state_dir; then
  failed=1
fi

if [[ "$failed" -ne 1 ]]; then
  echo "FAIL: e2e_resolve_state_dir returned success despite failed migration" >&2
  exit 1
fi

if [[ ! -d "$legacy_dir" ]]; then
  echo "FAIL: legacy state was removed despite failed migration" >&2
  exit 1
fi

if [[ -e "${STABLE_ROOT}/test-repo" ]]; then
  echo "FAIL: empty STATE_DIR must not be created after failed migration" >&2
  exit 1
fi

echo "OK: migration failure propagates under if ! e2e_resolve_state_dir"

# --- success path: legacy moves to XDG STATE_DIR ---
unset STATE_DIR STATE_ROOT E2E_ENV_FILE E2E_VARS_FILE E2E_PROJECT_SLUG E2E_STATE_DIR
SKILL_ROOT="$tmpdir/skill-ok"
STABLE_ROOT="$tmpdir/stable-ok"
legacy_dir="${SKILL_ROOT}/state/test-repo"
mkdir -p "$legacy_dir"
echo 'SECRET=1' >"${legacy_dir}/.env"

e2e_default_state_root() {
  printf '%s\n' "$STABLE_ROOT"
}

if ! e2e_resolve_state_dir; then
  echo "FAIL: successful migration should return 0" >&2
  exit 1
fi

if [[ -d "$legacy_dir" ]]; then
  echo "FAIL: legacy dir should be gone after successful migration" >&2
  exit 1
fi

if [[ ! -f "${STABLE_ROOT}/test-repo/.env" ]]; then
  echo "FAIL: credentials not present at migrated STATE_DIR" >&2
  exit 1
fi

echo "OK: successful migration moves legacy state to STATE_DIR"
