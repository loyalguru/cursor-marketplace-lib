# AGENTS.md

## Cursor Cloud specific instructions

This repository is the **Loyal Guru Cursor plugins marketplace**: a static library of
plugins (skills, agents, rules, commands, and MCP configs) consumed by the Cursor IDE.
It is **not** a runtime application — there is no server, database, port, or build step.

### Services

There are no local services to run. External integrations (Atlassian, Datadog, Notion,
Figma) are hosted MCP endpoints referenced by each plugin's `mcp.json` and are only
exercised inside Cursor at runtime, not by this repo.

### Dependencies

There is no package manager and no dependencies to install (no `package.json`, lockfile,
or `node_modules`). The only requirement is Node.js (already present on the VM); the
validator uses Node built-ins only.

### Validate / test / "build"

The single verification command (documented in `README.md` and `docs/add-a-plugin.md`) is:

```bash
node scripts/validate-template.mjs
```

Run it from the repository root. It checks `.cursor-plugin/marketplace.json`, each
`plugins/<name>/.cursor-plugin/plugin.json`, referenced paths (logo/rules/skills/agents/
commands/hooks/mcpServers), and required YAML frontmatter. It exits `0` on success and
`1` on failure. Non-fatal "no hooks.json / no mcp.json" lines are informational warnings,
not errors.

### Dev loop for adding/editing a plugin

1. Create `plugins/<name>/.cursor-plugin/plugin.json` (plus any `rules/`, `skills/`,
   `agents/`, `commands/`, `mcp.json`, `assets/`).
2. Register it in `.cursor-plugin/marketplace.json` (see `docs/add-a-plugin.md`).
3. Run `node scripts/validate-template.mjs` and fix all reported errors before committing.
