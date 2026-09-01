#!/usr/bin/env python3
"""PreToolUse hook: no edit to tracked project files without a GitHub issue.

Every change in this repo traces to an issue. This enforces that mechanically
instead of relying on remembering it.

/start-issue records the active issue(s) in .claude/.current-issue; until it
does, Edit and Write on tracked files are denied. It also refuses any edit made
on the default branch, and refuses a record written for a different branch.

Run with --session-start to instead print the active issue as session context.

Deliberately NOT gated:
  * paths outside the repo (scratchpad, ~/.claude/plans)
  * .claude/** -- otherwise this config could never be set up or repaired

Known gap: this covers Edit/Write, not shell redirection through Bash. Gating
all of Bash would cost far more than the loophole is worth.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _hooklib import (  # noqa: E402
    git_branch,
    project_dir,
    read_payload,
    relative_to_project,
    target_path,
)

RECORD_NAME = os.path.join(".claude", ".current-issue")
# The repo's default branch -- edits made directly on it are refused.
MAIN_BRANCH = "main"
EXEMPT_PREFIXES = (".claude/",)


def record_path():
    return os.path.join(project_dir(), RECORD_NAME)


def load_record():
    try:
        with open(record_path(), "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or not record.get("issues"):
        return None
    return record


def issue_list(record):
    return ", ".join("#{}".format(n) for n in record.get("issues", []))


def deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


def session_start():
    record = load_record()
    if not record:
        context = (
            "No GitHub issue is on record for this repo. Every change here must "
            "trace to an issue: run /start-issue <number> before editing any "
            "tracked file. Edits are blocked until then."
        )
    else:
        context = (
            "Active issue(s): {issues} on branch `{branch}` (recorded {when}). "
            "Keep the work scoped to these issues; run /start-issue again to "
            "change them.".format(
                issues=issue_list(record),
                branch=record.get("branch", "?"),
                when=record.get("recorded", "?"),
            )
        )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


def main():
    if "--session-start" in sys.argv:
        return session_start()

    abs_path = target_path(read_payload())
    if not abs_path:
        return 0

    rel = relative_to_project(abs_path)
    if rel is None or rel.startswith(EXEMPT_PREFIXES):
        return 0

    record = load_record()
    if not record:
        return deny(
            "No GitHub issue on record, so `{}` cannot be edited. Every change "
            "in this repo must trace to an issue. Run `/start-issue <number>` "
            "first, or `/new-issue <description>` to file one if none covers "
            "this work.".format(rel)
        )

    branch = git_branch()
    if branch == MAIN_BRANCH:
        return deny(
            "Refusing to edit `{}` on `{}`. Work happens on a "
            "`<type>/<description>` branch -- run `/start-issue <number>` to "
            "create one.".format(rel, MAIN_BRANCH)
        )

    recorded_branch = record.get("branch")
    if branch and recorded_branch and branch != recorded_branch:
        return deny(
            "The issue record is stale: {issues} was recorded for branch "
            "`{recorded}`, but HEAD is `{actual}`. Run `/start-issue <number>` "
            "to record the issue(s) for this branch.".format(
                issues=issue_list(record),
                recorded=recorded_branch,
                actual=branch,
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
