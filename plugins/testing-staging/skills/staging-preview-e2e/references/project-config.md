# Per-project configuration

Skill-owned local state adapts the runner to each repository. Nothing here is
committed to application repos.

**Auth is not defined by this skill.** Credentials, smoke auth (headers vs
Basic), Accept headers, and login procedures live in the app repo’s
`e2e_tests/AGENTS.md`. On first run, the agent **infers** as much as possible
from the project ([infer-project-auth.md](infer-project-auth.md)), then asks
only for secret values ([first-run-setup.md](first-run-setup.md)).

State is grouped by **git repo name** (from `origin`, without owner):

`git@github.com:loyalguru/loyal-guru-api.git` → `state/loyal-guru-api/`

## Bootstrap

Run from the application repo (so `origin` and `e2e_tests/AGENTS.md` resolve):

```bash
"$SKILL_ROOT/scripts/bootstrap.sh"
```

Requires a parseable `## Authentication` YAML in `e2e_tests/AGENTS.md`. Creates:

```text
state/{repo}/
  .env                     # long-lived AGENTS.md credentials only
  auth.manifest.json       # parsed auth (no secrets)
  variables/preview.json   # baseUrl, gcp, fixtures, ephemeral credentials
```

## `e2e_tests/AGENTS.md` (required for setup)

Must include:

1. `## Authentication` with a fenced YAML block (`credentials`, `smoke`,
   optional `default_headers`, optional `session_variables`).
2. `## Auth procedure` describing how to log in / attach auth to requests.

Examples to copy:

| Product | Asset |
|---------|--------|
| Template | [`assets/agents-authentication.example.md`](../assets/agents-authentication.example.md) |
| Streaming | [`assets/AGENTS.streaming.example.md`](../assets/AGENTS.streaming.example.md) |
| Management / Owner | [`assets/AGENTS.management.example.md`](../assets/AGENTS.management.example.md) |

## `state/{repo}/.env`

Only **long-lived** keys declared in AGENTS.md `credentials` (API keys, owner
email/token, passwords used to log in). The skill does **not** hardcode
`API_KEY` / `SECRET_KEY`. Keep mode `600`.

Do **not** put mid-run tokens (Bearer access/refresh, MFA codes, one-off auth
material) here — those belong in `variables/preview.json`.

## `state/{repo}/variables/preview.json`

| Key | Required | Purpose |
|-----|----------|---------|
| `baseUrl` | yes | Preview API base URL |
| `gcp.*` | no | Cloud project / region / service |
| fixtures | no | Nested business ids for `{{placeholders}}` |
| ephemeral credentials | when needed | Session/access/refresh tokens, MFA material kept for the run, any extra one-off auth value |

**Hard rule:** any credential needed only for the current QA run (or obtained
during login) must be written into this JSON and referenced as
`{{accessToken}}` (etc.). **Never** paste those values into `.http` files.

## Skill-owned deploy / QA knobs

In `scripts/lib/skill_defaults.sh` (not in state):

| Key | Default |
|-----|---------|
| `SMOKE_PATH` | `/ping` |
| `PREVIEW_COMMENT` | `/preview` |
| `PREVIEW_TZ` | `Europe/Madrid` |
| `PREVIEW_SHUTDOWN_HOUR` | `18` |
| `JIRA_QA_STATUS` | `Ready for QA` |
| `JIRA_DEPLOY_STATUS` | `Ready to deploy` |

## Verify gates

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step agents
"$SKILL_ROOT/scripts/verify_state.sh" --step bootstrap
"$SKILL_ROOT/scripts/verify_state.sh" --step credential --key OWNER_EMAIL
"$SKILL_ROOT/scripts/verify_state.sh" --step base_url
"$SKILL_ROOT/scripts/verify_state.sh" --step session
"$SKILL_ROOT/scripts/verify_state.sh" --step all
```

## Auth in `.http` files

Placeholders only — **no credential literals**. Values come from `.env`
(maps_to), `preview.json` (fixtures + ephemeral tokens), and/or manifest
inject.

Streaming-style placeholders (optional if inject is on):

```http
{{authHeaderKey}}: {{apiKey}}
{{authHeaderSecret}}: {{apiSecret}}
```

Bearer after login (token must already be in `preview.json`):

```http
Authorization: Bearer {{accessToken}}
```

Prefer `inject_auth_on_requests: true` so cases omit auth headers entirely.

Do not put credentials in the application repository.

## Switching repositories

1. Open the other git root (parseable `origin`).
2. Ensure that repo has `e2e_tests/AGENTS.md`.
3. Run first-run setup / bootstrap for the new `state/{repo}/`.
