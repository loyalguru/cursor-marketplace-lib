#!/usr/bin/env bash
# Resolve STATE_DIR for the repo under test: state/{repo-name}/

e2e_repo_slug_from_git() {
  local repo_root origin slug
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -z "$repo_root" ]]; then
    return 1
  fi
  origin="$(git -C "$repo_root" remote get-url origin 2>/dev/null || true)"
  if [[ -z "$origin" ]]; then
    return 1
  fi
  slug="$(python3 "${SCRIPT_DIR}/lib/resolve_project.py" "$origin" 2>/dev/null || true)"
  if [[ -z "$slug" ]]; then
    return 1
  fi
  printf '%s\n' "$slug"
}

e2e_resolve_state_dir() {
  # Prefer explicit override of the full project state path.
  if [[ -n "${E2E_STATE_DIR:-}" ]]; then
    STATE_DIR="$E2E_STATE_DIR"
    export STATE_DIR
    export E2E_ENV_FILE="${E2E_ENV_FILE:-${STATE_DIR}/.env}"
    export E2E_VARS_FILE="${E2E_VARS_FILE:-${STATE_DIR}/variables/preview.json}"
    export E2E_PROJECT_SLUG="${E2E_PROJECT_SLUG:-$(basename "$STATE_DIR")}"
    return 0
  fi

  local slug
  if ! slug="$(e2e_repo_slug_from_git)"; then
    echo "ERROR: cannot resolve project state dir." >&2
    echo "Run from a git repo with a parseable 'origin' remote, or set E2E_STATE_DIR." >&2
    return 1
  fi

  STATE_DIR="${SKILL_ROOT}/state/${slug}"
  export STATE_DIR
  export E2E_PROJECT_SLUG="$slug"
  export E2E_ENV_FILE="${E2E_ENV_FILE:-${STATE_DIR}/.env}"
  export E2E_VARS_FILE="${E2E_VARS_FILE:-${STATE_DIR}/variables/preview.json}"
}
