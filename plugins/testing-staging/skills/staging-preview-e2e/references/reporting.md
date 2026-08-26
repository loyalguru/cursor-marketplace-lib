# Report and tracker

Use the same report in chat and the issue tracker.

## Template

```markdown
## Staging preview E2E — [TICKET-KEY] / PR #<n>

**Preview service:** `<service-name-or-n/a>`
**Base URL:** `<service-url>`
**PR:** <github-pr-url>
**Result:** PASS | FAIL | PASS (HTTP only; open risks)

### Scope matrix
| Behaviour | Layers | Evidence | Result |
|-----------|--------|----------|--------|
| … | L1, L3 | `e2e_tests/http/….http` / `Test…` / tracker / gap | OK/NOK/OPEN |

### Cases
| Case | Endpoint | Request | Expected response | Response | Result |
|------|----------|---------|-------------------|----------|--------|
| … | `POST /…` | `{…}` | `HTTP <code> {…}` | `HTTP <code> {…}` | OK/NOK |

### Observability
- **Unexpected Sentry:** checked / clean | unexpected event(s) found | skipped (reason) — list event ids/titles if any
- **Expected Sentry:** triggered / verified / not in scope / skipped (reason)

### Error leak check
- Error responses reviewed for stack/framework/language/infra leaks: OK | NOK (cite case)

### Open risks
- Any L3/L4 (or other) row still without evidence — or `(none)`

### Notes
- Ticket cases included, fixture discovery calls, disposable resources, DATA_STALE, follow-ups
```

## Cases table rules

For every case row, always fill JSON bodies — never status-only, never
truncated placeholders like `{…}`, never omit a column:

- **Request:** full JSON request body sent (compact one-line JSON). If the
  method has no body, write `(none)`.
- **Expected response:** `HTTP <status>` plus the full JSON body the case
  should return (from `# @expect` / known contract). Compact one-line JSON.
  If the contract expects an empty body, write `HTTP <status> (empty)`.
- **Response:** `HTTP <status>` plus the full JSON body actually returned by
  the preview API for that run. Compact one-line JSON. If empty or non-JSON,
  write `HTTP <status> (empty)` or the raw body text.
- **Result:** `OK` or `NOK`.

Do not redact response fields needed to understand the assertion (codes,
messages, ids). Do not put secrets (API keys, tokens, passwords) in the
report. Prefer public error codes over raw tokens; if a field is clearly a
credential, replace with `(redacted)`.

## Tracker comment (mandatory after the run)

Post the **same** report body (template above) as a comment on the linked
tracker issue whenever a ticket can be resolved. Chat gets the report too.

### Resolve the linked task

1. Prefer the ticket key already used in this QA session (preconditions /
   matrix header).
2. If unknown, inspect the active PR for a linked issue:
   - `gh pr view --json title,body,closingIssuesReferences,url`
   - Branch name / PR title / body for keys like `PROJ-123`
   - Closing/linked issues from GitHub–Jira integration when present
3. If still unknown: **ask the user once** — provide the ticket key **or**
   explicitly choose to **skip** the tracker comment for this run.
4. Never invent a ticket key. Never post to a guessed issue.

### Post

- Use the tracker MCP / `addCommentToJiraIssue` (or the project’s equivalent)
  with the full report markdown (no secrets).
- If posting fails (auth, permissions): note it under **Notes** in the chat
  report and ask whether to retry or skip — do not silently omit.

### Skip

Only when the user explicitly says to ignore/skip the tracker comment, or
there is no ticket and they decline to provide one. Record that choice in
**Notes**.

## Tracker transitions

| Result | Post report? | Transition to deploy-ready? |
|--------|--------------|-------------------------------|
| **PASS** | yes | yes, when `JIRA_DEPLOY_STATUS` is configured |
| **PASS (HTTP only; open risks)** | yes | **no** |
| **FAIL** | yes | **no** |

Any FAIL, open risk, unexpected Sentry event, error-message leak, or
unverified in-scope expected L4 prevents deploy-ready. Still post the report
(chat + tracker comment when a task is resolved) so QA status is visible.
