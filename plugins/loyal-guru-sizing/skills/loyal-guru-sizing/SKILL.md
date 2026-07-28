---
name: loyal-guru-sizing
description: >-
  Estimate engineering effort using Loyal Guru's T-Size / Fibonacci SP / time
  scale. Write the estimate on Jira in the T-Size field (customfield_11740).
  Calibrate against similar past tickets (estimated T-Size vs actual time).
  If functional doubts block a reliable size, add an internal note tagging
  Loyal Guru people only (reporter if LG, else Request participants / Client Director)
  + project PO.
  If a cross-team dependency is detected, create a product request (New Feature)
  in the owning team's Jira project, copy Organizations / Client / Client Director /
  Request participants / Priority / Labels / Quarter / Due date from the source,
  and link it.
  Use when the user asks for sizing, estimation, story points, T-shirt size,
  SP, effort, or how big a ticket/feature is.
---

# Loyal Guru sizing

When estimating work, **always** use this scale. Do not invent alternate T-shirt or day mappings.

## Scale (canonical)

| T-Size | SP (Fibonacci) | Time effort |
| --- | --- | --- |
| XL | 144 | 1 quarter |
| L | 55 | 1 month |
| M-L | 34 | 3 weeks |
| M | 21 | 2 weeks |
| S-M | 13 | 1.5 week |
| S | 8 | 1 week |
| XS-S | 5 | 3 days |
| XS | 3 | 1 day |
| XXS | 1–2 | 0.5 day |

Reference image: [sizing-scale.png](sizing-scale.png)

## How to estimate

1. **Inspect the real code/path** before sizing (endpoint, service, DB, indexes, tests, docs). Do not size from the ticket text alone.
2. **Calibrate with similar past tickets** (see below). Prefer evidence over gut feel so we neither overshoot nor undershoot.
3. If **functional doubts** block a reliable size, follow **Functional doubts → comment** below before locking T-Size.
4. If a **cross-team dependency** is detected, follow **Dependencies → product request** below.
5. Size the **requested scope only** (e.g. extend existing `GET /customers`, not a new endpoint unless asked).
6. Split **MVP vs full** when complexity diverges (indexes, pagination, fuzzy search, migrations).
7. Report using **all three** columns: T-Size, SP, Time effort.
8. Pick the closest row; if between two, give a range (e.g. `XS-S → S (5–8 SP)`).
9. Call out what would bump the size (performance/indexes, pagination, breaking API changes, multi-service work).
10. When writing the estimate on a Jira ticket, put it in the **T-Size** field (`customfield_11740`). Use the T-Size value from the scale (e.g. `S`, `S-M`, `M`), not SP alone.

## Calibrate with past similar work

Before locking a T-Size, search for **comparable done tickets** and compare **what we sized** vs **what it really took**.

### What to look for

| Signal | Where |
| --- | --- |
| Similar scope | Same domain (API endpoint, connector, audience condition, BQ ingestion, UI condition, etc.), same services, similar blast radius |
| Estimated size | **T-Size** field (`customfield_11740`) on those tickets |
| Actual effort | Worklogs / time spent if present; else cycle time (In Progress → Done), sprint/PR history, comments about spillover |

### How to use it

1. Find 2–5 similar resolved tickets (Jira search / linked epics / same labels/components/repos).
2. For each: note **T-Size estimated** vs **actual time** (map actual days back onto the scale).
3. Adjust the new estimate:
   - Past similar work **took longer** than its T-Size → size up (or keep size and call out risk).
   - Past similar work **finished faster** → size down if scope truly matches.
4. Prefer recent tickets (same stack/process) over old ones.
5. If no good comps exist, say so and size from code inspection alone.

### Output when comps exist

Include a short calibration note, e.g.:

```markdown
**Calibration:** CUS-1234 (S → ~1.5w real), CDP-5678 (S-M → ~1w real) → recommend S-M
```

Goal: refine sizing over time so estimates land closer to reality — avoid systematically oversizing or undersizing.

## Functional doubts → comment

If something **functional is unclear** and that ambiguity would make the T-Size unreliable (scope, acceptance criteria, product rules, who owns eligibility data, MVP vs full, etc.):

1. **Do not invent** product decisions to force a size.
2. Still give a **provisional** range if useful (e.g. `S-M → M-L depending on X`), and say what would lock it.
3. **Add an internal note** (never “Reply to customer”) — see **Who to mention** below.
4. In the comment: list the concrete questions, why they block sizing, and options if any.
5. Deduplicate mentions (same person once).

### Who to mention (Loyal Guru only)

**Never mention customers / external people.** Mentions must be Loyal Guru staff only.

Who counts as Loyal Guru:

- `emailAddress` ends with `@loyal.guru`, **or**
- `accountType: "atlassian"` with a Loyal Guru identity (many LG staff hide email in the API — **missing email ≠ external**), **or**
- known LG staff (PO table, Client Directors below, LG request participants / CS / Delivery).

