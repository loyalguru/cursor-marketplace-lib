#!/usr/bin/env bash
# Verify runner + workflow dependencies. If required tools are missing,
# install them with the OS package manager only after explicit approval.
# Exit 1 only if install is impossible or still missing after install.
# Optional tools are reported only (never auto-installed).
# Never install the httpYac CLI.
#
# Env:
#   CHECK_TOOLS_NO_INSTALL=1  — check only; do not install
#   CHECK_TOOLS_INSTALL=1     — allow non-interactive install of required tools

set -euo pipefail

missing=()
warnings=()

require_cmd() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    missing+=("$tool")
  fi
}

collect_missing() {
  missing=()
  require_cmd curl
  require_cmd python3
  require_cmd gh
}

detect_package_manager() {
  if command -v brew >/dev/null 2>&1; then
    echo brew
  elif command -v apt-get >/dev/null 2>&1; then
    echo apt
  elif command -v dnf >/dev/null 2>&1; then
    echo dnf
  elif command -v yum >/dev/null 2>&1; then
    echo yum
  elif command -v pacman >/dev/null 2>&1; then
    echo pacman
  elif command -v zypper >/dev/null 2>&1; then
    echo zypper
  else
    echo unknown
  fi
}

# Map a required command name to package names for the PM (allowlist only).
packages_for_tool() {
  local pm="$1"
  local tool="$2"
  case "${pm}:${tool}" in
    brew:curl) echo "curl" ;;
    brew:python3) echo "python" ;;
    brew:gh) echo "gh" ;;
    apt:curl) echo "curl" ;;
    apt:python3) echo "python3" ;;
    apt:gh) echo "gh" ;;
    dnf:curl|yum:curl) echo "curl" ;;
    dnf:python3|yum:python3) echo "python3" ;;
    dnf:gh|yum:gh) echo "gh" ;;
    pacman:curl) echo "curl" ;;
    pacman:python3) echo "python" ;;
    pacman:gh) echo "github-cli" ;;
    zypper:curl) echo "curl" ;;
    zypper:python3) echo "python3" ;;
    zypper:gh) echo "gh" ;;
    *) echo "" ;;
  esac
}

# Only allow known package name tokens (defense in depth).
assert_safe_pkg_token() {
  local pkg="$1"
  if [[ ! "$pkg" =~ ^[a-zA-Z0-9@._+-]+$ ]]; then
    echo "ERROR: refusing unsafe package token: ${pkg}" >&2
    return 1
  fi
}

install_packages() {
  local pm="$1"
  shift
  local pkg
  if (($# == 0)); then
    return 0
  fi
  for pkg in "$@"; do
    assert_safe_pkg_token "$pkg" || return 1
  done
  echo "Installing via ${pm}: $*" >&2
  case "$pm" in
    brew)
      brew install "$@"
      ;;
    apt)
      sudo apt-get update -y
      sudo apt-get install -y "$@"
      ;;
    dnf)
      sudo dnf install -y "$@"
      ;;
    yum)
      sudo yum install -y "$@"
      ;;
    pacman)
      sudo pacman -Sy --noconfirm "$@"
      ;;
    zypper)
      sudo zypper --non-interactive install "$@"
      ;;
    *)
      echo "ERROR: unsupported package manager: ${pm}" >&2
      return 1
      ;;
  esac
}

confirm_install() {
  local pkgs="$1"
  if [[ "${CHECK_TOOLS_INSTALL:-0}" == "1" ]]; then
    echo "CHECK_TOOLS_INSTALL=1: proceeding with install of: ${pkgs}" >&2
    return 0
  fi
  if [[ "${CHECK_TOOLS_NO_INSTALL:-0}" == "1" ]]; then
    echo "ERROR: CHECK_TOOLS_NO_INSTALL=1 set; not installing." >&2
    return 1
  fi
  if [[ -t 0 ]]; then
    echo "About to install required tools via OS package manager: ${pkgs}" >&2
    printf "Proceed? [y/N] " >&2
    local answer=""
    read -r answer || true
    case "$answer" in
      y|Y|yes|YES) return 0 ;;
      *)
        echo "ERROR: install declined." >&2
        return 1
        ;;
    esac
  fi
  echo "ERROR: missing required tools: ${missing[*]}" >&2
  echo "Re-run with CHECK_TOOLS_INSTALL=1 to allow package-manager install of: ${pkgs}" >&2
  echo "Or install manually, then re-run." >&2
  return 1
}

