# Shared HTTP test format

The repository **under test** stores `.http` definitions under:

```text
e2e_tests/http/**/*.http
```

These files are **L1 / L2 / L5** evidence for the staging-preview-e2e skill.
They do not cover **L3** (non-HTTP side effects) or **L4** (observability) by
themselves. See [qa-coverage.md](qa-coverage.md).

Per-project credentials and fixture shapes: [project-config.md](project-config.md).

## State

Run first-run setup ([first-run-setup.md](first-run-setup.md)) from the app repo.
Bootstrap creates:

```text
state/{repo}/
  .env                       # long-lived AGENTS.md credentials only
  auth.manifest.json         # parsed Authentication YAML (no secrets)
  variables/preview.json     # baseUrl, gcp, fixtures, ephemeral credentials
```

Auth for smoke and `.http` placeholders comes from AGENTS.md + state — not from
literals in `.http`. **Never** put keys, tokens, passwords, or Bearer values in
`.http` files; ephemeral credentials go in `variables/preview.json`.

## Allowlisted `.http` grammar

```http
### case_name
# @qa-layer L1
# @qa-evidence matrix:optional-row-id
# @expect status 200
# @expect jsonpath $.code == "invalid_request"
# @expect jsonpath $.data length 1
POST {{baseUrl}}/example/resource
{{authHeaderKey}}: {{apiKey}}
{{authHeaderSecret}}: {{apiSecret}}
Content-Type: application/json
Accept: application/json

{
  "id": {{resourceId}}
}
```

Header names / Basic / Bearer come from project `e2e_tests/AGENTS.md`. The
example above is Streaming-style; Management uses Basic or Bearer per that
repo’s Auth procedure.

- Case: `### name`
- Required status: `# @expect status <code>`
- Body assertions: JSONPath equality or `length <n>`
- Optional docs (ignored by runner): `# @qa-layer …`, `# @qa-evidence …`
- Methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- Headers end at the first blank line
- Body must be JSON
- Variables use `{{flatName}}` from flattened `preview.json` plus auth
  `maps_to` from `.env` / inject. Never embed secret literals in the case body
  or headers.

The parser rejects `@name`, `??`, dynamic `{{$…}}` variables, multipart,
script blocks, uploads, and multiple request lines in one case.

## L2 read-after-write

When persisted state is readable via an existing endpoint, prefer ordered cases
in the same or dependent files: mutate, then GET/list, then assert fields that
prove the write. Do not invent read APIs for E2E.

## Happy path and controlled errors

For every PR-modified endpoint in scope, author (or reuse) cases for:

1. **Happy path** — expected success status and contract fields.
2. **Controlled errors** — validation/auth/not-found/conflict (as applicable),
   with `# @expect status` and public error code/message asserts.

On error responses, also assert the body is **leak-safe**: no stack traces,
exception class names, framework/language fingerprints, or infra debug pages.
See [qa-coverage.md](qa-coverage.md) L5.

## Fixture discovery

Prefer real preview data discovered via list/show (or equivalent) API calls,
written into `state/{repo}/variables/preview.json`, over invented business ids.

## What not to assert in `.http`

Do not use HTTP expects to “cover” values that only exist in pub/sub payloads,
external-client requests, or other non-response channels. Track those as L3 in
the QA matrix and cite PR automated tests (or a future side-effect probe).

## Runner

Required system tools must be present. `check_tools.sh` is the gate (also
invoked by `run.sh`). Missing **required** tools may be installed via the OS
package manager only after interactive confirmation or
`CHECK_TOOLS_INSTALL=1` (`brew` / `apt-get` / `dnf` / `yum` / `pacman` /
`zypper`):

```bash
# SKILL_ROOT = directory containing this skill's SKILL.md
"$SKILL_ROOT/scripts/check_tools.sh"   # may prompt; or CHECK_TOOLS_INSTALL=1
"$SKILL_ROOT/scripts/run.sh" /path/to/repo/e2e_tests/http/example.http
```

Required: `curl`, `python3` (≥3.9), `gh`. Optional (not auto-installed):
`gcloud`, IDE httpYac plugin. Never install the httpYac CLI.
`CHECK_TOOLS_NO_INSTALL=1` skips installs (check-only).

Security notes for cases:

- URLs must stay on the same host as `{{baseUrl}}` (runner enforces this).
- Fixture keys in `preview.json` must be safe identifiers (`[A-Za-z_][A-Za-z0-9_]*`
  path segments).
- Runner console logs omit response bodies; use asserts + the QA report for
  contract details.

`run.sh` preflight requires:

- non-auth `{{variables}}` referenced by the target `.http` files
- smoke `GET {SMOKE_PATH}` using auth from AGENTS.md manifest (headers or Basic)

Exit codes: `0` HTTP cases passed, `1` assertion failure, `2` `DATA_STALE`.

Exit `0` means the selected `.http` files passed — not that overall staging QA
is a clean PASS. The skill still applies the scope matrix rules in
[qa-coverage.md](qa-coverage.md).
