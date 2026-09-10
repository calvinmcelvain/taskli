# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`taskli` is a single-package Python CLI for tracking nested task lists, installed
as `tk` / `taskli` (both entry points → `taskli.cli:main`). Each list is one
JSON file under `$TASKLI_PATH` (`~/.taskli` by default); list names are dotted
(`work.meetings` is the file `work.meetings.json`), capped at two sublist levels.
Items form a recursive tree addressed by dotted positional paths (`1`, `1.2`,
`1.2.1`) at unlimited depth. Output is `rich` tables and trees. Deps: `rich`,
`pydantic` v2, `argcomplete`.

## Commands

Setup (all check commands below assume this `.venv` exists — see
`.claude/project.json`, which prefixes them with `.venv/bin/`):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

| Task | Command |
|---|---|
| Tests | `pytest -q` |
| One file / class / test | `pytest tests/unit/test_cli.py::TestAdd::test_creates_list_if_missing` |
| Lint | `ruff check .` |
| Type-check | `mypy src tests` |
| Format (in place) | `black --line-length 79 . && isort .` |

CI (`.github/workflows/ci.yml`, Python 3.12) runs ruff, `black --check`
+ `isort --check-only`, `mypy src tests`, and `pytest` with a **95% coverage
gate** (`--cov-fail-under=95`); a `build` job also smoke-tests the wheel. Line
length is 79 everywhere.

## Architecture

Strict one-way dependency chain — the checkable rules live in
`.claude/ARCHITECTURE.md`; `architecture-checker` enforces them against every
plan. The shape:

```
cli → logic → {render, storage} → models/ → exceptions
                                   (leaves: exceptions, hierarchy, migrations, env)
```

- **`cli.py`** — argparse routing only. Every action is a flag (no bare-word
  subcommands), grouped into list-management / item-action / config / default-view;
  `_resolve_op` picks exactly one op per call. The per-attribute **argparse
  vocabulary** (flags, `nargs`, `dest`) lives in the `MODIFIER_FLAGS` table here —
  the one sanctioned `cli.py` module constant, because the registry can't carry
  argparse objects. `_dispatch` is wrapped in `_handle_errors` (renders any
  `TaskliError` as exit 1). `logic`, `render`, and `storage.load_config` are
  function-local imports (at module scope `cli.py` imports only `env` and the
  pydantic-free `models` leaves), so the tab-completion path (`import
  taskli.cli`) never loads pydantic or rich; `_complete_list_names` enumerates
  list names via `env.scan_list_names`.
- **`logic.py`** — one public function per command. Loads via `storage`, mutates
  via `TaskliList` methods, saves, returns a `CommandResult` (messages / warnings
  / exit_code / optional view) or plain data. Imports no `render`, prints nothing.
- **`render.py`** — all `rich`. Every styled span is a `rich.text.Text`
  (`.append` / `Text.assemble`), never bracket-tag markup. `cli.py` calls
  `render_*` and never constructs `rich` objects or `print()`s.
- **`storage.py`** — all list- and config-file content I/O. One JSON file per
  list; enforces the "sibling order = id order" invariant on save
  (`sort_by_index`) and load (`reindex`). `load_*` raises `Outdated*FileError`
  on an old schema rather than self-healing — only `tk --migrate` rewrites
  files. The list-creation functions take a `config` keyword; when passed, a new
  sublist with no explicit `--color` inherits the nearest existing ancestor
  list's color at creation, gated on `Config.inherit_sublist_color` (default
  `True`). Delegates the storage-dir path and the list-name scan to the `env`
  leaf (`resolve_storage_dir`, `scan_list_names`).
- **`models/`** — pydantic models + enums + pure value objects, no I/O / `rich` /
  `argparse`. `TaskliItem` is a recursive tree (`children: list[TaskliItem]`,
  `id` a dotted string). `TaskliList` owns **all** item-mutation logic as methods.
  `registry.py`'s `ATTRIBUTES` table drives filter operators, sort keys, render
  columns, and value parsing off one per-attribute entry — adding a
  filterable/sortable/settable attribute is a two-table edit (`registry.py` entry
  + `cli.MODIFIER_FLAGS` entry, kept honest by `TestModifierRegistryParity`).
  `models/__init__.py` is empty — consumers deep-import from the leaf modules
  (`from .models.tasks import TaskliList`), though the `registry` module stays
  `from .models import registry`.
- **`migrations.py`** — versioned schema migrations on raw parsed dicts before
  model validation, stdlib-only, historical label strings hard-coded (frozen
  contract). Extend the existing unreleased migration step rather than bumping
  `CURRENT_*_VERSION` when no real data is on the current version.
- **`env.py`** — stdlib-only leaf (`os` + `pathlib`): `resolve_storage_dir`,
  `scan_list_names`, and `CONFIG_FILE_NAME`. Exists so `cli.py`'s parser /
  tab-completion path can resolve the storage dir and list names without
  importing `storage.py` (and therefore pydantic); `storage.py` delegates
  `config_file_path` / `list_all_lists` to it.

## Conventions

- Python style: numpy-style docstrings, static typing, black at 79, strict
  naming — the `python-style` skill is authoritative (`python-tests` for
  `test_*.py`). `cli.py` specifically: no docstrings, no new module constants
  beyond `MODIFIER_FLAGS`, truthy checks over `is not None`, plain values over
  new dataclasses.
- Tests: `tests/unit/` mirrors `src/taskli/`, one `Test<Feature>` class per
  behavior area. Use the `taskli_env` fixture (points `TASKLI_PATH` at `tmp_path`)
  for anything touching storage. CLI tests call `taskli.cli.main(argv)` directly
  and assert on return code + `capsys`. JSON fixtures live in `tests/resources/`,
  loaded via `tests/utils.py`.
- `completions/` holds the **verbatim** `register-python-argcomplete` output
  (`taskli.sh` for bash/zsh, `taskli.ps1` for PowerShell) — not hand-edited.
  Provenance, the regeneration commands, and the generated-with `argcomplete`
  version live in `completions/README.md`; `tests/test_completions.py` guards
  the committed files against a fresh generation (version-gated on
  `EXPECTED_ARGCOMPLETE`). `pyproject.toml` ships the dir in the sdist and maps
  it into the wheel at `<prefix>/share/taskli/completions/`.

## Workflow

This repo runs the `issue-gated` workflow (`.claude/WORKFLOW.md`): every change
traces to a GitHub issue, goes through plan mode with a `### Task N` breakdown,
is built by `implementer` agents, and passes `/check` (format, lint, tests,
`reviewer`) before `/pr`. Claude never commits or pushes. Commit messages and
PR descriptions carry **no Claude attribution** — no `Co-Authored-By: Claude`,
no `Claude-Session:` trailer, no "Generated with Claude Code" footer, no
`claude.ai/code` link. Draft them as the user would. Local config — the
check commands, source glob, `GH_REPO` (`calvinmcelvain/taskli`), architecture
rules, and `doc_drift` watch paths — lives in `.claude/project.json`,
`.claude/settings.local.json`, and `.claude/ARCHITECTURE.md`.
