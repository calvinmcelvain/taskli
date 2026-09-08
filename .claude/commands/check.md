---
description: Run the local check sweep (format, lint, tests/build, review)
---

This is the **only** place formatting, linting, and tests run. There is no
write-time hook -- nothing has been checked until this runs, so it is the final
step of every plan.

The commands are not hardcoded here -- they live in `.claude/project.json`
(`format_cmd`, `lint_cmd`, `test_cmd`, and `find_expr`, a command that emits the
source files NUL-separated). Read each one with:

```bash
cfg() { python3 -c "import json,sys;print(json.load(open('.claude/project.json')).get(sys.argv[1],''))" "$1"; }
```

A blank value means "skip that step".

## 1. Apply formatting

```bash
FMT=$(cfg format_cmd); [ -n "$FMT" ] && eval "$FMT"
```

Skip with a one-line note when `format_cmd` is blank. Otherwise it edits in
place -- run it first (a `--check`-mode formatter later in the sweep would fail
on a file this fixes). Mention it in passing if it changed files; do not paste
diffs.

## 2. Run lint + tests

```bash
LINT=$(cfg lint_cmd); [ -n "$LINT" ] && eval "$LINT"
TEST=$(cfg test_cmd); [ -n "$TEST" ] && eval "$TEST"
```

Run a slow suite in the background -- `run_in_background: true` on the `Bash`
call, wait for its completion notification (don't poll with `sleep`), then read
the output. A fast one can run in the foreground.

Any non-zero exit is a failure -- report the failing section and fix it, then
re-run this command from step 1.

Once everything passes, stamp the freshness hash so `/pr` can confirm it later.
`/pr` recomputes this exact line -- keep them identical:

```bash
FIND=$(cfg find_expr)
eval "$FIND" | sort -z | xargs -0 sha256sum | sha256sum | cut -d" " -f1 > .claude/.last-check
```

## 3. Review pass

Only once step 2 has passed -- reviewing code that doesn't build or lint cleanly
yet isn't useful. Check whether the branch actually touches source:

```bash
BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || echo main)
FILES=$(eval "$(cfg find_expr)" | tr '\0' '\n')
git diff "origin/$BASE...HEAD" -- $FILES
git status --porcelain -- $FILES
```

If both are empty, skip this step with a one-line note -- a docs/config-only
change has nothing for a code reviewer to look at.

If either is non-empty, dispatch the `reviewer` agent (`.claude/agents/reviewer.md`)
via the `Agent` tool -- it runs in the background; wait for its completion
notification rather than blocking the turn or polling. It gives a read-only pass
over the diff for structure, isolation, efficiency, and long-term validity.
Present its findings to the user directly as part of the `/check` output.

**Findings are not optional follow-up.** If the reviewer reports nothing
significant, `/check` has passed -- proceed to `/pr`. If it reports findings,
`/check` has *not* passed: re-enter plan mode (`EnterPlanMode`) to plan the
fixes (the small-change exemption in `/start-issue` still applies if a finding is
genuinely single-file), implement them -- `implementer` agent for anything beyond
a trivial fix -- then run `/check` from step 1 again. Repeat plan -> implement ->
`/check` until a review pass reports nothing significant. That is the only way
`/check` succeeds once source changed; `/pr` does not verify this itself, so
running it before the loop finishes clean ships unverified code.
