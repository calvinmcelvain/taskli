---
description: Run the local check sweep (format, lint, tests/build, review)
---

This is the **only** place formatting, linting, and tests run. There is no
write-time hook — nothing has been checked until this runs, so it is the final
step of every plan.

## 1. Apply formatting

Formatting has one correct answer, so fix it rather than report it. Run it
first: a formatter run in `--check` mode later in the sweep would fail on a file
this step would have fixed.

```bash
black --line-length 79 . && isort .
```

It edits in place. Mention it in passing if it changed files; do not paste diffs.

## 2. Run lint + tests

```bash
ruff check .
mypy src tests
pytest -q --cov=taskli --cov-report=term-missing --cov-fail-under=95
```

Run a slow suite in the background — use `run_in_background: true` on the `Bash`
call, wait for its completion notification (don't poll with `sleep`), then read
the output. A fast one can run in the foreground.

Any non-zero exit is a failure — report the failing section and fix it, then
re-run this command from step 1.

Once everything passes, stamp it so `/pr` can confirm freshness later:

```bash
find src tests -type f -name "*.py" -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d" " -f1 > .claude/.last-check
```

## 3. Review pass

Only once step 2 has passed — reviewing code that doesn't build or lint cleanly
yet isn't useful. Check whether the branch actually touches source:

```bash
git diff origin/main...HEAD -- src tests
git status --porcelain -- src tests
```

If both are empty, skip this step with a one-line note — a docs/config-only
change has nothing for a code reviewer to look at.

If either is non-empty, dispatch the `reviewer` agent (`.claude/agents/reviewer.md`)
via the `Agent` tool — it runs in the background; wait for its completion
notification rather than blocking the turn or polling. It gives a read-only pass
over the diff for structure, isolation, efficiency, and long-term validity.
Present its findings to the user directly as part of the `/check` output.

**Findings are not optional follow-up.** If the reviewer reports nothing
significant, `/check` has passed — proceed to `/pr`. If it reports findings,
`/check` has *not* passed: re-enter plan mode (`EnterPlanMode`) to plan the
fixes (the small-change exemption in `/start-issue` still applies if a finding is
genuinely single-file), implement them — `implementer` agent for anything beyond
a trivial fix — then run `/check` from step 1 again. Repeat plan → implement →
`/check` until a review pass reports nothing significant. That is the only way
`/check` succeeds once source changed; `/pr` does not verify this itself, so
running it before the loop finishes clean ships unverified code.
