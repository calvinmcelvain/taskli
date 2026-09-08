"""Shared helpers for this workflow's .claude hooks.

Small, dependency-free utilities the hooks need: locating the repo root,
reading the current and default branch, loading the project's local config
(.claude/project.json), parsing a hook payload, and resolving the file a
Write/Edit acts on. Nothing here shells out to a language toolchain.
"""

import json
import os
import subprocess
import sys

# Nothing here may hang the session waiting on a subprocess.
GIT_TIMEOUT_SECONDS = 15


def project_dir():
    """Absolute path to the repo root.

    Always prefer $CLAUDE_PROJECT_DIR: `.claude/hooks/` is a symlink into the
    shared store, so a __file__-relative walk would land in the store, not the
    consuming repo. The cwd fallback (hooks run from the repo root) is only for
    a stray direct invocation with the env unset.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.getcwd())


def git(*args):
    """Run a git command in the repo, returning stdout or '' on failure."""
    try:
        done = subprocess.run(
            ("git",) + args,
            cwd=project_dir(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def git_branch():
    """Current branch name, or None if git is unavailable / detached HEAD."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    return branch or None


def default_branch():
    """The repo's default branch, derived from the remote HEAD. Falls back to 'main'.

    Never stored per-project -- every hook and command resolves it at runtime so
    a core file needs no branch placeholder.
    """
    ref = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    if ref:
        return ref.split("/", 1)[-1]
    return "main"


def base_ref():
    """`origin/<default branch>` -- the ref a branch diff / status range is taken against."""
    return "origin/{}".format(default_branch())


def load_project_config():
    """Parse .claude/project.json into a dict. Returns {} when absent or malformed.

    This is the single per-project config file -- source globs, the
    format/lint/test commands, and any workflow-specific knobs. A hook must
    never raise on a missing or broken config; it degrades instead.
    """
    path = os.path.join(project_dir(), ".claude", "project.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def read_payload():
    """Parse the hook payload from stdin. Returns {} when absent or malformed."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def target_path(payload):
    """The file a Write/Edit payload acts on, as an absolute path, or None."""
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response") or {}
    path = tool_input.get("file_path") or response.get("filePath")
    if not path:
        return None
    return os.path.abspath(path)


def relative_to_project(abs_path):
    """Project-relative POSIX path, or None if `abs_path` is outside the repo."""
    root = project_dir()
    try:
        rel = os.path.relpath(abs_path, root)
    except ValueError:  # different drive on Windows
        return None
    if rel.startswith(".."):
        return None
    return rel.replace("\\", "/")
