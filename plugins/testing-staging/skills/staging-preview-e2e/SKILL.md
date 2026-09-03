---
name: staging-preview-e2e
description: >-
  Use when validating a PR on preview/staging, QA-ing changed API behaviour on
  a preview URL, running e2e_tests/http cases against staging, checking Sentry
  during preview QA, or reporting staging E2E / preview QA results to chat or
  the issue tracker.
---

# Staging preview E2E

Act as **QA for the current PR**, not only as an HTTP smoke runner.

This skill is **project-agnostic**. The repo under test owns
`e2e_tests/http/**/*.http`. This skill owns execution, mutable state under
`state/`, coverage judgement, and reporting.

**Precedence:** if that repo has `e2e_tests/AGENTS.md`, its rules override this
skill on conflict (deploy, fixtures, auth, extra checks).

Validate the **complete PR diff**. The linked ticket **adds** required cases
(it does not shrink scope). Read references before the matching phase:

| Phase | Reference |
|-------|-----------|
| Scope matrix / PASS rules | [qa-coverage.md](references/qa-coverage.md) |
| Creating/editing `.http` | [http-tests.md](references/http-tests.md) |
| Preview reuse/redeploy / URL | [preview-deployment.md](references/preview-deployment.md) |
| State keys / bootstrap | [project-config.md](references/project-config.md) |
| First-run setup (AGENTS.md) | [first-run-setup.md](references/first-run-setup.md) |
| Infer auth from repo | [infer-project-auth.md](references/infer-project-auth.md) |
| Auth from curl examples | [auth-from-curls.md](references/auth-from-curls.md) |
| Chat + tracker report | [reporting.md](references/reporting.md) |

## When to use / not

**Use when:** active PR needs staging/preview QA; changed API behaviour must be
proven on a preview; `.http` cases need to run; Sentry must be checked for the
run; results must go to chat/tracker.

**Do not use when:** local unit/integration only (no preview); docs-only PR with
no prod path; you only need to author `.http` grammar offline (use
[http-tests.md](references/http-tests.md)).

## Workflow (mandatory order)

```text
Tool check → Preconditions → Scope matrix → Parallel (preview + scaffold)
  → L0 OK → Discover fixtures via API → Run .http (happy + errors)
  → Sentry (unexpected always; expected when in scope) → Report/tracker
```

0. **Tool dependencies (hard gate — do this first)**  
   Ensure required tools are present. Run:

   Resolve `SKILL_ROOT` as the directory that contains this `SKILL.md` (plugin
   cache when installed from the marketplace). Scripts already derive it from
   their own location.

   ```bash
   "$SKILL_ROOT/scripts/check_tools.sh"
   ```

   | Tool | Required? | Role |
   |------|-----------|------|
   | `curl` | **yes** | HTTP runner |
   | `python3` (≥3.9 + stdlib used by `scripts/lib/`) | **yes** | parse/assert/decide_preview |
   | `gh` | **yes** | PR / comments / workflow |
   | `gcloud` | no | optional URL resolve; auth failures must not block |
   | Cursor/VS Code extension `anweber.vscode-httpyac` | no | IDE Send Request only |
   | httpYac CLI | **never** | do not require or install |

   - If a **required** tool is missing, ask the user (or require
     `CHECK_TOOLS_INSTALL=1`) before installing via the OS package manager
     (`brew`, `apt-get`, `dnf`, `yum`, `pacman`, or `zypper`). Package names
     are allowlisted. Do **not** invent a runner without those tools.
   - Optional tools (`gcloud`, httpYac plugin) are reported only — never
     auto-installed. Never install the httpYac CLI.
   - Exit `0` → continue. Exit `1` → **stop** (declined install, unsupported
     PM, install failure, or still missing). Surface the error to the user
     (may need `sudo`, network, or PATH). `CHECK_TOOLS_NO_INSTALL=1` forces
     check-only.
   - `scripts/run.sh` also runs this check at startup.
   - Scripts must stay Bash 3.2-compatible (macOS `/bin/bash`).
1. **Preconditions**
   - Resolve active PR (`gh pr view`) and linked ticket when used.
   - **Read the linked ticket** for acceptance criteria and any listed test
     cases / scenarios; feed them into the matrix (additive to the diff).
   - Transition ticket to QA-ready (`JIRA_QA_STATUS`) when configured; else ask.
   - Confirm preview network access (VPN or equivalent) when ingress is private.
   - **First-run / incomplete state (hard gate):** if `state/{repo}/` is missing
     or `scripts/verify_state.sh --step all` fails, follow
     [first-run-setup.md](references/first-run-setup.md) **strictly**
     (one step → confirm → verify → next).
     - If `e2e_tests/AGENTS.md` is missing: **analyze the app repo first**
       ([infer-project-auth.md](references/infer-project-auth.md)) — how calls
       and auth work in code/docs/`.http` — draft AGENTS.md, confirm with the
       user, then ask only for secret **values** (and curls only if still
       ambiguous; [auth-from-curls.md](references/auth-from-curls.md)).
     - Never lead with “qué tipo de auth?” when the repo already shows it.
     - Auth lives only in AGENTS.md; skill scripts stay generic
       (`machine_headers` / `user_basic` / `user_bearer_session`).
     - If `session_variables` are declared, run **Auth procedure** (login →
       persist tokens in `preview.json`) and pass `--step session` before live
       `.http`.
     Never store secrets in the application repo; committing generated
     `e2e_tests/AGENTS.md` without secrets is OK.
