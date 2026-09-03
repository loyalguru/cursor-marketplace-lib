# Testing Staging

Cursor plugin for QA of the active PR on preview/staging.

## What's Included

### Skills (`skills/`)

| Skill | Purpose |
|-------|---------|
| `staging-preview-e2e` | Builds a coverage matrix from the PR diff and ticket, reuses or redeploys preview, runs `e2e_tests/http` cases, checks Sentry, and reports results. |

## Usage

Ask Cursor to run staging/preview E2E QA on the current PR, or invoke `/staging-preview-e2e`.
