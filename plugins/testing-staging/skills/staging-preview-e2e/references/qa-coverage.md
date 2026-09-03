# QA coverage model

Use this reference while running the staging-preview-e2e skill. It defines how
to build the scope matrix and decide PASS without encoding any product- or
repository-specific scenario into the skill.

## Purpose

Preview HTTP checks prove request/response behaviour. They do **not**
automatically prove:

- payloads sent to external clients or message buses
- async finalize / mark-used / compensation flows
- observability events
- invariants that never appear in the HTTP body

The skill’s job as QA is to **inventory** those behaviours from the PR diff and
require evidence for each one.

## Building the matrix

1. Take the full PR diff against the base branch (`gh pr diff` / commits).
2. **Read the linked ticket/issue** for acceptance criteria and any explicit
   test cases, scenarios, or QA notes. Add those rows to the matrix. Do **not**
   shrink the matrix to the ticket text alone — ticket cases are **additive**.
3. Inventory **every HTTP endpoint modified by the PR**. Each modified
   endpoint needs matrix coverage for:
   - **Happy path** (L1, plus L2 when a read API can observe the write)
   - **Controlled errors** (L5: validation, auth, not-found, conflict, etc.
     that the change touches or the ticket lists)
4. Add one row per distinct behaviour a reviewer would care about.
5. Assign every applicable layer (a row may be `L1,L3` or `L1,L2,L5`).
6. Write an evidence plan before running preview tests.
7. After the run, set each row to `OK`, `NOK`, or `OPEN`.

Suggested row granularity: one user-visible or system-visible behaviour, not
one file.

## Layer rules

### L0 — Smoke

- Always run `GET {SMOKE_PATH}` after preview URL resolution (`SMOKE_PATH` from
  skill defaults; default `/ping`).
- Smoke is the source of truth that a reused or freshly deployed preview is
  alive. A `gcloud` auth failure is not an L0 failure.
- Failure stops the workflow (or forces redeploy when evaluating reuse).

### L1 — HTTP contract (happy path)

Applies when the PR changes an endpoint’s request schema, status codes, or
response body — and for **every modified endpoint**, even if only behaviour
details changed.

Evidence: allowlisted `.http` case with `# @expect status` and field asserts.

### L2 — Readable persistence

Applies when the PR writes state that an existing GET/list (or equivalent)
can observe.

Evidence: mutate then read in `.http` (same file or ordered cases). If no read
API exists, do **not** invent one; leave L2 unmarked and cover via L1/L3 as
appropriate.

### L3 — Non-HTTP side effect

Applies when the PR changes code that builds or sends a payload outside the
HTTP response: queue/event publishers, external HTTP clients, finalize hooks,
webhooks, etc.

Evidence (any one is enough to mark the row covered):

1. A PR automated test (unit or integration) that asserts the side-effect
   payload or invariant (preferred when no staging probe exists).
2. A future skill-owned side-effect probe, when implemented.

Not evidence:

- HTTP success alone
- Response fields that do not include the side-effect payload
- “Looks fine in logs” without a captured assert

If neither (1) nor (2) exists, the row stays **OPEN** and clean PASS is
forbidden.

### L4 — Observability / Sentry

Two checks; both matter for PASS:

**L4-unexpected (always, every QA run):** after executing the scoped `.http`
cases (and any intentional triggers), query the project’s error tracker
(Sentry MCP/UI) for new events attributable to this preview/QA window that
were **not** planned as expected captures. Any unexpected event → matrix
**NOK** / overall **FAIL**. If the tracker is unavailable → **OPEN** (blocks
clean PASS); never claim PASS by skipping the check.

**L4-expected (when in scope):** when the PR or ticket changes a controlled
capture path (or documents an expected Sentry error), add a safe trigger case,
provoke that path, and verify the matching event appears in Sentry. Missing
verification when in scope → **OPEN** or **NOK**.

### L5 — Boundaries and leak-safe errors

Applies when the PR changes validation, auth, envelope rules, partial-success
behaviour — and for **controlled error cases** of every modified endpoint in
scope (ticket cases included).

Evidence: negative or mixed `.http` cases.

