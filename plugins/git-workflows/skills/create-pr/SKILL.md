---
name: create-pr
description: Create a PR with formatted description and auto-open it. Use when ready to open a pull request.
---

# Open a PR

- Check that I'm in a branch other than `main` or `prod`. If not, create a new git branch and switch to it.
- Check the diff between my branch and the main branch of the repo
- If there's unstaged or staged work that hasn't been commited, commit all the relevant code first
(Use `gh` in case it's installed)
- Find Jira issue keys matching `[A-Z][A-Z0-9]+-\d+` in the branch name, commits included in the PR, and proposed title. Deduplicate them while preserving their first-detected order.
- If no Jira issue key is found, ask me for one before creating the PR.
- Resolve the canonical URL for every detected Jira issue using the available Jira integration. If any URL cannot be resolved, ask me for it before creating the PR.
- Write the title and PR body in concise, plain English. Avoid unusual, vague, or overly technical wording.
- Use the first detected Jira issue key at the very start of the title. Keep the title to 80 characters or fewer:

`[JIRA-123] <feature_area>: <Short plain-English title>`

- Write the PR body in this format. Do not add a checklist:

<TLDR in no more than 2 sentences>

## Tasks
- [JIRA-123](<canonical Jira URL>)

<Description>
- 1~3 bullet points explaining what's changing

- In case there is a PR template, respect it while including the concise summary and linked `Tasks` section. Do not add checklist items.
- Always include the PR link in your response as a clickable markdown link, e.g. `[PR #123: Title](https://github.com/...)`
- Prepend GIT_EDITOR=true to all git commands you run, so you can avoid getting blocked as you execute commands

- At the end, use the `open` command to open the PR automatically for me
