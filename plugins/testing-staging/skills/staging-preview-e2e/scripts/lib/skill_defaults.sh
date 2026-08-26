#!/usr/bin/env bash
# Deploy / QA knobs owned by the skill (not per-project state).

e2e_load_skill_defaults() {
  export SMOKE_PATH="${SMOKE_PATH:-/ping}"
  export PREVIEW_COMMENT="${PREVIEW_COMMENT:-/preview}"
  export PREVIEW_TZ="${PREVIEW_TZ:-Europe/Madrid}"
  export PREVIEW_SHUTDOWN_HOUR="${PREVIEW_SHUTDOWN_HOUR:-18}"
  export JIRA_QA_STATUS="${JIRA_QA_STATUS:-Ready for QA}"
  export JIRA_DEPLOY_STATUS="${JIRA_DEPLOY_STATUS:-Ready to deploy}"

  export smokePath="$SMOKE_PATH"
}
