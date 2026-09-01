"""Shared helpers for this workflow's .claude hooks.

Small, dependency-free utilities the hooks need: locating the repo root,
reading the current branch, parsing a hook payload, and resolving the file a
Write/Edit acts on. Nothing here shells out to a language toolchain.
"""

import os
import subprocess
import sys

# Nothing here may hang the session waiting on a subprocess.
GIT_TIMEOUT_SECONDS = 15


def project_dir():
    """Absolute path to the repo root."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return os.path.abspath(env)
    # .claude/hooks/_hooklib.py -> repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


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


def read_payload():
    """Parse the hook payload from stdin. Returns {} when absent or malformed."""
    import json

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
