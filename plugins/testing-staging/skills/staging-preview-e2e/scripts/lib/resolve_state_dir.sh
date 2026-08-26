#!/usr/bin/env bash
# Resolve STATE_DIR for the repo under test outside the plugin cache.
# Default: ${XDG_STATE_HOME:-$HOME/.local/state}/cursor-staging-preview-e2e/{repo}

e2e_default_state_root() {
  if [[ -n "${E2E_STATE_ROOT:-}" ]]; then
    printf '%s\n' "$E2E_STATE_ROOT"
    return 0
  fi
  printf '%s\n' "${XDG_STATE_HOME:-$HOME/.local/state}/cursor-staging-preview-e2e"
}

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
    export STATE_ROOT="$(cd "$(dirname "$STATE_DIR")" 2>/dev/null && pwd || dirname "$STATE_DIR")"
    export E2E_ENV_FILE="${E2E_ENV_FILE:-${STATE_DIR}/.env}"
    export E2E_VARS_FILE="${E2E_VARS_FILE:-${STATE_DIR}/variables/preview.json}"
    export E2E_PROJECT_SLUG="${E2E_PROJECT_SLUG:-$(basename "$STATE_DIR")}"
    return 0
  fi

  local slug stable_root legacy_dir
  if ! slug="$(e2e_repo_slug_from_git)"; then
    echo "ERROR: cannot resolve project state dir." >&2
    echo "Run from a git repo with a parseable 'origin' remote, or set E2E_STATE_DIR." >&2
    return 1
  fi

  stable_root="$(e2e_default_state_root)"
  export STATE_ROOT="$stable_root"
  STATE_DIR="${stable_root}/${slug}"
  legacy_dir="${SKILL_ROOT}/state/${slug}"

  # One-shot: move per-repo state out of the commit-SHA plugin cache.
  # Use || return: callers invoke via `if ! e2e_resolve_state_dir`, which disables
  # set -e for this function body (failed mkdir/mv would otherwise be swallowed).
  if [[ ! -e "$STATE_DIR" && -d "$legacy_dir" ]]; then
    mkdir -p "$stable_root" || return 1
    mv "$legacy_dir" "$STATE_DIR" || return 1
    echo "Migrated project state ${legacy_dir} → ${STATE_DIR}" >&2
  fi

  export STATE_DIR
  export E2E_PROJECT_SLUG="$slug"
  export E2E_ENV_FILE="${E2E_ENV_FILE:-${STATE_DIR}/.env}"
  export E2E_VARS_FILE="${E2E_VARS_FILE:-${STATE_DIR}/variables/preview.json}"
}
