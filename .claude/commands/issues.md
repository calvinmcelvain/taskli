---
description: Browse open GitHub issues for this repo
argument-hint: [search terms | label:refactor | assignee:@me]
---

List the open issues so we can pick what to work on. Filter: **$ARGUMENTS** (all
open issues when empty).

```bash
gh issue list --state open --limit 40 --json number,title,labels,assignees \
  --template '{{range .}}{{printf "%-5v" .number}} {{printf "%-10v" (index .labels 0).name}} {{.title}}{{"\n"}}{{end}}'
```

`GH_REPO` is set in `.claude/settings.json`, so `gh` resolves the repo without `-R`.

Pass `$ARGUMENTS` through as appropriate:
- bare words → `--search "<words>"`
- `label:x` → `--label x`
- `assignee:@me` → `--assignee @me`

## Presenting the results

If issue titles carry a Conventional-Commit prefix (`feat:`, `fix:`, `refactor:`,
`docs:`, `test:`), group by it. Lead with the count, then a compact table of
number / type / title. Do not dump raw JSON.

To show one issue in full: `gh issue view <n>`.

## After picking

Hand off to `/start-issue <number> [more...]` — that is what records the issue and
cuts the branch. No tracked file can be edited until it runs.

If `gh` reports it is not on PATH, the session's environment predates the install —
restart Claude Code. If it reports no authentication, run `gh auth login`.