**Leak-safe client errors (required on error responses under test):** assert
that status/body messages do **not** expose internal implementation details
that reveal language, framework, stack traces, ORM, cloud product internals,
or similar. Safe: stable public error codes/messages. Unsafe examples:
exception class names, backtraces, “Rack/Rails/Sinatra”, SQL fragments tied to
internals, raw provider HTML/debug pages. Leak found → **NOK** / **FAIL**.

## Fixture discovery via API

Before relying on stale `preview.json` values:

1. Use read-only (or safe list/show) preview API calls appropriate to the repo
   to locate real entities needed by the cases.
2. Write discovered ids/codes into `state/{repo}/variables/preview.json`
   (preserve nested shape; also keep `baseUrl` / `gcp` there).
3. Prefer discovered data over invented business identifiers.
4. Negative-test constants (`E2E_NONEXISTENT_*`) remain allowed.

## PASS decision

```text
clean PASS
  = L0 OK
  + every matrix row OK (all modified endpoints: happy + controlled errors)
  + ticket-listed cases covered
  + leak-safe asserts OK on error responses
  + L4-unexpected clean (no unexpected Sentry)
  + L4-expected verified when in scope
  + no OPEN L3/L4 (or other) risks
  + no failed required HTTP/observability checks

PASS (HTTP only; open risks)
  = L0 OK
  + required L1/L2/L5 HTTP cases OK
  + at least one OPEN risk remains
  (still must not ignore a known unexpected Sentry event — that is FAIL)

FAIL
  = deploy/preview failure
  OR any required HTTP/observability check NOK
  OR unexpected Sentry event from the QA run
  OR client error response leaks internal implementation details
```

Only **clean PASS** may move the ticket to the project’s deploy-ready status.

## Mapping diff signals → layers (generic)

Use as heuristics, not a closed list:

| Diff signal | Likely layers |
|-------------|----------------|
| Route/handler/schema/serializer | L1, often L5 |
| DB write + existing read API | L1, L2 |
| Publisher / event payload / external client | L3 (+ L1 if HTTP also changed) |
| Error wrapping, status mapping, error capture | L4 (+ L1) |
| Feature flag branch on the path | same layers as the branch’s behaviour |
| Docs-only / test-only with no prod path change | usually no new matrix row |

When the org’s API/monitoring Best Practices apply to the repo under test,
use them as **extra matrix prompts**, not as hardcoded skill scenarios:

| Practice signal | Matrix prompt |
|-----------------|---------------|
| List/show field parity, pagination envelope `data[]`, null-omit, required/optional enums | L1/L5 contract rows |
| Pub/Sub publisher/subscriber or admin-ops quota paths | L3 (payload/invariant); do not treat HTTP 200 as coverage |
| New Datadog/metrics or error-capture paths | L4 verification |

## Optional `.http` annotations

The runner ignores unknown `#` comments today. Useful documentation:

```http
### example_case
# @qa-layer L1
# @qa-evidence matrix:create-resource-happy
# @expect status 200
```

For L3 rows covered by PR tests, record evidence in the matrix / report as the
test name, not as a fake HTTP assert.

## Future side-effect probes

When/if the skill gains async probes, keep them **generic** (subscribe/assert
on configured attributes). Do not hardcode product event names in `SKILL.md`.
Until then, L3 coverage is PR automated tests + honest OPEN risks.

## Anti-patterns

- Declaring staging QA PASS because all `.http` files exited 0 while L3 rows
  are open
- Skipping ticket-listed test cases
- Covering only happy path for a modified endpoint
- Leaving a PR-modified endpoint without matrix rows
- Encoding a single feature’s or single repo’s scenarios into the skill
- Hardcoding staging business fixtures instead of discovering via API
- Claiming L2 coverage without a real read API
- Using the ticket title as the only scope source
- Hardcoding cloud projects, regions, VPN profiles, or hostnames in the skill
- Truncating report Cases with `{…}` or status-only rows
- Treating `gcloud` auth failure as proof the preview is down
- Skipping `decide_preview.py` under time pressure
- Skipping Sentry because HTTP was green
- Ignoring unexpected Sentry events from the QA run
- Accepting error bodies that leak stack/framework/language/infra details
