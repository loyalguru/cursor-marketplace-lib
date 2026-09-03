# Inferring AGENTS.md from curls (fallback)

Use this **after** [infer-project-auth.md](infer-project-auth.md) when the repo
scan is incomplete or the user corrects the draft.

When `e2e_tests/AGENTS.md` is still missing or wrong:

1. Prefer evidence already found in code/docs.
2. Ask for **working curl example(s)** of an authenticated call (and login
   curls if the token is obtained separately).
3. Merge curls + code evidence into `e2e_tests/AGENTS.md`.
4. Continue first-run for secret **values** only.

Do **not** change skill scripts. Do **not** lead with a blank auth-type quiz if
curls or code already show the mechanism.

## Auth families

| Family | `auth_mode` | Typical curls | Manifest shape |
|--------|-------------|---------------|----------------|
| Machine-to-machine API keys | `machine_headers` | `-H 'X-Api-Key: …'` / secret header | `smoke.headers` + credentials for keys/header names |
| User Basic (email:token) | `user_basic` | `-u 'email:TOKEN'` + version Accept | `smoke.basic` + email/token credentials |
| User session (login then Bearer) | `user_bearer_session` | login POSTs then `-H 'Authorization: Bearer …'` | login credentials + `session_variables` + Bearer `value_from` / `value_prefix` |

Always set:

```yaml
inject_auth_on_requests: true
```

## What to extract from each curl

- **Static headers** (`Accept`, `Content-Type`, API version) → `default_headers`
- **Secret header values** → `credentials` + `smoke.headers` (`name` /
  `name_from` + `value_from`)
- **`-u user:pass`** → `smoke.basic` (`user_from` / `password_from`)
- **`Authorization: Bearer <token>`** from a prior login → login secrets in
  `.env`, **token only in** `state/{repo}/variables/preview.json` as
  `accessToken` (never in `.http`), `session_variables`, and:

  ```yaml
  - name: Authorization
    value_prefix: "Bearer "
    value_from: accessToken
  ```

- **Multi-step login** (PKCE, MFA) → **Auth procedure** Markdown only.

## Questions (only gaps — one at a time)

1. If no authenticated curl in docs/specs: ask for one working curl.
2. If Bearer without login evidence: ask for login curl(s).
3. If two modes remain equally plausible after code+curls: ask which is default
   for E2E (one confirmation).

## Red flags

- Embedding real secrets into AGENTS.md
- Encoding one product’s PKCE into skill scripts
- Skipping `verify_state.sh --step agents` after writing AGENTS.md
- Asking for API key header names that already appear in the codebase
