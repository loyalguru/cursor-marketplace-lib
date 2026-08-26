#!/usr/bin/env bash
# Verify first-run / auth setup gates. Never print secret values.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/resolve_state_dir.sh"

usage() {
  cat <<EOF
Usage: $0 --step agents|bootstrap|credential|base_url|session|all [--key NAME] [--agents PATH]

Exit 0 = step OK. Exit 1 = SETUP_INCOMPLETE (do not advance wizard).
EOF
}

STEP=""
CRED_KEY=""
AGENTS_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --step)
      STEP="${2:-}"
      shift 2
      ;;
    --key)
      CRED_KEY="${2:-}"
      shift 2
      ;;
    --agents)
      AGENTS_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$STEP" ]]; then
  usage
  exit 2
fi

if ! e2e_resolve_state_dir; then
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$AGENTS_PATH" ]]; then
  if [[ -n "$repo_root" ]]; then
    AGENTS_PATH="${repo_root}/e2e_tests/AGENTS.md"
  fi
fi

MANIFEST="${STATE_DIR}/auth.manifest.json"
ENV_FILE="${E2E_ENV_FILE}"
VARS_FILE="${E2E_VARS_FILE}"

fail() {
  echo "SETUP_INCOMPLETE: $*" >&2
  exit 1
}

ok() {
  echo "SETUP_OK: $*"
  exit 0
}

step_agents() {
  if [[ -z "$AGENTS_PATH" || ! -f "$AGENTS_PATH" ]]; then
    fail "missing e2e_tests/AGENTS.md (expected ${AGENTS_PATH:-unknown}). Copy assets/agents-authentication.example.md or AGENTS.*.example.md into the app repo."
  fi
  if ! e2e_python "${SCRIPT_DIR}/lib/parse_agents_auth.py" "$AGENTS_PATH" >/dev/null; then
    fail "AGENTS.md ## Authentication YAML invalid — fix it before continuing"
  fi
  ok "AGENTS.md Authentication parseable at ${AGENTS_PATH}"
}

step_bootstrap() {
  [[ -f "$ENV_FILE" ]] || fail "missing ${ENV_FILE} — run bootstrap.sh"
  [[ -f "$VARS_FILE" ]] || fail "missing ${VARS_FILE} — run bootstrap.sh"
  [[ -f "$MANIFEST" ]] || fail "missing ${MANIFEST} — run bootstrap.sh with valid AGENTS.md"
  ok "bootstrap files present under ${STATE_DIR}"
}

env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -n1 | cut -d= -f2- || true
}

step_credential() {
  [[ -n "$CRED_KEY" ]] || fail "--key required for credential step"
  [[ -f "$MANIFEST" ]] || fail "missing manifest ${MANIFEST}"
  [[ -f "$ENV_FILE" ]] || fail "missing ${ENV_FILE}"

  e2e_python - "$MANIFEST" "$ENV_FILE" "$CRED_KEY" <<'PY' || exit 1
import json, sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
env_path = Path(sys.argv[2])
want = sys.argv[3]
env = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v

cred = None
for item in manifest.get("credentials", []):
    if item.get("key") == want:
        cred = item
        break
if cred is None:
    print(f"SETUP_INCOMPLETE: key {want!r} not declared in AGENTS.md credentials", file=sys.stderr)
    sys.exit(1)

value = env.get(want, "")
if value == "" and cred.get("default") is not None:
    value = str(cred["default"])
required = bool(cred.get("required"))
if required and value == "":
    print(f"SETUP_INCOMPLETE: required credential {want} is empty", file=sys.stderr)
    sys.exit(1)
if not required and value == "" and cred.get("default") is None:
    # optional without default: OK if user confirmed skip (empty allowed)
    print(f"SETUP_OK: optional credential {want} empty (skipped)")
    sys.exit(0)
print(f"SETUP_OK: credential {want} present (len={len(value)})")
PY
}

