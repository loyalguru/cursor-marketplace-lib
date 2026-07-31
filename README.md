# Loyal Guru - Cursor Plugins

Team Marketplace for Loyal Guru's Cursor plugins. Provides shared skills, agents, and rules to streamline development workflows across the team.

## Active plugins

Registered in `marketplace.json` and available to all team members:

- **git-workflows**: Commit, PR, CI, merge conflict, and branch validation workflows
- **pm**: Ticket-oriented PM workflows with MCP integration, ticket writing, and board summarization
- **testing-reliability**: Datadog dashboards, performance optimization, and testing agents
- **planning**: Strategic planning workflows including devil's advocate analysis for decision making
- **cvss-severity-calculator**: CVSS v4.0 severity calculation for security findings
- **loyal-guru-sizing**: T-Size estimation for Jira tickets (Loyal Guru scale)
- **productivity**: Structured planning interviews and decision stress-testing workflows

## Available plugins

Present in the repository but not yet activated in `marketplace.json`. To enable one, add its entry to `.cursor-plugin/marketplace.json`:

- **documentation**: README updates, weekly review summaries, markdown naming, and docs writing
- **design**: Wireframes, component design support, and mockup workflows
- **featureflag-migration**: Migrate legacy feature flag systems to OpenFeature with inventory, migration, verification, cleanup, and scaffolding agents

## Repository structure

- `.cursor-plugin/marketplace.json`: marketplace manifest and plugin registry
- `plugins/<plugin-name>/.cursor-plugin/plugin.json`: per-plugin metadata
- `plugins/<plugin-name>/rules`: rule files (`.mdc`)
- `plugins/<plugin-name>/skills`: skill folders with `SKILL.md`
- `plugins/<plugin-name>/agents`: subagent definitions
- `plugins/<plugin-name>/mcp.json`: MCP server configuration for each plugin

## Validate changes

Run:

```bash
node scripts/validate-template.mjs
```

This checks marketplace paths, plugin manifests, and required frontmatter in rule/skill/agent/command files.

## Submission checklist

- Each plugin has a valid `.cursor-plugin/plugin.json`
- Plugin names are unique, lowercase, and kebab-case
- `.cursor-plugin/marketplace.json` entries map to real plugin folders
- Required frontmatter metadata exists in plugin content files
- Logo paths resolve correctly from each plugin manifest
- `node scripts/validate-template.mjs` passes
