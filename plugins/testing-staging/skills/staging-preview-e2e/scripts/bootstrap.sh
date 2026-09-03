#!/usr/bin/env bash
# Initialize personal staging-preview-e2e state from skill assets + AGENTS.md auth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/resolve_state_dir.sh"

if ! e2e_resolve_state_dir; then
  exit 1
fi

# STATE_ROOT is set by resolve (stable XDG path). Also clean legacy skill-cache state.
LEGACY_STATE_ROOT="${SKILL_ROOT}/state"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
AGENTS_PATH="${E2E_AGENTS_PATH:-}"
if [[ -z "$AGENTS_PATH" && -n "$repo_root" ]]; then
  AGENTS_PATH="${repo_root}/e2e_tests/AGENTS.md"
fi

if [[ -z "$AGENTS_PATH" || ! -f "$AGENTS_PATH" ]]; then
  echo "ERROR: missing e2e_tests/AGENTS.md for this repo." >&2
  echo "Create it with ## Authentication (YAML). See:" >&2
  echo "  ${SKILL_ROOT}/assets/agents-authentication.example.md" >&2
  echo "  ${SKILL_ROOT}/assets/AGENTS.streaming.example.md" >&2
  echo "  ${SKILL_ROOT}/assets/AGENTS.management.example.md" >&2
  exit 1
fi

umask 077

# One-shot: migrate flat state/ into state/{repo}/ when present (stable + legacy).
e2e_python "${SCRIPT_DIR}/lib/migrate_flat_state.py" "$STATE_ROOT" "$STATE_DIR"
e2e_python "${SCRIPT_DIR}/lib/migrate_flat_state.py" "$LEGACY_STATE_ROOT" "$STATE_DIR"

mkdir -p "${STATE_DIR}/variables"

# Parse AGENTS.md → auth.manifest.json (no secrets).
if ! e2e_python "${SCRIPT_DIR}/lib/parse_agents_auth.py" "$AGENTS_PATH" \
  --write-manifest "${STATE_DIR}/auth.manifest.json"; then
  echo "ERROR: failed to parse ## Authentication in ${AGENTS_PATH}" >&2
  exit 1
fi
echo "Wrote ${STATE_DIR}/auth.manifest.json from ${AGENTS_PATH}"

if [[ ! -f "${STATE_DIR}/.env" ]]; then
  # Seed empty keys declared in AGENTS.md credentials.
  e2e_python - "${STATE_DIR}/auth.manifest.json" "${STATE_DIR}/.env" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lines = [
    "# Keys from e2e_tests/AGENTS.md Authentication. Fill via first-run setup.",
    "# Never commit this file.",
]
for cred in manifest.get("credentials", []):
    key = cred["key"]
    default = cred.get("default")
    if default is not None and not cred.get("required"):
        lines.append(f"{key}={default}")
    else:
        lines.append(f"{key}=")
Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  echo "Created ${STATE_DIR}/.env (empty values — complete first-run setup)"
fi

if [[ ! -f "${STATE_DIR}/variables/preview.json" ]]; then
  cp "${SKILL_ROOT}/assets/preview.json" "${STATE_DIR}/variables/preview.json"
  echo "Created ${STATE_DIR}/variables/preview.json"
fi

chmod 600 "${STATE_DIR}/.env" 2>/dev/null || true
chmod 600 "${STATE_DIR}/variables/preview.json" 2>/dev/null || true
chmod 600 "${STATE_DIR}/auth.manifest.json" 2>/dev/null || true

if [[ -f "${STATE_DIR}/preview.env" ]]; then
  rm -f "${STATE_DIR}/preview.env"
  echo "Removed ${STATE_DIR}/preview.env"
fi
if [[ -f "${STATE_ROOT}/preview.env" ]]; then
  rm -f "${STATE_ROOT}/preview.env"
  echo "Removed ${STATE_ROOT}/preview.env"
fi
if [[ -f "${LEGACY_STATE_ROOT}/preview.env" ]]; then
  rm -f "${LEGACY_STATE_ROOT}/preview.env"
  echo "Removed ${LEGACY_STATE_ROOT}/preview.env"
fi

echo "Project state: ${STATE_DIR}"
echo "Next: follow references/first-run-setup.md (one step at a time; verify each)."
echo "Verify agents: ${SKILL_ROOT}/scripts/verify_state.sh --step agents"
