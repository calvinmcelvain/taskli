# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-05
<!-- set the real release date when merging -->

1.0 begins the [stability promise](docs/stability.md): the CLI flag grammar and
the on-disk schema stay compatible across 1.x.

### Added

- First release on PyPI as `taskli-cli`: `uv tool install taskli-cli` or
  `pipx install taskli-cli`. The `tk` and `taskli` commands are unchanged.
- Nested subtasks at any depth, addressed by dotted ids (`1.2.1`) and created
  with `--under`. `-e --under` re-nests an existing item; `--under ""` moves it
  back to the top level.
- Due dates: `today`, `tomorrow`, `next-week`, `N days`, `N weeks`, weekday
  names, and `MM-DD-YYYY`. Filter with `--today`, a repeatable `--due` (OR),
  and `--due none` / `--undated`.
- `tk --agenda`: one cross-list timeline with a Priority column, a
  configurable window (`agenda_window`), and `agenda_include_overdue`.
- A due/overdue reminder banner above commands, controlled by
  `show_reminders`.
- `-D` / `--details` shows one task in full: description, timestamps, subtasks.
- Task descriptions (`--desc`), flagged with a `¶` in tables.
- `-d`, `-i`, `-u`, and `-rm` can be combined in one call.
- Sublists inherit their parent list's color (`inherit_sublist_color`).
- `silent_prune` config option to print only the `--prune` summary.
- Schema versioning for list and config files, and `tk --migrate` to upgrade
  them.
- Checked-in shell completion scripts for bash, zsh, and PowerShell, and faster
  tab completion.

### Changed

- **Breaking vs 0.3.0-beta:** list and config files written by 0.3.0-beta must
  be upgraded once with `tk --migrate`. taskli errors and points to it rather
  than rewriting files itself.
- Requires Python 3.12 or newer.
- Item tables fold the ID, state, and text columns into a single `Task` column.
- `uv tool install` is now the recommended install path.

## [0.3.0-beta] - 2026-08-12

### Added

- Move and copy items between lists.
- Several modifiers in one command, and per-item tags and priority when adding
  multiple items.
- A `modified_at` timestamp on items.
- `tk --version` and `tk --path`.
- The default list is shown in bold in `--lists`.

### Changed

- **Breaking:** the command-line grammar was rewritten so every action is a
  flag.
- Item ids follow the list's sort order.

## [0.2.0-beta] - 2026-08-03

### Added

- A user config file, managed with `--config`.
- A test suite with coverage reporting.

### Changed

- Subparsers were replaced with plain arguments.
- Models were renamed to `Taskli*`, and `todo` became `task`.

## [0.1.0-beta] - 2026-07-31

### Added

- Initial release.

[Unreleased]: https://github.com/calvinmcelvain/taskli/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/calvinmcelvain/taskli/compare/v0.3.0-beta...v1.0.0
[0.3.0-beta]: https://github.com/calvinmcelvain/taskli/compare/v0.2.0-beta...v0.3.0-beta
[0.2.0-beta]: https://github.com/calvinmcelvain/taskli/compare/v0.1.0-beta...v0.2.0-beta
[0.1.0-beta]: https://github.com/calvinmcelvain/taskli/releases/tag/v0.1.0-beta
