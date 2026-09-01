#!/usr/bin/env python3
"""Stop hook: flag workflow changes that .claude/CLAUDE.md may no longer describe.

CLAUDE.md makes concrete, checkable claims -- which hooks are wired, which
commands exist, how checks are enforced. Every one of those claims has a file
behind it, so when that file changes and CLAUDE.md does not, the documentation
is a candidate for being wrong.

A hook cannot judge whether an update is actually *needed* -- that takes reading
both sides. So this only supplies the signal: which watched files changed, and
whether CLAUDE.md changed with them. The model decides.

Runs on Stop rather than PostToolUse deliberately: it is pure git, no toolchain,
and fires once per turn rather than once per write.

Fires at most once per distinct drift set, and not at all once CLAUDE.md has
been edited since the last prompt -- so answering it, either by updating the
file or by deciding no update is warranted, does not loop on the next stop.

CLAUDE.md is hashed directly rather than looked for in git output. A global
gitignore can exclude it, and an ignored file never appears in `git status` or a
branch diff, which would leave the prompt unanswerable by editing the file.

If .claude/CLAUDE.md does not exist, this hook does nothing -- there is no doc to
keep honest. Run /init to create one, or leave it; the workflow works without.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _hooklib import git, project_dir  # noqa: E402

ACK_NAME = os.path.join(".claude", ".doc-drift-ack")
# Literal forward-slash string, not os.path.join: changed_files() below builds its paths
# from `git diff`/`git status`, which always emit forward slashes even on Windows, and
# `DOC in paths` (see main()) needs to match that exactly.
DOC = ".claude/CLAUDE.md"

# The repo's default branch -- the base for the "what changed on this branch" diff.
BASE_BRANCH = "main"

# Each entry backs a claim CLAUDE.md typically makes about this workflow. The
# trailing project-specific paths (build config, CI workflow files) catch drift
# in the toolchain the /check sweep mirrors.
WATCHED = (
    ".claude/settings.json",   # which hooks are wired, what is denied/allowed
    ".claude/commands/",       # the command list
    ".claude/hooks/",          # hook behaviour
    ".claude/agents/",         # the subagents
    ".claude/ARCHITECTURE.md",  # the architecture rules
    "pyproject.toml",          # toolchain: lint / format / type / coverage config
    ".github/workflows/",      # CI commands the /check sweep mirrors
)


def changed_files():
    """Every path this branch touches: committed since the base, plus uncommitted."""
    paths = set()
    for line in git("diff", "--name-only", "origin/{}...HEAD".format(BASE_BRANCH)).splitlines():
        paths.add(line.strip())
    # --porcelain columns are fixed-width; the path starts at column 3.
    for line in git("status", "--porcelain").splitlines():
        entry = line[3:].strip()
        if entry:
            paths.add(entry.split(" -> ")[-1])
    return {p for p in paths if p}


def ack_path():
    return os.path.join(project_dir(), ACK_NAME)


def doc_hash():
    """Content hash of CLAUDE.md, or '' when it is absent."""
    try:
        with open(os.path.join(project_dir(), DOC), "rb") as handle:
            return hashlib.sha1(handle.read()).hexdigest()
    except OSError:
        return ""


def read_ack():
    """(drift digest, CLAUDE.md hash) recorded the last time this fired."""
    try:
        with open(ack_path(), "r", encoding="utf-8") as handle:
            parts = handle.read().split()
    except OSError:
        return "", ""
    parts += ["", ""]
    return parts[0], parts[1]


def write_ack(digest, doc):
    try:
        with open(ack_path(), "w", encoding="utf-8") as handle:
            handle.write("{} {}\n".format(digest, doc))
    except OSError:
        pass  # an unwritable ack file must not break the session.


def main():
    # No CLAUDE.md -> nothing to keep honest.
    if not os.path.exists(os.path.join(project_dir(), DOC)):
        return 0

    paths = changed_files()
    if not paths or DOC in paths:
        return 0

    drifted = sorted(p for p in paths if p.startswith(WATCHED))
    if not drifted:
        return 0

    digest = hashlib.sha1("\n".join(drifted).encode("utf-8")).hexdigest()
    current_doc = doc_hash()
    acked_digest, acked_doc = read_ack()

    # Either this exact set was already raised, or CLAUDE.md has been edited
    # since it was raised. Both mean the question has been answered.
    answered = acked_digest == digest or (acked_doc and current_doc != acked_doc)
    write_ack(digest, current_doc)
    if answered:
        return 0

    listing = "\n".join("  - {}".format(p) for p in drifted)
    json.dump(
        {
            "decision": "block",
            "reason": (
                "These files define workflow that .claude/CLAUDE.md documents, "
                "and they changed on this branch while CLAUDE.md did not:\n\n{}\n\n"
                "Read CLAUDE.md and confirm it still describes the repo "
                "accurately -- the hooks it says are wired, the commands it "
                "lists, how checks are enforced. Update it if any claim is now "
                "wrong. If everything still holds, say so in one line and stop; "
                "this will not ask again for the same set of changes.".format(listing)
            ),
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