Who is **not** LG (do not mention):

- `accountType: "customer"`, portal/`qm:` accounts, client-domain emails (e.g. `@decathlon.*`, `@danone.com`).

**Do not** re-route mentions away from the reporter just because `emailAddress` is null. Examples of LG reporters: Marina Deleonardis, Adrián Massaro, Natali Benavides, Alejandro Amezcua, etc.

**Mention order:**

1. Always mention the **PO of the project** (table below).
2. If the **reporter is Loyal Guru** → also mention the reporter (preferred contact).
3. If the **reporter is not Loyal Guru** (true external/customer):
   1. Mention **Request participants** (`customfield_10015`) that are Loyal Guru (skip any external participants).
   2. If there are **no LG request participants**, mention the **Client Director** person from `customfield_11781` using the mapping below.

### Client Director → person (when reporter is external)

| Client Director (field value) | Mention | Account ID |
| --- | --- | --- |
| Alejandro | Alejandro Amezcua Garcia | `5d8352093065f00d32c4ed7d` |
| Miguel | Miguel Gil | `712020:6f35a78b-8d29-4f20-a84c-9b00c199258e` |
| Miriam | Miriam Panico | `640efa3fb05b4e3e7da83fe9` |
| Melina | Melina Ezeiza | `712020:1e9dbefe-e516-4029-bac6-b51bc0a58eed` |
| Diana | Diana Lecha | `5d9b43400d44fc0dca53e537` |

If Client Director is empty/unknown, ask the user before posting.

### Internal note (not reply to customer) — mandatory

On JSM tickets (**CUS**, **LOYAL**, **SE**, **OFFERS**, **NLTCS**, etc.), every sizing/doubts comment **must** be created as **Add internal note**:

- UI: tab **Add internal note** (yellow composer, padlock on the note).
- Not **Reply to customer**.
- Success check in Jira: note has yellow background + padlock; customer portal must not see it.

**Do not use Atlassian MCP `addCommentToJiraIssue` for these comments** until Atlassian ships true Internal note support (`public: false` / `jsdPublic: false`). Today that tool posts **Reply to customer**. `commentVisibility: Service Desk Team` is **not** a valid substitute.

