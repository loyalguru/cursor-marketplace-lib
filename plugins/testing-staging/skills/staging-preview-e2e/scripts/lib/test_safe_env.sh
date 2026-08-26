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
assert_reserved HTTP_PROXY
assert_reserved HTTPS_PROXY
assert_reserved ALL_PROXY
assert_reserved NO_PROXY
assert_reserved FTP_PROXY
assert_reserved http_proxy
assert_reserved https_proxy
assert_reserved all_proxy
assert_reserved no_proxy
assert_reserved ftp_proxy
assert_reserved CURL_HOME
assert_reserved XDG_CONFIG_HOME
assert_reserved SSL_CERT_FILE
assert_reserved CURL_CA_BUNDLE
assert_reserved OPENSSL_CONF
assert_reserved OPENSSL_MODULES
assert_reserved OPENSSL_ENGINES
assert_reserved SSLKEYLOGFILE
assert_reserved SCRIPT_DIR
assert_reserved SKILL_ROOT
assert_reserved STATE_DIR
assert_reserved STATE_ROOT
assert_reserved _E2E_LIB_DIR
assert_reserved E2E_AUTH_MANIFEST
assert_reserved E2E_ENV_FILE
assert_reserved E2E_VARS_FILE
assert_reserved E2E_SUBST_ALLOW
assert_reserved E2E_AUTH_SUBST_ALLOW
assert_reserved GCONV_PATH

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
assert_allowed e2eToken
assert_allowed script_dir

# python3 -c / python3 - put cwd on sys.path and load site; a PR under QA can
# plant json.py or sitecustomize.py after e2e_load_env exported secrets.
if ! declare -F e2e_python >/dev/null; then
  echo "FAIL: e2e_python helper missing" >&2
  fail=1
else
  hijack_dir="$(mktemp -d)"
  marker="${hijack_dir}/pwned"
  cat >"${hijack_dir}/json.py" <<'PY'
import os
from pathlib import Path
Path(os.environ["E2E_PWN_MARKER"]).write_text("pwned\n", encoding="utf-8")
raise SystemExit("hijacked json")
PY
  cat >"${hijack_dir}/sitecustomize.py" <<'PY'
import os
from pathlib import Path
Path(os.environ["E2E_PWN_MARKER"]).write_text("sitecustomize\n", encoding="utf-8")
PY

  (
    cd "$hijack_dir"
    export E2E_PWN_MARKER="$marker"
    export PREVIEW_SECRET=should-not-leak
    # Unprotected python3 -c is the regression baseline (must be hijackable).
    rm -f "$marker"
    python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"[]" >/dev/null 2>&1 || true
    if [[ ! -f "$marker" ]]; then
      echo "FAIL: baseline python3 -c did not load cwd json.py (test invalid)" >&2
      exit 1
    fi
    rm -f "$marker"
    if ! out="$(e2e_python -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"[]" 2>&1)"; then
      echo "FAIL: e2e_python -c failed: ${out}" >&2
      exit 1
    fi
    if [[ "$out" != "0" ]]; then
      echo "FAIL: e2e_python -c unexpected output: ${out}" >&2
      exit 1
    fi
    if [[ -f "$marker" ]]; then
      echo "FAIL: e2e_python -c executed cwd json.py" >&2
      exit 1
    fi
    rm -f "$marker"
    if ! e2e_python -c 'print("ok")' >/dev/null; then
      echo "FAIL: e2e_python -c print failed" >&2
      exit 1
    fi
    if [[ -f "$marker" ]]; then
      echo "FAIL: e2e_python -c executed cwd sitecustomize.py" >&2
      exit 1
    fi
    rm -f "$marker"
    if ! e2e_python - >/dev/null <<'PY'
import json
assert json.loads("[]") == []
print("ok")
PY
    then
      echo "FAIL: e2e_python - (stdin) failed" >&2
      exit 1
    fi
    if [[ -f "$marker" ]]; then
      echo "FAIL: e2e_python - executed cwd json.py" >&2
      exit 1
    fi
  ) || fail=1
  rm -rf "$hijack_dir"
fi

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

echo "ok: safe_env case-sensitive reserved check"
