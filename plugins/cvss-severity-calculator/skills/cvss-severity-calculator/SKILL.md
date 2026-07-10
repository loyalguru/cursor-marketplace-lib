---
name: cvss-severity-calculator
description: Calculate vulnerability severity with CVSS v4.0 base metrics for Loyal Guru security tickets, CVEs, penetration test findings, Semgrep findings, cloud findings, and code review security issues. Use when the user asks to calculate severity, classify a vulnerability, score a Jira security ticket, evaluate CVSS, or decide whether a finding is Low, Medium, High, or Critical.
---

# CVSS Severity Calculator

## Purpose

Use this skill to calculate vulnerability severity in a consistent way for Loyal Guru security tickets, internal findings, CVEs, penetration test findings, Semgrep findings, GCP/AWS findings, and code review security issues.

Default to **CVSS v4.0 Base Metrics** unless the user explicitly asks for another version.

## Workflow

1. Gather the vulnerability context:
   - If the user provides a Jira issue key or Atlassian URL, read the issue first.
   - If the user provides a CVE, use the published score from NVD, OSV, GitHub Advisory, vendor advisory, or FIRST when available.
   - If the user provides only a description, infer the metrics from the described exploit path and impact.

2. Assign each CVSS v4.0 Base Metric:
   - Exploitability: `AV`, `AC`, `AT`, `PR`, `UI`
   - Vulnerable system impact: `VC`, `VI`, `VA`
   - Subsequent system impact: `SC`, `SI`, `SA`

3. Build the vector:
   - Format: `CVSS:4.0/AV:.../AC:.../AT:.../PR:.../UI:.../VC:.../VI:.../VA:.../SC:.../SI:.../SA:...`

4. Calculate the score:
   - Prefer the official FIRST CVSS calculator for final confirmation.
   - For terminal calculation, use `offseckit` via the `osk` command.
   - Check whether `osk` already exists before creating a temporary Python virtualenv.
   - Do not modify the project repository just to calculate a CVSS score.
   - If a tool is unavailable, provide the vector and state that the score should be verified in the FIRST calculator.

5. Explain the result:
   - Give the recommended vector, score, and severity first.
   - Explain every metric in plain Spanish.
   - Mention alternative scoring only when a reasonable interpretation changes the severity.

## Severity Bands

Use these CVSS score bands:

| Score | Severity |
| --- | --- |
| `0.0` | None |
| `0.1-3.9` | Low |
| `4.0-6.9` | Medium |
| `7.0-8.9` | High |
| `9.0-10.0` | Critical |

## Terminal Calculator

Use `offseckit` as the default terminal calculator because its CVSS v4.0 output matches the official FIRST calculator for tested vectors.

First check whether `osk` is already available:

```bash
command -v osk
```

If `osk` exists, use it directly:

```bash
osk cvss calc 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N' --json
```

If `osk` does not exist, install and run `offseckit` in a temporary virtualenv:

```bash
tmpdir="$(mktemp -d)"
python3 -m venv "$tmpdir/.venv"
"$tmpdir/.venv/bin/python" -m pip install --upgrade pip
"$tmpdir/.venv/bin/python" -m pip install offseckit
"$tmpdir/.venv/bin/osk" cvss calc 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N' --json
```

Never install calculation packages into the target project just to compute a CVSS score.

## Metric Guidance

### Exploitability

- `AV:N` Network: exploitable over a network, API, web endpoint, public service, or remotely reachable interface.
- `AV:A` Adjacent: requires same local network, VPC, WiFi, subnet, or adjacent network position.
- `AV:L` Local: requires local account, shell, job execution, local file access, or access to the running host.
- `AV:P` Physical: requires physical device access.

- `AC:L` Low: attack is direct and repeatable once the attacker knows the target.
- `AC:H` High: attack requires race conditions, unusual timing, brittle conditions, or hard-to-reproduce states.

- `AT:N` None: no special deployment condition or prerequisite is needed.
- `AT:P` Present: a specific precondition must already exist, such as a vulnerable feature enabled, uncommon configuration, or specific system state.

