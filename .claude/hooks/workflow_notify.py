#!/usr/bin/env python3
"""SessionStart hook: say when this adopted repo has fallen behind the
claude-toolkit store, or when the local store clone itself looks stale.

Notify only -- it never runs `wf sync`. All the reconcile logic lives in `wf`;
this hook just runs `wf status --porcelain` and formats the result. If `wf`
is not on PATH on this machine, or anything goes wrong, it stays silent and
never blocks the session.

What it can and cannot know: `wf status` does not hit the network, so the hook
distinguishes "this repo is behind the local store clone" (definite) from
"the store clone hasn't fetched in a while, so `wf sync` may pull new commits"
(a fetch-age heuristic). It never claims the store "has moved ahead" -- that
needs a fetch, and a `git fetch` in a SessionStart hook risks hanging.
"""

import json
import os
import shutil
import subprocess
import sys

STALE_FETCH_DAYS = 7


def project_dir():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return os.path.abspath(env) if env else os.path.abspath(os.getcwd())


def emit(context):
    json.dump(
        {"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }},
        sys.stdout,
    )
    sys.stdout.write("\n")


def main():
    project = project_dir()
    wf = shutil.which("wf")
    if not wf:
        return 0
    try:
        out = subprocess.run(
            [wf, "status", "--porcelain", project],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return 0

    line = next((ln for ln in out.splitlines() if ln.strip()), "")
    parts = line.split("\t")
    if len(parts) != 5:
        return 0
    _path, name, state, attention, fetched_days = parts

    behind = state.startswith("behind") or attention not in ("0", "")
    try:
        stale = fetched_days == "-" or int(fetched_days) >= STALE_FETCH_DAYS
    except ValueError:
        stale = False

    if not behind and not stale:
        return 0

    bits = []
    if behind:
        detail = "core file(s) need attention" if state.startswith("current") \
            else state.replace("behind:", "behind ")
        bits.append(
            "This repo is behind the local claude-toolkit store ({}: {}). "
            "Run `wf sync .` to reconcile -- it is not automatic. "
            "`wf status .` shows detail and any pending MIGRATIONS.md steps; "
            "`wf diff .` shows core files edited in this repo.".format(name, detail)
        )
    if stale:
        age = "never" if fetched_days == "-" else "{} day(s) ago".format(fetched_days)
        bits.append(
            "The claude-toolkit store clone was last fetched {}; `wf sync` "
            "pulls before it reconciles, so run it to pick up store changes."
            .format(age)
        )
    emit(" ".join(bits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
