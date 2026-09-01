---
description: Prepare a PR body and hand the push/create commands back to the user
---

**This command never touches the remote.** `git push` and `git commit` are denied
in `.claude/settings.json` — publishing is the user's call, always.

## Steps

1. **Require an issue.** Read `.claude/.current-issue`. If it is missing, stop and
   tell the user to run `/start-issue <number>` — a PR without a linked issue is not
   allowed here.

2. **Confirm `/check` is current.** Recompute the same hash `/check` stamps — use
   the identical find globs from `/check` step 2:

   ```bash
   find src tests -type f -name "*.py" -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d" " -f1
   ```

   Compare it to `.claude/.last-check` (gitignored, written by `/check`). If the file
   is missing, or the hash differs, stop — tell the user source has changed since
   `/check` last passed (or `/check` has never run here) and to run it before `/pr`.

3. **Verify the branch.** Confirm `git rev-parse --abbrev-ref HEAD` matches the
   recorded branch, and that it is not the default branch.

4. **Show what would ship.** `git status --short` and `git diff --stat origin/main...HEAD`.

   Read these together: the diffstat shows only *committed* work, so uncommitted
   changes are invisible in it. If `git status` is not clean, say so loudly —
   pushing at that point ships the previous commit and silently omits the session's
   work. Name any file that should **not** go in (unrelated untracked files, scratch
   files) so it is left out of the `git add`.

5. **Draft the title** as `type: Sentence-case description`, where `type` matches the
   branch prefix (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`). A scope is
   optional, e.g. `fix(build):`.

6. **Write the body** to `.claude/.pr-body.md` (gitignored). If the repo has
   `.github/PULL_REQUEST_TEMPLATE.md`, follow it exactly. Otherwise use:

   ```
   ## Summary
   <one or two plain sentences on what changed>

   ## Related Issues
   Closes #<n>   (one line per recorded issue number)

   ## Changes Made
   - <one bullet per meaningfully distinct change>
   ```

   **Keep it short.** A reviewer should read the whole thing in a few seconds.
   - **Summary**: one or two plain sentences on *what changed*. No "This PR aims
     to...", no restating the issue, no narrating how the approach was chosen.
   - **Changes Made**: one bullet per meaningfully distinct change, not one per file
     and not a paragraph per bullet. Skip anything the diff already makes obvious.

7. **Print the handoff** and stop:

   ```
   ! git add <the files from step 4>
   ! git commit -m "<type>: <Sentence-case description>"
   ! git push -u origin <branch>
   ! gh pr create --title "<title>" --body-file .claude/.pr-body.md
   ```

   Include the `add`/`commit` lines whenever step 4 showed uncommitted work. Draft a
   real commit message; do not leave a placeholder. Tell the user to run these with
   the `!` prefix so they execute in their session.

   `git commit` and `git push` are denied to you, so these are the user's to run —
   which is the point. They are also the last human review before anything leaves the
   machine.

   If this session is in a worktree (`.claude/worktrees/<branch>`), add a reminder:
   once merged, say "keep" or "remove" and `ExitWorktree` will clean it up — it is
   never called proactively.