- `PR:N` None: no authentication or account is required.
- `PR:L` Low: a basic authenticated user or low-privilege role is required.
- `PR:H` High: admin, owner, maintainer, cloud IAM, or elevated privilege is required.

- `UI:N` None: no victim interaction is needed.
- `UI:P` Passive: victim only has to view or receive content.
- `UI:A` Active: victim must click, upload, approve, submit, or perform an explicit action.

### Vulnerable System Impact

- `VC:H` High: direct disclosure of sensitive data, credentials, tokens, personal data, tenant data, or broad confidential records.
- `VC:L` Low: limited disclosure, existence oracle, account/resource enumeration, internal error details, metadata, or technology fingerprinting.
- `VC:N` None: no confidentiality impact.

- `VI:H` High: attacker can modify critical data, perform unauthorized business actions, alter security settings, or execute code in the vulnerable system.
- `VI:L` Low: attacker can make limited, non-critical changes.
- `VI:N` None: no integrity impact.

- `VA:H` High: attacker can make the vulnerable service unavailable or broadly unusable.
- `VA:L` Low: partial degradation, limited resource consumption, or localized failures.
- `VA:N` None: no availability impact.

### Subsequent System Impact

Use subsequent impact only when the vulnerable component causes impact beyond itself, such as another service, database, tenant, cloud resource, queue, or customer system.

- `SC:H`: sensitive data is exposed in a subsequent system.
- `SC:L`: limited data, metadata, existence, or enumeration is exposed in a subsequent system.
- `SC:N`: no subsequent confidentiality impact.

- `SI:H`: critical modification of another system is possible.
- `SI:L`: limited modification of another system is possible.
- `SI:N`: no subsequent integrity impact.

- `SA:H`: another system can be made unavailable.
- `SA:L`: another system can be partially degraded.
- `SA:N`: no subsequent availability impact.

## Loyal Guru Defaults

- Treat unauthenticated, internet-reachable API vulnerabilities as at least serious: usually `AV:N/PR:N/UI:N`.
- Treat account, customer, tenant, or resource enumeration as `VC:L` by default unless it directly exposes sensitive records.
- Treat internal exception messages and class names as `VC:L`, not `VC:H`, unless they expose secrets or customer data.
- Do not mark a vulnerability Critical only because it is in authentication code. Critical usually requires direct sensitive data disclosure, account takeover, code execution, major data modification, or service-wide outage.
- If a finding combines multiple independent issues, consider scoring the most severe exploit path and note whether it should be split into separate Jira tickets.
- When in doubt between two severities, explain both and recommend the more defensible one for audit and remediation prioritization.

## Output Template

Respond in Spanish using this structure:

```markdown
Recomendación: `Medium`, score `6.9`

Vector: `CVSS:4.0/...`

Desglose:
- `AV:N` Network: [razón]
- `AC:L` Low: [razón]
- `AT:N` None: [razón]
- `PR:N` None: [razón]
- `UI:N` None: [razón]
- `VC:L` Low: [razón]
- `VI:N` None: [razón]
- `VA:N` None: [razón]
- `SC:L` Low: [razón]
- `SI:N` None: [razón]
- `SA:N` None: [razón]

Conclusión:
[1-3 frases sobre por qué esa severidad es proporcional.]

Alternativa:
[Solo si aplica: otra interpretación razonable y cuándo usarla.]
```

## Example: JWT Claim Processing Before Signature Verification

For an unauthenticated OAuth/JWT issue where forged JWT claims are processed before signature verification, allowing account/resource enumeration, arbitrary model probing, and internal error disclosure, but not direct login bypass, data modification, full data disclosure, RCE, or denial of service:

Recommended vector:

`CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N`

Recommended result:

`6.9 Medium`

Use `VC:H` or `SC:H` only if the issue exposes sensitive customer/user records directly, not merely existence or metadata. With `VC:H/SC:L`, the same exploit shape becomes `8.8 High`; with `VC:H/SC:H`, it becomes `9.2 Critical`.
