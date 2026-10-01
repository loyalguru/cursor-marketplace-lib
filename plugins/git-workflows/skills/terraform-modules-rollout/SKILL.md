---
name: terraform-modules-rollout
description: >-
  Guides testing and rollout of terraform-gcp-modules changes into
  terraform-customers via temporary ?ref= pins and Terraform Cloud workspace
  applies. Use when the user mentions terraform-gcp-modules, terraform-customers,
  ?ref=, customers-* workspaces, module plan preview, or deploying a modules PR
  to GCP.
---

# Terraform modules rollout (gcp-modules → customers)

Two repos: `loyalguru/terraform-gcp-modules` (definitions) and
`loyalguru/terraform-customers` (applies them). Merging modules does **not**
change GCP until customers workspaces plan+apply.

## Modes — ask first

Ask which mode before acting. Default is **Guide**.

| Mode | Agent may | Agent must not |
| --- | --- | --- |
| **Guide** (default) | Explain steps, paste commands, interpret plan output | Edit git, open PRs, run terraform, touch TFC |
| **Execute preview** | Create customers branch, set `?ref=`, commit, open temp PR (use create-pr / git-commit skills) | `terraform apply`, TFC New run / Confirm, merge modules, `terraform state rm` |

Rollout after modules merge is **always Guide only** — never apply for the user.

## Phase 1 — Preview with `?ref=`

1. Identify modules branch/PR and the module path changed (e.g. `gcp/bigquery/achievements`).
2. In `terraform-customers`, pin only that source in `_modules/customer_infrastructure/main.tf`:

```hcl
source = "git::git@github.com:loyalguru/terraform-gcp-modules.git//<module-path>?ref=<modules-branch>"
```

Modules normally have **no** `?ref=` (track `main`).

3. Default test workspace: `customers-test-02` (`_workspaces/test_02`). Prefer test over `group_01`/`03`/`04` (prod).
4. Changes under `_modules/` alone often **do not** trigger a TFC speculative plan on the PR. Plan options:
   - Local (from the workspace group dir): `terraform init -upgrade` then `terraform plan`
   - TFC UI New run — UI runs the **workspace VCS branch** (usually `main`), not the temp PR branch, unless VCS speculative plans fire
5. Homebrew: Terraform is not `brew install terraform`. Use:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

Then `terraform login` once for Terraform Cloud.

### Plan review

**Good:** in-place update (`~`) of the expected resource; additive schema/`+` fields as intended.

**Bad — stop:** destroy/recreate of tables/datasets; unexpected IAM churn; `Provider configuration not present` / orphans (workspace state from another branch, e.g. locked for Platform experiments). Do **not** `terraform state rm`. Tell the user to ask Platform / whoever holds the lock.

## Phase 2 — Ship modules

User merges the modules PR to `main` after preview looks right. Agent does not merge unless the user explicitly asks in a separate request.

Close the temp customers PR (**do not merge**). Never leave `?ref=` on customers `main`.

## Phase 3 — Rollout guide (TFC)

Cross-repo module changes do **not** auto-plan customers. User must run workspaces manually.

Org: [LoyalGuru workspaces search=customers](https://app.terraform.io/app/LoyalGuru/workspaces?search=customers)

| Group dir | TFC workspace | Role |
| --- | --- | --- |
| `group_01` | `customers-group-01` | Prod batch 1 |
| `group_02` | `customers-group-02` | Pre / staging |
| `group_03` | `customers-group-03` | Prod batch 2 |
| `group_04` | `customers-group-04` | Newest prod |
| `mobile_app` | `customers-mobile-app` | Mobile |
| `selex` | `customers-selex` | Selex |
| `test` | `customers-test` | Integration test |
| `test_02` | `customers-test-02` | QA / demo / staging |

Checklist to show the user:

1. Confirm modules commit is on `main`.
2. For each unlocked workspace: **New run** → Run type **Plan and apply (standard)** → review plan for the expected module delta → **Confirm** apply only if the plan matches.
3. If **Locked** or plan fails because another branch owns the workspace: skip; ping the lock owner. Do not fight state.
4. Prefer applying test workspaces first, then pre (`group_02`), then prod groups.
5. Close any remaining temp `?ref=` PR.

## Hard rules

- Never auto-apply. Never merge modules unprompted.
- Never `terraform state rm` / state surgery on shared workspaces.
- Temp customers PR body must say do not merge; title includes Jira key when present.
- After preview, remove `?ref=` by closing/discarding the temp branch — ship only via modules `main`.
