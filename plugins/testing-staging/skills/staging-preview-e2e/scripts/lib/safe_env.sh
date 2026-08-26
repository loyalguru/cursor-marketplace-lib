#!/usr/bin/env bash
# Block env names that must never be exported from AGENTS.md / preview.json.

e2e_is_reserved_env_key() {
  local key="$1"
  local upper
  upper="$(printf '%s' "$key" | tr '[:lower:]' '[:upper:]')"
  case "$upper" in
    PATH|LD_PRELOAD|LD_LIBRARY_PATH|LD_AUDIT|\
    DYLD_INSERT_LIBRARIES|DYLD_LIBRARY_PATH|DYLD_FRAMEWORK_PATH|\
    PYTHONPATH|PYTHONHOME|PYTHONSTARTUP|PYTHONUSERBASE|\
    BASH_ENV|ENV|IFS|CDPATH|SHELLOPTS|BASHOPTS|\
    HOME|USER|LOGNAME|SHELL|TMPDIR|TEMP|TMP|\
    SSL_CERT_FILE|SSL_CERT_DIR|CURL_CA_BUNDLE|REQUESTS_CA_BUNDLE|\
    NODE_OPTIONS|NODE_PATH|PERL5LIB|PERL5OPT|RUBYLIB|RUBYOPT|\
    GIT_DIR|GIT_WORK_TREE|GIT_OBJECT_DIRECTORY|\
    GH_TOKEN|GH_HOST|GITHUB_TOKEN|PROMPT_COMMAND|PS4|TERMCAP|TERMINFO)
      return 0
      ;;
  esac
  case "$upper" in
    DYLD_*|BASH_FUNC_*|LD_*)
      return 0
      ;;
  esac
  return 1
}
