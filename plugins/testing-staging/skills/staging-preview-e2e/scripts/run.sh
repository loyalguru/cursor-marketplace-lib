#!/usr/bin/env bash
# Run allowlisted .http e2e cases via curl.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/resolve_state_dir.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/skill_defaults.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/load_env.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/load_variables.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/preflight.sh"

SKIP_PREFLIGHT=0
TARGETS=()

# Hard gate: required system tools must be installed.
"${SCRIPT_DIR}/check_tools.sh" || exit 1

if ! e2e_resolve_state_dir; then
  exit 2
fi

usage() {
  cat <<EOF
Usage: ${0} [--skip-preflight] [path-to.http|directory]...

State:
  project:   ${E2E_PROJECT_SLUG:-}
  env:       ${E2E_ENV_FILE}
  variables: ${E2E_VARS_FILE}

Loads skill-owned state, parses allowlisted .http files from the target
repository, substitutes {{vars}}, runs curl, and checks @expect assertions.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --skip-preflight)
      SKIP_PREFLIGHT=1
      shift
      ;;
    *)
      TARGETS+=("$1")
      shift
      ;;
  esac
done

if ((${#TARGETS[@]} == 0)); then
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -z "$repo_root" ]]; then
    echo "ERROR: no target supplied and current directory is not a git repository" >&2
    exit 2
  fi
  TARGETS=("${repo_root}/e2e_tests/http")
fi

collect_http_files() {
  local target absolute
  local -a files=()

  for target in "${TARGETS[@]}"; do
    if [[ "$target" = /* ]]; then
      absolute="$target"
    else
      absolute="$(pwd)/${target}"
    fi

    if [[ -d "$absolute" ]]; then
      # Portable across Bash 3.2 / BSD find+sort (no mapfile, no sort -z).
      while IFS= read -r file; do
        [[ -n "$file" ]] && files+=("$file")
      done < <(find "$absolute" -type f -name '*.http' | LC_ALL=C sort)
    elif [[ -f "$absolute" ]]; then
      files+=("$absolute")
    else
      echo "ERROR: path not found: $target" >&2
      return 1
    fi
  done

  if ((${#files[@]} == 0)); then
    echo "ERROR: no .http files found" >&2
    return 1
  fi
  printf '%s\n' "${files[@]}"
}

e2e_load_skill_defaults
e2e_load_env
e2e_load_variables

HTTP_FILES=()
while IFS= read -r file; do
  [[ -n "$file" ]] && HTTP_FILES+=("$file")
done < <(collect_http_files)

if [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
  if ! e2e_preflight "${HTTP_FILES[@]}"; then
    exit 2
  fi
fi

CASES_JSON="$(python3 "${SCRIPT_DIR}/lib/parse_http.py" "${HTTP_FILES[@]}")"
CASE_COUNT="$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"$CASES_JSON")"

pass=0
fail=0
echo "baseUrl=${baseUrl} smokePath=${smokePath} cases=${CASE_COUNT}"

for ((i = 0; i < CASE_COUNT; i++)); do
  case_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)[int(sys.argv[1])]))' "$i" <<<"$CASES_JSON")"
  name="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])' <<<"$case_json")"
  method="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["method"])' <<<"$case_json")"
  url_tmpl="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' <<<"$case_json")"
  body_tmpl="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("body") or "")' <<<"$case_json")"
  expects_tmpl="$(python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["expects"]))' <<<"$case_json")"
  headers_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["headers"]))' <<<"$case_json")"

  if ! expects_json="$(printf '%s' "$expects_tmpl" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" substitute)"; then
    echo -e "FAIL\t-\t${name}\tunresolved variables in @expect"
    fail=$((fail + 1))
    continue
  fi
  if ! url="$(printf '%s' "$url_tmpl" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" substitute)"; then
    echo -e "FAIL\t-\t${name}\tunresolved variables in URL"
    fail=$((fail + 1))
    continue
  fi
  if ! python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" check-url "$baseUrl" "$url"; then
    echo -e "FAIL\t-\t${name}\tURL rejected (must be same origin as baseUrl)"
    fail=$((fail + 1))
    continue
  fi

  declare -a curl_headers=()
  declare -a curl_extra=()
  declare -a case_header_names=()
  header_count="$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"$headers_json")"
  header_err=0
  for ((h = 0; h < header_count; h++)); do
    header_name_tmpl="$(python3 -c 'import json,sys; print(json.load(sys.stdin)[int(sys.argv[1])][0])' "$h" <<<"$headers_json")"
    header_tmpl="$(python3 -c 'import json,sys; print(json.load(sys.stdin)[int(sys.argv[1])][1])' "$h" <<<"$headers_json")"
    if ! header_name="$(printf '%s' "$header_name_tmpl" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" substitute)"; then
      echo -e "FAIL\t-\t${name}\tunresolved variables in header name"
      header_err=1
      break
    fi
    if ! header_value="$(printf '%s' "$header_tmpl" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" substitute)"; then
      echo -e "FAIL\t-\t${name}\tunresolved variables in header ${header_name}"
      header_err=1
      break
    fi
    if ! python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" check-header \
      "$header_name" "$header_value"; then
      echo -e "FAIL\t-\t${name}\tunsafe header ${header_name}"
      header_err=1
      break
    fi
    curl_headers+=(-H "${header_name}: ${header_value}")
    case_header_names+=("$header_name")
  done
  if [[ "$header_err" -ne 0 ]]; then
    fail=$((fail + 1))
    continue
  fi

  # Inject AGENTS.md auth (headers / Basic) unless case already set the header.
  inject="$(python3 -c 'import json,sys; print("1" if json.load(open(sys.argv[1])).get("inject_auth_on_requests",True) else "0")' "${E2E_AUTH_MANIFEST:-${STATE_DIR}/auth.manifest.json}")"
  if [[ "$inject" == "1" ]]; then
    skip_csv="$(IFS=,; echo "${case_header_names[*]}")"
    auth_file="$(mktemp)"
    if python3 "${SCRIPT_DIR}/lib/build_curl_auth.py" \
      "${E2E_AUTH_MANIFEST:-${STATE_DIR}/auth.manifest.json}" \
      --skip-names "$skip_csv" >"$auth_file"; then
      while IFS=$'\t' read -r kind hname hval; do
        case "$kind" in
          H) curl_headers+=(-H "${hname}: ${hval}") ;;
          U) curl_extra+=(-u "$hname") ;;
        esac
      done <"$auth_file"
    else
      rm -f "$auth_file"
      echo -e "FAIL\t-\t${name}\tfailed to inject auth from AGENTS.md manifest"
      fail=$((fail + 1))
      continue
    fi
    rm -f "$auth_file"
  fi

  body=""
  if [[ -n "$body_tmpl" ]]; then
    if ! body="$(printf '%s' "$body_tmpl" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" substitute)"; then
      echo -e "FAIL\t-\t${name}\tunresolved variables in body"
      fail=$((fail + 1))
      continue
    fi
    if ! printf '%s' "$body" | python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" check-body; then
      echo -e "FAIL\t-\t${name}\trefusing curl @filepath body"
      fail=$((fail + 1))
      continue
    fi
  fi

  response_file="$(mktemp)"
  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$response_file" -w '%{http_code}' \
      "${curl_extra[@]+${curl_extra[@]}}" \
      "${curl_headers[@]+${curl_headers[@]}}" \
      -X "$method" "$url" --data-raw "$body" || echo "000")"
  else
    code="$(curl -sS -o "$response_file" -w '%{http_code}' \
      "${curl_extra[@]+${curl_extra[@]}}" \
      "${curl_headers[@]+${curl_headers[@]}}" \
      -X "$method" "$url" || echo "000")"
  fi

  assert_output="$(mktemp)"
  if python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" assert "$code" "$expects_json" <"$response_file" >"$assert_output" 2>&1; then
    echo -e "PASS\t${code}\t${name}\t$(python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" redact-log <"$response_file")"
    pass=$((pass + 1))
  else
    message="$(cat "$assert_output" 2>/dev/null || true)"
    echo -e "FAIL\t${code}\t${name}\t${message}\t$(python3 "${SCRIPT_DIR}/lib/substitute_and_assert.py" redact-log <"$response_file")"
    fail=$((fail + 1))
  fi
  rm -f "$response_file" "$assert_output"
done

echo "PASS=${pass} FAIL=${fail}"
[[ "$fail" -eq 0 ]]
