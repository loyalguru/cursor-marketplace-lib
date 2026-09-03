# Infer auth and call patterns from the application repo

When there is **no** usable `e2e_tests/AGENTS.md` (or first-run state is empty),
**analyze the project before asking the user anything** that the code or docs
can already answer.

Do **not** change skill scripts. Infer into a draft `e2e_tests/AGENTS.md`, then
ask only for **secret values** and facts that cannot be found in the repo.

## Order (mandatory)

```text
1. Scan repo for auth + HTTP call patterns
2. Draft AGENTS.md Authentication YAML + Auth procedure (show user)
3. Confirm draft (or refine with optional curls if still ambiguous)
4. verify --step agents → bootstrap → ask only unresolved credential VALUES
```

Never open with “what auth type do you use?” if the repo already shows it.

## Where to look (search in parallel)

| Signal | Examples to search |
|--------|--------------------|
| Existing E2E | `e2e_tests/http/**/*.http`, any `*.http`, Postman/Insomnia collections |
| Docs | `README*`, `docs/**`, `CONTRIBUTING*`, wiki links, “curl”, “Authentication” |
| API version / Accept | `application/vnd.`, `Accept:`, API version middleware |
| Machine auth | `X-Api-Key`, `X-Api-Secret`, `api_key`, `API_KEY`, `SECRET_KEY`, HMAC |
| Basic / token user | `authenticate_or_request_with_http_basic`, `authentication_token`, `-u `, `http_basic` |
| Session / OAuth / PKCE | `code_challenge`, `code_verifier`, `/authorization`, `/session`, `access_token`, `Bearer`, `PKCE`, `Doorkeeper`, `oauth` |
| MFA | `requires_mfa`, `mfa_code`, `otp` |
| Controllers / middleware | `before_action :authenticate`, `current_user`, `authorize!` |
| Client SDKs / specs | OpenAPI/Swagger, RSpec request specs with headers, VCR cassettes |
| Preview / smoke | `/ping`, `/health`, `SMOKE`, Cloud Run, `/preview` in workflows |

Also read `e2e_tests/AGENTS.md` if a partial file exists, and any
`e2e_tests/AGENTS*.md` drafts.

## Map findings → AGENTS fields

| Finding | Set in YAML |
|---------|-------------|
| Fixed API key headers | `auth_mode: machine_headers`, `smoke.headers`, credentials for key/secret (+ optional header name keys with defaults) |
| `-u email:authentication_token` or HTTP Basic with token | `auth_mode: user_basic`, `smoke.basic` |
| Login then `Authorization: Bearer` | `auth_mode: user_bearer_session`, `session_variables: [accessToken]`, smoke Bearer header with `value_prefix` / `value_from`; store token in `variables/preview.json` only |
| Multi-step login / PKCE / MFA | **Auth procedure** steps only; any mid-run credential → `variables/preview.json`, never `.http` |
| Required `Accept: application/vnd…` | `default_headers` |
| Smoke path | Prefer skill default `/ping` unless repo documents another (note for the agent; knobs stay in skill_defaults) |

Always draft with:

```yaml
inject_auth_on_requests: true
```

## What you may infer vs what you must ask

| Infer (do not ask if clear) | Ask only if missing |
|-----------------------------|---------------------|
| `auth_mode` | Confirmation if two modes coexist and which is default for E2E |
| Header **names**, Basic vs Bearer shape | Secret **values** (keys, tokens, passwords) |
| Login URL paths and body field names | Real email/password/token for staging |
| `default_headers` | Staging `baseUrl` if not yet on a preview |
| `maps_to` / `key` names | MFA code when API returns `requires_mfa` |
| Auth procedure outline | Curl paste **only** when code/docs are insufficient |

## Ambiguity rules

1. If the repo documents **both** M2M and user auth: prefer the path used by
   existing `e2e_tests/http` cases; else prefer the simpler E2E path (Basic over
   full PKCE when both exist for the same API); state the choice in AGENTS and
   ask the user to confirm **once**.
2. If still unclear after a thorough scan: ask for one working curl (see
   [auth-from-curls.md](auth-from-curls.md)) — not a blank “what auth do you use?”.
3. Never invent secret values. Never invent endpoints that are not in the repo.

## Output before asking secrets

Show the user a short summary:

- Inferred `auth_mode` and evidence (file paths).
- Draft `## Authentication` YAML (no secrets).
- Draft `## Auth procedure` (login steps if needed).

Wait for confirmation, write `e2e_tests/AGENTS.md`, run
`verify_state.sh --step agents`, then continue first-run for **values** only.