2. **Scope matrix** — before preview or scaffolding. Must include:
   - **Every HTTP endpoint modified by the PR** (happy path **and** controlled
     error / boundary cases).
   - Ticket-listed test cases.
   - Leak-safe error responses, L3/L4 as applicable.
   Details in [qa-coverage.md](references/qa-coverage.md).
3. **Parallel** (matrix must exist first):
   - **Preview:** follow [preview-deployment.md](references/preview-deployment.md).
     Run `decide_preview.py` before any `PREVIEW_COMMENT`. On `reuse`, resolve
     URL + L0; on `redeploy`, trigger then smoke. User says preview is up →
     `--force-reuse`.
   - **Scaffold:** add missing L1/L2/L5 `.http` cases with placeholders and
     `# @expect`. Do not call the live API.
4. **Do not run live tests** until Preview succeeds (`reuse`/`redeploy` + L0 OK).
5. **Discover fixtures via API** — with read-only (or safe list/show) preview
   calls, find real data for placeholders; refresh
   `state/{repo}/variables/preview.json` (including `baseUrl` / `gcp` when
   resolved). Prefer discovered IDs over invented ones. For destructive
   endpoints, create and delete only disposable resources this run.
6. **Run `.http`** for open L1/L2/L5 rows (happy path + controlled errors for
   every modified endpoint in scope):

   ```bash
   "$SKILL_ROOT/scripts/run.sh" "$REPO_ROOT/e2e_tests/http/<scope>.http"
   ```

   Exit `0` = selected `.http` passed (not clean QA PASS). `1` = assertion
   failure. `2` = `DATA_STALE` → refresh/fix URL, rerun.

   On every error / 4xx–5xx response under test: assert messages do **not**
   leak internal stack traces, framework names, language, or infrastructure
   that reveal how the service is built.
7. **Sentry (always)** — after the HTTP run (and after intentional L4
   triggers):
   - **Unexpected:** check the project’s error tracker (Sentry MCP/UI) for new
     events caused by this QA run that were **not** planned. Any unexpected
     event → **FAIL** (or OPEN only if tracker unavailable — blocks clean PASS).
   - **Expected:** when the PR/code has controlled capture paths, trigger them
     safely and verify the matching Sentry events appear.
8. **Report** with [reporting.md](references/reporting.md). Update the matrix.
   Post the **same** report in chat **and** as a comment on the linked tracker
   task when one exists. Resolve the ticket from session context or the PR
   (`gh pr view` / title / body / linked issues). If still unknown, ask the
   user for the task key or whether to skip the tracker comment — never guess.

## QA layers (summary)

| Layer | Meaning | Evidence |
|-------|---------|----------|
| **L0** | Service alive | `GET {SMOKE_PATH}` |
| **L1** | HTTP contract (happy path) | `.http` + `# @expect` |
| **L2** | Readable persisted state | read-after-write `.http` |
| **L3** | Non-HTTP side effect | PR unit/integration asserting payload/invariant, or future probe |
| **L4** | Observability | Unexpected Sentry check (always) + expected capture when in scope |
| **L5** | Auth / validation / controlled errors / leak-safe messages | Negative or mixed `.http` |

HTTP green alone never closes L3 or L4.

## Result vocabulary

| Result | Meaning |
|--------|---------|
| **PASS** | Every matrix row evidenced; required HTTP OK; no open L3/L4; no unexpected Sentry |
| **FAIL** | Required HTTP/observability failed, unexpected Sentry, or preview blocked verification |
| **PASS (HTTP only; open risks)** | L0–L2/L5 HTTP green; ≥1 L3/L4 (or other) row still OPEN |

Only **PASS** may transition to deploy-ready (`JIRA_DEPLOY_STATUS`). Always post
the report for FAIL / HTTP-only results.

## Test discovery rules

- Search current repo `e2e_tests/http/` first; reuse complete cases.
- Cover **all PR-modified endpoints**; for each, happy path **and** controlled
  errors from the matrix/ticket.
- Discover fixture values via preview API calls; never hardcode staging
  business identifiers in `.http` — use flattened placeholders from
  `state/{repo}/variables/preview.json`.
