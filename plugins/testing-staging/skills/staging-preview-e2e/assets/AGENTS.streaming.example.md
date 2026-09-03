# E2E / staging-preview-e2e — Streaming API

Copy to `e2e_tests/AGENTS.md` in `loyal-guru-api-streaming-v2` (or merge sections).

This file overrides the staging-preview-e2e skill on **auth** for this repo.
Runner calls stay generic; credentials and headers are declared here.

## Authentication

Secrets live only in the skill state directory, for example:

`${XDG_STATE_HOME:-~/.local/state}/cursor-staging-preview-e2e/loyal-guru-api-streaming-v2/.env`

Never commit credentials to this repository.

```yaml
auth_mode: machine_headers
inject_auth_on_requests: true
credentials:
  - key: API_KEY
    required: true
    maps_to: apiKey
    notes: Company Streaming API key
  - key: SECRET_KEY
    required: true
    maps_to: apiSecret
    notes: Company Streaming API secret
  - key: AUTH_HEADER_KEY
    required: false
    maps_to: authHeaderKey
    default: X-Api-Key
    notes: HTTP header name for API_KEY (default X-Api-Key)
  - key: AUTH_HEADER_SECRET
    required: false
    maps_to: authHeaderSecret
    default: X-Api-Secret
    notes: HTTP header name for SECRET_KEY (default X-Api-Secret)
default_headers:
  - name: Accept
    value: application/json
smoke:
  headers:
    - name_from: authHeaderKey
      value_from: apiKey
    - name_from: authHeaderSecret
      value_from: apiSecret
      when: set
```

## Auth procedure

No login / token exchange. With `inject_auth_on_requests: true`, the runner
attaches API key headers from the manifest on every request. `.http` cases may
omit auth headers (or keep placeholders; duplicates are skipped by name).