**Current decision (until MCP is fixed):** do **not** post sizing/doubts comments via MCP or API workarounds. Give the user a ready-to-paste draft for **Add internal note** (ADF/markdown with the right LG mentions). Track MCP progress: [ECO-1459](https://jira.atlassian.com/browse/ECO-1459) / [atlassian-mcp-server#139](https://github.com/atlassian/atlassian-mcp-server/issues/139).

When MCP supports Internal notes natively, post with that flag and verify yellow + padlock / `jsdPublic: false` before considering it done.

Never leave a sizing/doubts note as Reply to customer.

### Team → project → PO

| Team | Project | When to use | PO | Account ID |
| --- | --- | --- | --- | --- |
| **CDP** | **CUS** | Default CDP product requests | Esther Alonso | `5dd3a7e02358f10ef5874a8e` |
| **CDP** | **SE** | Audience / segment / SE topics | Esther Alonso | `5dd3a7e02358f10ef5874a8e` |
| **Loyalty** | **LOYAL** | Loyalty engine, rewards eligibility, games rules, points, tiers engine | Gastón Legnani | `60c8672400bdd90068f45b0d` |
| **Perso** | **OFFERS** | Personalization / offers / campaigns delivery | slugo | `712020:ffb40e4c-2cdb-45eb-a46b-40248a1eb26f` |
| **Apps** | **APPS** | Mobile / app work | slugo | `712020:ffb40e4c-2cdb-45eb-a46b-40248a1eb26f` |
| **Analytics** | **NLTCS** | Analytics / NLTCS | Gastón Legnani | `60c8672400bdd90068f45b0d` |

**Mentions:** always post comments with `contentFormat: adf` and real ADF `mention` nodes (`attrs.id` = accountId). Do **not** use markdown/`[~accountid:…]`/`<custom data-type="mention">` — those render as plain text in Jira.

### Comment template (ADF mention shape)

```json
{"type":"mention","attrs":{"id":"<accountId>","text":"@Display Name","accessLevel":""}}
```

Body content (markdown equivalent of what to say):

```markdown
@LG-contact @PO — no podemos cerrar el T-Size con confianza todavía.

Dudas funcionales que bloquean el sizing:
1. …
2. …

Impacto en sizing: provisional X → Y según la respuesta.
¿Podéis confirmar para poder fijar el T-Size?
```

Before posting doubts, **read recent comments** — if answers already exist, acknowledge that and only ask what is still open.

## Dependencies → product request

When sizing detects that delivery **depends on another team** (data they own, eligibility they must expose, API/UI they must build, analytics pipeline, etc.):

1. Identify the **owning team** from the table above.
2. **Create a product request** in that team’s Jira project (do not only mention it in a comment).
3. **Link** the new issue to the source ticket (`Relates`, or `Blocks` if the source is blocked by the dependency).
4. **Assign** the new issue to the project PO.
5. Comment on the **source** ticket with the new key and what is needed.
6. Skip creating a duplicate if an equivalent open linked request already exists.
7. If the dependency is on the **same team** as the source project, do **not** open a cross-team request — keep it in the same ticket / sub-scope.
8. If the owning team is ambiguous, ask the user before creating.
9. **Do not assume Loyalty owns every promo/discount API.** Storefront / CDP product endpoints (e.g. active promos per product for ecommerce paint) may be delivered in **CUS/CDP** even if they read promo data — confirm ownership before opening a LOYAL request.

### How to create

| Target project | Issue type | Notes |
| --- | --- | --- |
| **CUS**, **SE**, **LOYAL**, **OFFERS**, **NLTCS** | **New Feature** | Service-desk style product request |
| **APPS** | **Story** | APPS has no New Feature type |

**Summary:** short, actionable ask for the owning team (what they must deliver).  
**Description:** context from the source ticket, why it blocks, acceptance criteria for the dependency, link to source key.  
**Assignee:** PO of the target project.

### Copy fields from the source ticket (mandatory)

Before `createJiraIssue`, fetch the source with `fields: ["*all"]` (or the list below) and **copy every non-empty field that exists on the target project create screen**. Prefer over-copying; skip only if the target meta rejects the field.

| Field | ID | How to copy |
| --- | --- | --- |
| **Organizations** | `customfield_10004` | `[{"id": "<orgId>"}]` (from source org `id`) |
| **Request participants** | `customfield_10015` | `[{"accountId": "<id>"}, …]` |
| **Client Director** | `customfield_11781` | `{"id": "<optionId>"}` (or `{"value": "Miriam"}`) |
| **Client** | `customfield_10665` | string array as-is (e.g. `["Selex","DECATHLON"]`) |
| **Quarter** | `customfield_10637` | `[{"id": "<optionId>"}]` (or `{"value": "2026 Q4"}`) |
| **Approvers** | `customfield_10029` | `[{"accountId": "<id>"}, …]` if present |
| **Priority** | `priority` | `{"name": "Highest"}` (same as source) |
| **Labels** | `labels` | copy candidate / delivery labels; drop project-noise if needed |
| **Due date** | `duedate` | ISO date string if set on source |
| **Reporter** | `reporter` | keep source reporter when the API allows (`{"accountId": "…"}`) |

Also copy when present on source and writable on target:

- Product-outcome text fields if useful: `customfield_11772` / `11773` / `11774` / `11775` (What do we want / Solutions today / Business Outcome / Solution ideas) — summarize into description if the target screen differs.
- Components / Category only if they make sense on the destination project.

**Workflow:**

1. `getJiraIssue` source with the fields above.
2. `getJiraIssueTypeMetaWithFields` on the **target** project + issue type — only set fields that appear there.
3. `createJiraIssue` with `additional_fields` containing all copyable values (plus assignee = target PO).
4. If create succeeds but some fields were dropped, `editJiraIssue` to set the missing ones.
5. In the summary to the user, list which fields were copied.

Do **not** create a bare ticket with only summary/description/assignee when the source has Organizations, Client, Client Director, or Request participants filled.

### Example (from CUS-1115)

Dependency: Loyalty must materialize reward/game eligibility for audiences → create **New Feature** in **LOYAL**, assign Gastón, link to CUS-1115, comment on CUS-1115, **and copy Organizations / Client / Client Director / Request participants / Priority / Labels / Quarter / Due date from CUS-1115**.

## Jira field

| Field | ID | What to write |
| --- | --- | --- |
| **T-Size** | `customfield_11740` | Canonical T-Size from the scale (`XXS` … `XL`) |

Do not invent another custom field for sizing. If the user asks to “poner el sizing”, update **T-Size**.

## Output format

```markdown
## Sizing

| Scope | T-Size | SP | Time |
| --- | --- | --- | --- |
| MVP | S | 8 | 1 week |
| Full | S-M | 13 | 1.5 week |

**Recommendation:** S (8 SP / 1 week)

**Calibration:** …
**Assumptions:** …
**Upside risks:** …
**Dependencies / product requests:** … (keys created + owning team)
```

## Mapping tips

- Tiny param/validation/docs-only change → **XXS–XS**
- Small existing-endpoint extension + tests + OpenAPI → **XS-S–S**
- Pagination, indexes, cross-service, or fuzzy search → often **S-M–M**
- Multi-week platform work → **M–L+**
- Prefer one recommended size for the ticket default scope; keep full scope as optional uplift.
