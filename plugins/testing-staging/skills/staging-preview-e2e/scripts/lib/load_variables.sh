#!/usr/bin/env bash

e2e_load_variables() {
  if [[ ! -f "$E2E_VARS_FILE" ]]; then
    echo "DATA_STALE: missing ${E2E_VARS_FILE}" >&2
    echo "Run ${SKILL_ROOT}/scripts/bootstrap.sh and fill the generated state." >&2
    return 2
  fi

  # NUL-delimited KEY/VALUE pairs — never eval JSON-derived text as shell.
  local tmp key value
  local -a loaded_keys=()
  tmp="$(mktemp)"

  if ! python3 "${SCRIPT_DIR}/lib/flatten_variables.py" "$E2E_VARS_FILE" --null >"$tmp"; then
    rm -f "$tmp"
    echo "DATA_STALE: failed to parse ${E2E_VARS_FILE}" >&2
    return 2
  fi

  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      rm -f "$tmp"
      echo "DATA_STALE: unsafe variable name from ${E2E_VARS_FILE}: ${key}" >&2
      return 2
    fi
    export "${key}=${value}"
    loaded_keys+=("$key")
  done <"$tmp"
  rm -f "$tmp"

  if [[ -z "${baseUrl:-}" ]]; then
    echo "DATA_STALE: ${E2E_VARS_FILE} must define non-empty baseUrl" >&2
    return 2
  fi

  export URL="$baseUrl"
  export GCP_PROJECT="${gcpProject:-}"
  export GCP_REGION="${gcpRegion:-}"
  export GCP_SERVICE="${gcpService:-}"

  local joined=""
  local k
  for k in "${loaded_keys[@]+"${loaded_keys[@]}"}"; do
    if [[ -n "$joined" ]]; then
      joined+=","
    fi
    joined+="$k"
  done
  # Merge fixture keys with auth maps_to from load_env.
  if [[ -n "${E2E_AUTH_SUBST_ALLOW:-}" ]]; then
    if [[ -n "$joined" ]]; then
      joined+=",${E2E_AUTH_SUBST_ALLOW}"
    else
      joined="${E2E_AUTH_SUBST_ALLOW}"
    fi
  fi
  export E2E_SUBST_ALLOW="${joined}"
}
