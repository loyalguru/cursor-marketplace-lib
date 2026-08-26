# First-run setup (step-by-step)

Hard gate before QA. Configuration is **always** driven by the app repo’s
`e2e_tests/AGENTS.md` (`## Authentication` YAML + `## Auth procedure`).

Skill **scripts are project-agnostic**: they read the manifest and support
machine headers, Basic user auth, and Bearer-after-login. Do not patch scripts
per repo.

## Absolute rules

1. **Infer from the project first** ([infer-project-auth.md](infer-project-auth.md)).
   Ask the user only for secret **values** and facts the repo cannot provide.
2. **One step at a time.** Do not start the next step until verify exits `0`.
3. After the user confirms / provides a value, **run the verify command**.
4. If verify prints `SETUP_INCOMPLETE` (exit `1`): fix and **repeat the same
   step**. Never skip ahead.
5. Never invent credentials, tokens, or `baseUrl`.
6. Never log secret values.
7. **Ephemeral/extra credentials** (Bearer, refresh, MFA kept for follow-ups,
   one-off tokens) → only `state/{repo}/variables/preview.json`. Never `.http`.
8. Do not start matrix / preview live / `.http` until
   `verify_state.sh --step all` succeeds.
9. If AGENTS declares `session_variables`, run **Auth procedure** and pass
   `--step session` before live calls.

```bash
# SKILL_ROOT = directory containing this skill's SKILL.md
```

## When to enter

Enter if state is missing/incomplete or `verify_state.sh --step all` fails.

---

## Step 0 — Ensure `e2e_tests/AGENTS.md`

### 0a — File already exists

Parse/validate:

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step agents
```

On failure: help fix the YAML (prefer re-reading the repo for clues); stay on
this step.

### 0b — File **missing** (infer, then confirm, then write)

Do **not** start by asking “qué tipo de autenticación usáis?”.

1. **Analyze the application repo** per
   [infer-project-auth.md](infer-project-auth.md): `.http`, README/docs, auth
   middleware, request specs, OpenAPI, workflows, Accept/version headers,
   Basic/Bearer/PKCE/API-key signals.
2. Draft full `## Authentication` YAML + `## Auth procedure` (no secrets).
3. Show the user a short evidence summary (paths) + the draft. Wait for
   confirmation or corrections.
4. If the scan is still ambiguous: ask for **one working curl** (and login
   curls if needed) per [auth-from-curls.md](auth-from-curls.md) — then refine
   the draft. Do not ask for a blank auth-type menu if curls/code can decide.
5. Write `e2e_tests/AGENTS.md` in the **application** repo.
6. **Verify before Step 1:**

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step agents
```

Optional examples (only if the user wants a starting template after a failed
scan):

- [`assets/AGENTS.streaming.example.md`](../assets/AGENTS.streaming.example.md)
- [`assets/AGENTS.management.example.md`](../assets/AGENTS.management.example.md)
- [`assets/agents-authentication.example.md`](../assets/agents-authentication.example.md)

---

## Step 1 — Bootstrap project state

Confirm slug/path, then:

```bash
"$SKILL_ROOT/scripts/bootstrap.sh"
```

**Verify:**

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step bootstrap
```

---

## Steps 2…N — Credential **values** (not schema)

Schema (`key`, `maps_to`, header names, Basic vs Bearer) must already come from
AGENTS.md (inferred). Here you only collect **values**.

Read `state/{repo}/auth.manifest.json` → `credentials` **in order**.

For each key:

1. Show `notes` (and any inferred how-to-get from Auth procedure).
2. Ask for the secret/value (or default / skip for optionals).
3. Write `.env` → verify before the next key:

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step credential --key '<KEY>'
```

Do not re-ask “is this an API key header?” if AGENTS already defines it.

---

## Step baseUrl

Prefer resolving from preview comments / prior QA. Ask the user only if still
unknown. Write `baseUrl` in `variables/preview.json`.

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step base_url
```

---

## Step session (Bearer / login flows)

If `session_variables` is non-empty:

1. Follow **## Auth procedure** (prefer steps inferred from the repo).
2. Persist **all ephemeral credentials** (access/refresh tokens, MFA codes kept
   for the run, one-off auth material) into
   `state/{repo}/variables/preview.json` — **never** into `.http` files.
3. Verify:

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step session
```

Re-run when tokens are stale (`DATA_STALE` / preflight session check).

---

## Final

```bash
"$SKILL_ROOT/scripts/verify_state.sh" --step all
```

Then continue normal QA. `run.sh` injects auth from the manifest when
`inject_auth_on_requests: true`.

## Red flags

- Asking auth type / header names before searching the repo
- Patching skill scripts for one API
- Inventing endpoints or secret values
- Advancing without verify exit 0
- Skipping Auth procedure when `session_variables` are required
- Writing tokens / MFA / one-off secrets into `.http` instead of
  `state/{repo}/variables/preview.json`