step_base_url() {
  [[ -f "$VARS_FILE" ]] || fail "missing ${VARS_FILE}"
  e2e_python - "$VARS_FILE" <<'PY' || exit 1
import json, sys
from pathlib import Path
from urllib.parse import urlparse

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
base = data.get("baseUrl") if isinstance(data, dict) else None
if not isinstance(base, str) or not base.strip():
    print("SETUP_INCOMPLETE: preview.json baseUrl is empty", file=sys.stderr)
    sys.exit(1)
parsed = urlparse(base.strip())
if parsed.scheme not in ("http", "https") or not parsed.netloc:
    print("SETUP_INCOMPLETE: baseUrl must be http(s) URL with host", file=sys.stderr)
    sys.exit(1)
print(f"SETUP_OK: baseUrl host={parsed.netloc}")
PY
}

step_session() {
  [[ -f "$MANIFEST" ]] || fail "missing ${MANIFEST}"
  [[ -f "$VARS_FILE" ]] || fail "missing ${VARS_FILE}"
  e2e_python - "$MANIFEST" "$VARS_FILE" "${SCRIPT_DIR}/lib/flatten_variables.py" <<'PY' || exit 1
import importlib.util, json, sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
needed = manifest.get("session_variables") or []
if not needed:
    print("SETUP_OK: no session_variables required")
    sys.exit(0)

spec = importlib.util.spec_from_file_location("flatten_variables", sys.argv[3])
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
flat = mod.flatten(data)
missing = [n for n in needed if not flat.get(n)]
if missing:
    print(
        "SETUP_INCOMPLETE: session variables missing/empty in preview.json: "
        + ", ".join(missing)
        + " — follow ## Auth procedure in AGENTS.md",
        file=sys.stderr,
    )
    sys.exit(1)
print("SETUP_OK: session_variables present: " + ",".join(needed))
PY
}

case "$STEP" in
  agents) step_agents ;;
  bootstrap) step_bootstrap ;;
  credential) step_credential ;;
  base_url) step_base_url ;;
  session) step_session ;;
  all)
    if [[ -z "$AGENTS_PATH" || ! -f "$AGENTS_PATH" ]]; then
      fail "missing e2e_tests/AGENTS.md"
    fi
    e2e_python "${SCRIPT_DIR}/lib/parse_agents_auth.py" "$AGENTS_PATH" >/dev/null \
      || fail "AGENTS.md Authentication invalid"
    [[ -f "$ENV_FILE" ]] || fail "missing ${ENV_FILE}"
    [[ -f "$VARS_FILE" ]] || fail "missing ${VARS_FILE}"
    [[ -f "$MANIFEST" ]] || fail "missing ${MANIFEST}"
    e2e_python - "$MANIFEST" "$ENV_FILE" <<'PY' || exit 1
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
env = {}
for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v
missing = []
for cred in manifest.get("credentials", []):
    key = cred["key"]
    value = env.get(key, "")
    if value == "" and cred.get("default") is not None:
        value = str(cred["default"])
    if cred.get("required") and value == "":
        missing.append(key)
if missing:
    print("SETUP_INCOMPLETE: required credentials empty: " + ",".join(missing), file=sys.stderr)
    sys.exit(1)
PY
    e2e_python - "$VARS_FILE" <<'PY' || exit 1
import json, sys
from pathlib import Path
from urllib.parse import urlparse
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
base = data.get("baseUrl") if isinstance(data, dict) else None
if not isinstance(base, str) or not base.strip():
    print("SETUP_INCOMPLETE: preview.json baseUrl is empty", file=sys.stderr)
    sys.exit(1)
parsed = urlparse(base.strip())
if parsed.scheme not in ("http", "https") or not parsed.netloc:
    print("SETUP_INCOMPLETE: baseUrl must be http(s) URL with host", file=sys.stderr)
    sys.exit(1)
PY
    e2e_python - "$MANIFEST" "$VARS_FILE" "${SCRIPT_DIR}/lib/flatten_variables.py" <<'PY' || exit 1
import importlib.util, json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
needed = manifest.get("session_variables") or []
if needed:
    spec = importlib.util.spec_from_file_location("flatten_variables", sys.argv[3])
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    flat = mod.flatten(data)
    missing = [n for n in needed if not flat.get(n)]
    if missing:
        print("SETUP_INCOMPLETE: session variables missing: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)
PY
    ok "all setup gates passed for ${STATE_DIR}"
    ;;
  *)
    echo "Unknown step: $STEP" >&2
    usage
    exit 2
    ;;
esac
