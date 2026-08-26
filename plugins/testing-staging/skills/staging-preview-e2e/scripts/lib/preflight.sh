#!/usr/bin/env bash

# Validate env/fixtures actually referenced by the target .http files, then
# smoke the preview API using auth from AGENTS.md manifest.
e2e_preflight() {
  local -a http_files=("$@")
  local -a required_vars=()
  local -a curl_headers=()
  local -a curl_extra=()
  local missing=()
  local name line smoke_url ping_code
  local manifest="${E2E_AUTH_MANIFEST:-${STATE_DIR}/auth.manifest.json}"

  if ((${#http_files[@]} > 0)); then
    while IFS= read -r line; do
      [[ -n "$line" ]] && required_vars+=("$line")
    done < <(
      python3 "${SCRIPT_DIR}/lib/required_variables.py" \
        --manifest "$manifest" \
        "${http_files[@]}"
    )
  fi

  for name in "${required_vars[@]}"; do
    if [[ -z "${!name:-}" ]]; then
      missing+=("$name")
    fi
  done

  if ((${#missing[@]} > 0)); then
    echo "DATA_STALE: null/empty required variables: ${missing[*]}" >&2
    echo "Fill ${E2E_VARS_FILE} / complete Auth procedure in AGENTS.md." >&2
    return 2
  fi

  # Session vars required by bearer flows must be present before L0/live.
  local session_miss
  session_miss="$(python3 - "$manifest" <<'PY'
import json, os, sys
from pathlib import Path
m = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
missing = [n for n in (m.get("session_variables") or []) if not os.environ.get(n)]
print(",".join(missing))
PY
)"
  if [[ -n "$session_miss" ]]; then
    echo "DATA_STALE: session variables empty: ${session_miss}" >&2
    echo "Follow ## Auth procedure in AGENTS.md, then re-run." >&2
    return 2
  fi

  case "${smokePath}" in
    http://*|https://*)
      smoke_url="${smokePath}"
      ;;
    /*)
      smoke_url="${baseUrl}${smokePath}"
      ;;
    *)
      smoke_url="${baseUrl}/${smokePath}"
      ;;
  esac

  if ! python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" check-url "$baseUrl" "$smoke_url"; then
    echo "DATA_STALE: smoke URL rejected (must be same origin as baseUrl)" >&2
    return 2
  fi

  local curl_args_file
  curl_args_file="$(mktemp)"
  if ! python3 "${SCRIPT_DIR}/lib/build_curl_auth.py" "$manifest" >"$curl_args_file"; then
    rm -f "$curl_args_file"
    echo "DATA_STALE: failed to build smoke auth from AGENTS.md manifest" >&2
    return 2
  fi

  local kind hname hval
  while IFS=$'\t' read -r kind hname hval; do
    case "$kind" in
      H)
        curl_headers+=(-H "${hname}: ${hval}")
        ;;
      U)
        curl_extra+=(-u "$hname")
        ;;
    esac
  done <"$curl_args_file"
  rm -f "$curl_args_file"

  ping_code=$(curl -sS -o /dev/null -w '%{http_code}' \
    "${curl_extra[@]+${curl_extra[@]}}" \
    "${curl_headers[@]+${curl_headers[@]}}" \
    "$smoke_url" || echo "000")

  if [[ "$ping_code" != "200" ]]; then
    echo "DATA_STALE: GET ${smokePath} returned HTTP ${ping_code} (network / URL / auth?)" >&2
    return 2
  fi
}