- Negative constants like `E2E_NONEXISTENT_*` are allowed.
- Every case needs `# @expect status` and relevant field asserts; error cases
  must also assert leak-safe client-facing messages.
- Prefer L2 read-after-write when a GET/list already exposes the write.
- Never add runners, libraries, fixtures, or docs under `e2e_tests/` beyond
  `.http` (and repo `AGENTS.md` if the project already uses it).
- Never bake product-/repo-specific scenarios into this skill.

Optional (ignored by runner): `# @qa-layer L1`, `# @qa-evidence matrix:row-id`.

## Layout

```text
staging-preview-e2e/
  SKILL.md
  scripts/           # bootstrap, check_tools, run, decide_preview, …
  references/        # coverage, http, preview, project-config, reporting
  assets/            # empty templates only
  state/.gitignore   # keeps package tree empty of secrets
```

Mutable per-repo state (credentials, `preview.json`) lives outside the plugin
cache by default:

`${XDG_STATE_HOME:-~/.local/state}/cursor-staging-preview-e2e/{repo}/`

Override with `E2E_STATE_DIR` (one project) or `E2E_STATE_ROOT` (parent of all
`{repo}/` dirs). Legacy `${SKILL_ROOT}/state/{repo}/` is migrated once on
resolve.
## Common mistakes

| Mistake | Do instead |
|---------|------------|
| Skip `check_tools.sh` | Run it first; install only after approval / `CHECK_TOOLS_INSTALL=1` |
| Blind `/preview` | Run `decide_preview.py` first |
| Clean PASS because `.http` exit 0 | Close every matrix row; L3/L4 + Sentry rules |
| Skip ticket test cases | Read ticket; add those rows to the matrix |
| Test only happy path | Controlled errors for every modified endpoint |
| Invent fixture IDs | Discover via read-only preview API calls |
| Skip Sentry because “HTTP green” | Always check unexpected; verify expected when in scope |
| Truncate Cases with `{…}` | Full one-line JSON per [reporting.md](references/reporting.md) |
| Skip tracker comment without asking | Resolve ticket from PR or ask user / skip explicitly |
| Ticket text as only scope | Full PR diff **plus** ticket cases |
| `gcloud` auth fail → “not deployed” | Resolve URL from comment/state; gcloud is optional |
| Hardcode project/VPN/hostname in skill | Derive from URL/workflow/`preview.json` |
| Put secrets or ephemeral tokens in `.http` | Placeholders only; values in `state/{repo}/.env` or `variables/preview.json` |
| Put ephemeral auth (Bearer, MFA, one-off tokens) in `.env` | Write them under `state/{repo}/variables/preview.json` |
| Ask auth type before reading the repo | Infer from code/docs first ([infer-project-auth.md](references/infer-project-auth.md)) |
| Skip first-run verify gates | One step at a time; `verify_state.sh` must pass |
| Assume API_KEY without evidence | Infer from repo or curls; never invent |
| Live `.http` before L0 | Wait for preview success + smoke |

## Red flags — stop

- Starting QA without a successful `check_tools.sh` run
- “HTTP is green, mark PASS / deploy-ready” with open L3/L4 or unchecked Sentry
- Skipping the scope matrix or ticket-listed cases “to save time”
- Modified endpoint left without happy path or controlled-error coverage
- Error body leaks stack/framework/language/infra details
- Running live tests while preview decision is pending
- Claiming L2 without a real read API
- Encoding one feature’s scenarios into this skill
- Status-only or placeholder report bodies

**All of these mean: fix the process before claiming QA complete.**

## Safety

- Never commit state, secrets, API keys, or real staging fixtures into an
  application repo (`state/.gitignore` ignores everything except `.gitkeep`).
- Never delete pre-existing data.
- Never claim PASS for failed required cases, open L3/L4 risks, unexpected
  Sentry events, or unverified in-scope expected observability checks.
- Never `eval` fixture JSON or `brew shellenv` output; load vars via
  NUL-delimited allowlisted keys only.
- Never send HTTP requests whose host differs from `baseUrl` (same-origin).
- Never put API keys/secrets in reports; omit raw response bodies from runner
  console logs (assert messages only).
- Never install packages without user approval or `CHECK_TOOLS_INSTALL=1`.
- Always persist call variables (`baseUrl`, `gcp`, fixtures) and **any
  ephemeral/extra credentials** (access/refresh tokens, MFA codes kept for the
  run, one-off auth material) in `state/{repo}/variables/preview.json`.
  Long-lived secrets declared in AGENTS.md `credentials` stay in `.env` only.
- **Never** put credential literals (keys, tokens, passwords, Bearer values) in
  `.http` files — only `{{placeholders}}` that resolve from `.env` /
  `preview.json` / inject from the auth manifest.
- Never advance a first-run setup step until `verify_state.sh` for that step
  exits 0; never assume Streaming-style `API_KEY` without AGENTS.md.
