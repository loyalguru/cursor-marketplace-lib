#!/usr/bin/env bash
# Block env names that must never be exported from AGENTS.md / preview.json.

e2e_is_reserved_env_key() {
  # Exact match only: Unix env names are case-sensitive, so fixture / maps_to
  # ids like user, home, tmp, env, path must not be treated as USER/HOME/etc.
  local key="$1"
  case "$key" in
    PATH|LD_PRELOAD|LD_LIBRARY_PATH|LD_AUDIT|\
    DYLD_INSERT_LIBRARIES|DYLD_LIBRARY_PATH|DYLD_FRAMEWORK_PATH|\
    PYTHONPATH|PYTHONHOME|PYTHONSTARTUP|PYTHONUSERBASE|\
    BASH_ENV|ENV|IFS|CDPATH|SHELLOPTS|BASHOPTS|\
    HOME|USER|LOGNAME|SHELL|TMPDIR|TEMP|TMP|\
    SSL_CERT_FILE|SSL_CERT_DIR|CURL_CA_BUNDLE|REQUESTS_CA_BUNDLE|\
    OPENSSL_CONF|OPENSSL_MODULES|OPENSSL_ENGINES|SSLKEYLOGFILE|\
    HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|FTP_PROXY|\
    http_proxy|https_proxy|all_proxy|no_proxy|ftp_proxy|\
    CURL_HOME|XDG_CONFIG_HOME|\
    NODE_OPTIONS|NODE_PATH|PERL5LIB|PERL5OPT|RUBYLIB|RUBYOPT|\
    GIT_DIR|GIT_WORK_TREE|GIT_OBJECT_DIRECTORY|\
    GH_TOKEN|GH_HOST|GITHUB_TOKEN|PROMPT_COMMAND|PS4|TERMCAP|TERMINFO)
      return 0
      ;;
  esac
  case "$key" in
    DYLD_*|BASH_FUNC_*|LD_*)
      return 0
      ;;
  esac
  return 1
}
