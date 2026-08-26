# E2E / staging-preview-e2e — Management (Owner) API

Copy to `e2e_tests/AGENTS.md` in `loyal-guru-api` (or merge sections).

This file overrides the staging-preview-e2e skill on **auth** for this repo.
Prefer **Basic Auth** (`email` + `authentication_token`) for E2E/smoke.
PKCE + Bearer is optional when a case must mirror the Owner app.

## Authentication

Secrets live only in the skill state directory, for example:

`$SKILL_ROOT/state/loyal-guru-api/.env`

Never commit credentials to this repository.

```yaml
auth_mode: user_basic
inject_auth_on_requests: true
credentials:
  - key: OWNER_EMAIL
    required: true
    maps_to: ownerEmail
    notes: Owner user email (e.g. owner@dev.local)
  - key: OWNER_AUTH_TOKEN
    required: true
    maps_to: ownerAuthToken
    notes: User.authentication_token from Rails console/DB — NOT the login password
  - key: CUSTOMER_EMAIL
    required: false
    maps_to: customerEmail
    notes: End-customer email when cases need the customer role
  - key: CUSTOMER_AUTH_TOKEN
    required: false
    maps_to: customerAuthToken
    notes: Customer authentication_token when needed
default_headers:
  - name: Accept
    value: application/vnd.loyalguru-v1
  - name: Content-Type
    value: application/json
smoke:
  basic:
    user_from: ownerEmail
    password_from: ownerAuthToken
```

## Auth procedure (preferred for E2E — Basic Auth)

1. Obtain the token (do not invent it), e.g. in Rails console:
   `User.find_by(email: '<OWNER_EMAIL>').authentication_token`
2. During skill first-run setup, provide `OWNER_EMAIL` and `OWNER_AUTH_TOKEN`
   (and customer pair if needed). Wait for `verify_state.sh` OK on each key.
3. With `inject_auth_on_requests: true`, the runner adds Basic auth
   (`-u email:token`) and default Accept headers on smoke and `.http` calls.
   Cases do not need to repeat `-u`.
4. Customer-role cases that need a different user: temporarily override via
   case-level `Authorization` header, or run a dedicated AGENTS/profile —
   default inject uses owner credentials.
5. No session tokens are required in `preview.json` for Basic Auth.

Example:

```bash
curl -sS "{{baseUrl}}/users" \
  -H 'Accept: application/vnd.loyalguru-v1' \
  -H 'Content-Type: application/json' \
  -u "{{ownerEmail}}:{{ownerAuthToken}}"
```

## Auth procedure (optional — Owner PKCE + Bearer)

Use only when a case must mirror the Owner app. Switch YAML to roughly:

```yaml
auth_mode: user_bearer_session
inject_auth_on_requests: true
session_variables:
  - accessToken
smoke:
  headers:
    - name: Authorization
      value_prefix: "Bearer "
      value_from: accessToken
```

Add `OWNER_PASSWORD` to `credentials` if login needs it. Then:

1. `CODE_VERIFIER` + `CODE_CHALLENGE` = SHA-256 hex of the verifier (64 chars `[a-z0-9_]`).
2. `POST {{baseUrl}}/users/authorization` with `code_challenge` → `authorization`.
3. `POST {{baseUrl}}/users/session` with email, password, `authorization`, `code_verifier`.
4. If `{ "requires_mfa": true }`, ask the user for `mfa_code` and resend — do not skip.
5. Persist into skill `variables/preview.json` (never into `.http`):
   - `accessToken` ← `access_token`
   - `refreshToken` ← `refresh_token` (optional)
6. Authenticated calls use inject and/or `Authorization: Bearer {{accessToken}}`
   (placeholder only — token lives in `preview.json`).

Non-local environments: use `{{baseUrl}}` from preview state, not localhost.
