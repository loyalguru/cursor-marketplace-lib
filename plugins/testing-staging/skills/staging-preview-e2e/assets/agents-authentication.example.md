# Authentication section template for e2e_tests/AGENTS.md

Copy into your application repo as `e2e_tests/AGENTS.md` (or merge the
`## Authentication` + `## Auth procedure` sections into an existing file).

The staging-preview-e2e skill **refuses** first-run setup until this YAML parses.

## Authentication

Secrets live only in the skill `state/{repo}/.env` — never commit them here.

```yaml
auth_mode: machine_headers   # or user_basic | user_bearer_session
inject_auth_on_requests: true
credentials:
  - key: EXAMPLE_USER
    required: true
    maps_to: exampleUser
    notes: Describe what the user must provide
  - key: EXAMPLE_SECRET
    required: true
    maps_to: exampleSecret
    notes: Describe how to obtain this secret
default_headers:
  - name: Accept
    value: application/json
smoke:
  headers:
    - name: X-Example
      value_from: exampleSecret
  # OR basic auth:
  # basic:
  #   user_from: exampleUser
  #   password_from: exampleSecret
# Optional — required after Auth procedure (Bearer flows):
# session_variables:
#   - accessToken
```

## Auth procedure

Document **how** the agent authenticates before live `.http` calls:

1. Where to get each credential.
2. Whether requests use headers, Basic `-u`, or Bearer after login.
3. What to write into skill `state/{repo}/variables/preview.json` for any
   ephemeral credential (tokens, MFA material kept for the run) — **never**
   into `.http` files.
4. MFA / version headers / role-specific users if any.

See also:

- `assets/AGENTS.streaming.example.md`
- `assets/AGENTS.management.example.md`