refresh_brew_path() {
  # Avoid eval "$(brew shellenv)". Only prepend brew bindirs.
  local prefix
  prefix="$(brew --prefix 2>/dev/null)" || return 0
  if [[ -n "$prefix" && -d "${prefix}/bin" ]]; then
    PATH="${prefix}/bin:${prefix}/sbin:${PATH}"
    export PATH
  fi
}

install_missing_required() {
  local pm pkgs pkg tool
  local -a to_install=()
  local -a seen=()

  pm="$(detect_package_manager)"
  if [[ "$pm" == "unknown" ]]; then
    echo "ERROR: missing required tools: ${missing[*]}" >&2
    echo "No supported package manager found (brew, apt-get, dnf, yum, pacman, zypper)." >&2
    echo "Install curl, python3 (>=3.9), and gh, then re-run." >&2
    return 1
  fi

  echo "Package manager: ${pm}" >&2
  for tool in "${missing[@]}"; do
    pkgs="$(packages_for_tool "$pm" "$tool")"
    if [[ -z "$pkgs" ]]; then
      echo "ERROR: no package mapping for '${tool}' on ${pm}" >&2
      return 1
    fi
    for pkg in $pkgs; do
      local already=0
      local s
      for s in "${seen[@]+"${seen[@]}"}"; do
        if [[ "$s" == "$pkg" ]]; then
          already=1
          break
        fi
      done
      if [[ "$already" -eq 0 ]]; then
        seen+=("$pkg")
        to_install+=("$pkg")
      fi
    done
  done

  if ! confirm_install "${to_install[*]}"; then
    return 1
  fi

  if ! install_packages "$pm" "${to_install[@]}"; then
    echo "ERROR: package install failed for: ${to_install[*]}" >&2
    echo "Install manually with your OS package manager, then re-run." >&2
    return 1
  fi

  if [[ "$pm" == "brew" ]]; then
    refresh_brew_path
  fi
  hash -r 2>/dev/null || true
}

collect_missing

if ((${#missing[@]} > 0)); then
  echo "Missing required tools: ${missing[*]}" >&2
  if ! install_missing_required; then
    exit 1
  fi
  collect_missing
  if ((${#missing[@]} > 0)); then
    echo "ERROR: still missing after install: ${missing[*]}" >&2
    echo "Ensure the installer’s bin dir is on PATH, then re-run." >&2
    exit 1
  fi
  echo "Required tools installed successfully." >&2
fi

# Runner scripts need Python 3.9+ (zoneinfo) and stdlib imports used by lib/.
# Use -I so a planted cwd sitecustomize/json cannot run during the tool check.
if ! python3 -I - <<'PY'
import sys
if sys.version_info < (3, 9):
    sys.stderr.write(
        "ERROR: python3 >= 3.9 required (found %s.%s)\n"
        % (sys.version_info.major, sys.version_info.minor)
    )
    raise SystemExit(1)
import argparse, dataclasses, datetime, json, re, typing, urllib.parse, zoneinfo  # noqa: F401
print("python3: OK (%s.%s, stdlib imports ok)" % (sys.version_info.major, sys.version_info.minor))
PY
then
  exit 1
fi

echo "automatic runner: OK (curl python3)"
echo "PR workflow: OK (gh)"

if command -v gcloud >/dev/null 2>&1; then
  echo "cloud CLI: OK (gcloud) — optional; auth failures must not block preview reuse"
else
  warnings+=("gcloud")
  echo "cloud CLI: MISSING (optional; resolve URL from deploy comment / state)" >&2
fi

plugin_found=0
for editor in cursor code; do
  if command -v "$editor" >/dev/null 2>&1; then
    if "$editor" --list-extensions 2>/dev/null | tr '[:upper:]' '[:lower:]' \
      | grep -qx 'anweber.vscode-httpyac'; then
      plugin_found=1
      break
    fi
  fi
done

if [[ "$plugin_found" -eq 0 ]]; then
  for root in \
    "${HOME}/.cursor/extensions" \
    "${HOME}/.vscode/extensions" \
    "${HOME}/.vscode-server/extensions"; do
    if compgen -G "${root}/anweber.vscode-httpyac-*" >/dev/null; then
      plugin_found=1
      break
    fi
  done
fi

if [[ "$plugin_found" -eq 1 ]]; then
  echo "manual httpYac plugin: OK"
else
  warnings+=("anweber.vscode-httpyac")
  echo "manual httpYac plugin: MISSING (install anweber.vscode-httpyac)" >&2
  echo "  (blocks only IDE Send Request; skill runner still works)" >&2
fi

echo "tool check: REQUIRED ok"
if ((${#warnings[@]} > 0)); then
  echo "tool check: optional missing: ${warnings[*]}" >&2
fi

exit 0
