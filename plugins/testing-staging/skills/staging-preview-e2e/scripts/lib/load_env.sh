#!/usr/bin/env bash
# Load credentials from state .env according to auth.manifest.json (from AGENTS.md).

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/safe_env.sh"

e2e_load_env() {
  if [[ ! -f "$E2E_ENV_FILE" ]]; then
    echo "DATA_STALE: missing ${E2E_ENV_FILE}" >&2
    echo "Run first-run setup (see references/first-run-setup.md)." >&2
    return 2
  fi

  local manifest="${E2E_AUTH_MANIFEST:-${STATE_DIR}/auth.manifest.json}"
  if [[ ! -f "$manifest" ]]; then
    echo "DATA_STALE: missing ${manifest}" >&2
    echo "Run bootstrap / first-run setup so AGENTS.md auth is parsed." >&2
    return 2
  fi

  export E2E_AUTH_MANIFEST="$manifest"

  local tmp
  tmp="$(mktemp)"
  if ! python3 - "$manifest" "$E2E_ENV_FILE" <<'PY' >"$tmp"
import json, sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
env_path = Path(sys.argv[2])
env: dict[str, str] = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k] = v

missing = []
for cred in manifest.get("credentials", []):
    key = cred["key"]
    maps_to = cred["maps_to"]
    required = bool(cred.get("required"))
    default = cred.get("default")
    value = env.get(key, "")
    if value == "" and default is not None:
        value = str(default)
    if required and value == "":
        missing.append(key)
    sys.stdout.buffer.write(key.encode("utf-8") + b"\0")
    sys.stdout.buffer.write(value.encode("utf-8") + b"\0")
    sys.stdout.buffer.write(maps_to.encode("utf-8") + b"\0")
    sys.stdout.buffer.write(value.encode("utf-8") + b"\0")

if missing:
    print("MISSING:" + ",".join(missing), file=sys.stderr)
    sys.exit(2)
PY
  then
    rm -f "$tmp"
    echo "DATA_STALE: required credentials missing or empty in ${E2E_ENV_FILE}" >&2
    echo "Complete first-run setup using e2e_tests/AGENTS.md Authentication." >&2
    return 2
  fi

  local key value
  local -a loaded=()
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      rm -f "$tmp"
      echo "DATA_STALE: unsafe env key ${key}" >&2
      return 2
    fi
    if e2e_is_reserved_env_key "$key"; then
      rm -f "$tmp"
      echo "DATA_STALE: reserved env key ${key}" >&2
      return 2
    fi
    export "${key}=${value}"
    loaded+=("$key")
  done <"$tmp"
  rm -f "$tmp"

  local joined=""
  local k
  for k in "${loaded[@]+"${loaded[@]}"}"; do
    if [[ -n "$joined" ]]; then
      joined+=","
    fi
    joined+="$k"
  done
  export E2E_AUTH_SUBST_ALLOW="${joined}"
}
