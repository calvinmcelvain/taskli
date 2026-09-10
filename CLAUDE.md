# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup (editable install with dev deps):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the CLI once installed: `tk ...` or `taskli ...` (both entry points defined in `pyproject.toml`, pointing at `taskli.cli:main`).

Test:
```bash
pytest -q                                            # full suite
pytest tests/unit/test_cli.py                        # one file
pytest tests/unit/test_cli.py::TestAdd                # one class
pytest tests/unit/test_cli.py::TestAdd::test_creates_list_if_missing  # one test
```

Lint / format / type-check (all run in CI, `.github/workflows/ci.yml`, matched against Python 3.12):
```bash
ruff check .
black --check --line-length 79 .
isort --check-only .
mypy src tests
```
Drop `--check`/`--check-only` from `black`/`isort` to auto-fix.

## Architecture

Single package, `src/taskli/`, with a strict dependency direction
(`exceptions` → `models` → `{storage, render}` → `logic` → `cli`; nothing
later is imported by something earlier — and `logic` imports `storage`
but never `render`). `cli` imports `resolve_storage_dir` / `scan_list_names`
from the `env` leaf at module scope, and takes `logic` / `render` /
`storage.load_config` as function-local imports so the tab-completion path
(`import taskli.cli`) skips pydantic and rich.
`hierarchy` is a second leaf beside `exceptions` — a pure-string module
any layer may import — and `migrations` a third (stdlib-only, operating
on raw parsed file dicts before model validation; imported by `storage`).
`env` is a fourth (`os` + `pathlib` only — `resolve_storage_dir` /
`scan_list_names` / `CONFIG_FILE_NAME`; the one leaf that touches the
filesystem, imported by `storage`, `logic`, and `cli`).
`models` is itself a small sub-package rather than one file (with
`attributes.py`, `dates.py`, and `paths.py` the leaves inside it and
`registry.py` layered on `attributes.py` + `dates.py`) — see below.
`models/__init__.py` is empty: every symbol is imported from its owning
leaf module directly (`from .models.tasks import TaskliItem`), though the
`registry` module stays `from .models import registry`.

- **`models/`** package (`attributes.py` for `Priority`/`Color`/`Status`
  plus the `Operator` enum (`EQ`/`CONTAINS`/`LT`/`GTE`) and its `compare()`,
  `dates.py` for the due-date value parser, `paths.py` for the dotted
  item-path sort key, `config.py` for
  `Config`/`SortBy` (whose `inherit_sublist_color: bool = True` field,
  alongside `auto_prune` / `show_reminders` / `agenda_window`, is additive
  with a Python default so it needs no migration — `storage` reads it when
  creating a sublist), `tasks.py` for `TaskliItem`/`TaskliList`, `query.py`
  for the `Filter`/`Criterion`/`Sort` value objects, `registry.py` for the
  per-attribute `Attribute` dataclass + `ATTRIBUTES` table) — Pydantic
  models and enums, plus the plain frozen dataclasses in `query.py` and
  `registry.py`. The `Operator.LT`/`Operator.GTE` `compare()` branches are
  generic (not date-named) and short-circuit to `False` when either side
  is `None`; `GTE` (`value >= operand`) exists solely for
  `query.agenda_criteria`'s window lower bound and, like `LT`, carries no
  `registry.filter_operators` entry — both are built into `Criterion`s
  directly by `due_to_criteria`/`agenda_criteria`, bypassing that facet.
  `Priority._missing_` / `Status._missing_` accept only a
  case-insensitive label string now — the old container-form (`dict` with
  a `"label"` key) branch is gone, since unwrapping that shape is a
  `migrations.py` step. `dates.py` is a leaf beside `attributes.py`
  (imports only `re`, `datetime`, `..exceptions` — nothing from
  `models/`): `parse_due_date(str) -> datetime` accepts the keywords
  `today`/`tomorrow`/`next week`/`N days`/`N weeks`, a bare weekday name
  (full or 3-letter, via the module-level `WEEKDAY_INDEX` map — resolves
  to the closest upcoming occurrence, today-is-that-weekday means +7),
  and explicit
  `MM-DD-YYYY`, all normalised to midnight, and raises
  `InvalidModifierValueError` (listing the accepted forms) on anything
  else; `today() -> date` and `midnight(value) -> datetime` are the
  mockable / normalising seams. `parse_agenda_window(raw: str) -> str`
  lives in this same leaf (same shape: stdlib + `..exceptions` only) —
  it validates/normalises a `--agenda`/`agenda_window` token to
  `"today"`/`"week"`/`"overdue"` or a positive-integer digit string,
  raising `InvalidModifierValueError` otherwise; it's the one source of
  truth both `Config.agenda_window`'s validator and
  `query.agenda_criteria` call, kept in `dates.py` rather than `query.py`
  specifically so `config.py` (which only imports leaves) doesn't gain a
  new `-> query.py` edge. `paths.py` is a third leaf beside
  `attributes.py` / `dates.py` (imports nothing): `path_key(path: str) ->
  tuple[int, ...]` splits a dotted item path into its integer segments
  (`"1.10" -> (1, 10)`, so it sorts after `"1.2"`), the one shared
  sibling-ordering key. It lives here, not in `hierarchy.py`, because
  `hierarchy.py` is list-name math (`int(s)` per segment would raise on a
  real name like `work.meetings`) and `models/tasks.py` can't import
  `hierarchy` under Rule 1 — `paths.py` is imported by `tasks.py`.
  `registry.py` layers on `attributes.py` +
  `dates.py` (runtime imports `.attributes` and `.dates`): `ATTRIBUTES`
  is keyed by field name
  (`id`/`status`/`text`/`description`/`priority`/`tags`/`due_date`/`created_at`,
  plus the list `color`), insertion order = render column order, and each
  entry carries **domain + render + modifier facets** — `filter_operators`
  / `filter_default_operator`, `sort_key` / `sort_descending`,
  `column_header` / `column_justify` / `render_format` / `render_style`
  (only `priority` / `tags` / `due_date` still carry render-column
  facets — `id` / `status` / `text` / `description` lost theirs, and
  `text` its `render_style`, when the items table folded its `ID` /
  `State` / `Text` / `""` columns into one `Task` column, #104;
  `render_style` returns a rich colour *name* string, never imports
  rich), plus `parse` (the `str -> value` callable — `priority`'s
  `Priority[...]` lookup, moved here from `cli.MODIFIER_FLAGS`, and
  `due_date`'s `parse_due_date`) and `modifier_ops` (a frozenset of
  op-name strings, `"add"`/`"edit"`, marking which item actions may set
  the attribute). Module helpers `sortable()` / `renderable()` /
  `filterable()` / `modifiable(op)` select the entries carrying the
  matching facet. The sort facets feed `query.Sort` +
  `Config.default_sort` validation, the render facets feed
  `render._items_table`, the filter facets (`filter_operators` /
  `filter_default_operator`, `filterable()`) feed `cli._dispatch`'s VIEW
  `Criterion` loop, and the modifier facets (`parse` / `modifier_ops`,
  `modifiable(op)`) feed `logic._resolve_modifiers` + `cli._modifier_values`.
  The argparse vocabulary (flags / `nargs` / `metavar` / `dest`) for the
  same attributes lives in `cli.MODIFIER_FLAGS`, not here (see
  ARCHITECTURE.md Rule 2).
  `TaskliItem` is a **recursive tree**: `id: str` is the full dotted
  positional path (`"1"`, `"1.2"`, `"1.10"` — was an `int`), and
  `children: list[TaskliItem]` (default `[]`, last field, needs
  `TaskliItem.model_rebuild()` for the self-reference) holds nested
  subtasks at **arbitrary depth** (the 2-level cap is a *list-name*
  limit, it does not reach item paths). There is no `progress` / rollup
  property — completion shows through the indented child rows and their
  own state markers. Module helper `walk_items(items) -> list[TaskliItem]`
  (pre-order DFS flatten, exposed by `taskli.models.tasks`) is what
  `TaskliList.get_item` and the model's own lookups iterate (`render`
  walks its own `_task_rows` tree instead, #104). `TaskliList` also carries
  `view_only: bool` (`Field(default=False, exclude=True)`) — a
  persistence-policy hint set on the deep-copied filtered views built in
  `logic._grouped_lists`; `storage.save_list` raises `RuntimeError`
  rather than persist a `view_only` list.
  `TaskliList` owns all item-mutation
  logic (`add_item`, `edit_item`, `add_tags`, `mark_done`, `mark_undone`,
  `mark_in_progress`, `remove_item`, `reindex`, `sort_by`, `resort`,
  `sort_by_index`, `filtered_items`, `prune`, `copy_item`, `move_item`,
  ...) as methods, not free functions — storage and CLI code call into
  these rather than manipulating `items` directly. `TaskliItem.status` is
  a tri-state `Status` (`TODO`/`IN_PROGRESS`/`DONE`, default `TODO`);
  each member carries a `marker` (`☐` / `■` / `■`) and a `color`
  (`Color.WHITE` / `Color.CYAN` / `Color.WHITE`), and a `marker_style`
  property returns `"dim"` for `DONE` else that `color` — the single
  source the `Task` column and `render_item_details`'s header paint the
  leading state glyph with, #104; `Color` moved above `Status` /
  `Priority` in `attributes.py` so the `Status` tuples can name it.
  `done` is a **derived, read-only property** (`status == Status.DONE`)
  kept for call sites (`prune`, `render.py`) that only need a plain bool
  — it is not a settable field. Legacy on-disk shapes (a `done: bool`
  key instead of `status`, a missing `modified_at`, a `priority`/`status`
  dict) are no longer translated at construction time — that logic moved
  to `migrations.py`, and a file on an older schema now raises on load
  rather than self-healing (see `storage.py` / `migrations.py` below).
  `due_date: datetime | None` and `description: str | None` (both after
  `completed_at`, both default `None`) were added with **no
  `CURRENT_LIST_VERSION` bump and no migration step** — additive,
  nullable, defaulted fields that pydantic fills on `model_validate` of
  an old file, exactly as `completed_at` was added (a bump would raise
  `OutdatedListFileError` on every existing file until `tk --migrate`).
  `due_date` values are normalised to midnight on input; `description`
  lost its dedicated `*` marker column with the `Task`-column collapse
  (#104) and full display still only returns with `--details` (#96), but
  `render._task_cell` now appends a dim `¶` after the task text whenever
  `item.description` is set (#117) — a bespoke indicator, not a
  `registry.ATTRIBUTES["description"]` render facet, so it shows in both
  the items table and (since `render_agenda` shares `_task_cell`, #116)
  the `--agenda` table for free.
  **Invariant: sibling order is id order** — within each sibling group
  ids are assigned by position (`reindex`), and only a sort
  (`sort_by`) changes position.
  `reindex` walks the tree renumbering dotted paths positionally
  (top-level `"1".."N"`, a child of `"1"` becoming `"1.1".."1.k"`,
  recursively — mutating `item.id` in place so held refs survive); it
  runs after any
  removal, after every add (via `resort`, see `cli.py` below), and on every
  load. `resort(sort)` is `sort_by(sort)` + `reindex()` in one call — the
  two always travel together, so every caller that needs "sort then
  renumber" (adding an item, changing `default_sort`) goes through this
  instead of duplicating the pair. Both take a `Sort` value object
  (`query.py`): `sort_by` is no longer a `match` on the `SortBy` string,
  it sorts each sibling group with `sorted(..., key=sort.key,
  reverse=sort.descending)` and recurses into `children`,
  with the per-mode key funcs (`created_at`, `priority.index`, the tags
  tuple) now living on each registry entry's `sort_key`
  (`registry.ATTRIBUTES[...].sort_key`) — `query._SORT_KEYS` is gone.
  `Sort.__post_init__` validates `attr_key` against `registry.sortable()`,
  and `Sort.from_default_sort` reads `sort_descending` off the registry
  entry (the old hard-coded `descending=(value == "priority")` is gone).
  `SortBy` is likewise no longer a `Literal` — it is a plain `str` alias
  (kept for the package export / call sites), and `Config.default_sort` is
  a `str` field with a `field_validator` rejecting anything not in
  `registry.sortable()`. The `str → Sort` conversion is
  `Sort.from_default_sort`, called in `logic.py` at the `add`/`move`/
  `copy`/`set_config` call sites (`storage.resort_all_lists` just
  receives the resulting `Sort`).
  `sort_by_index` is the inverse — it
  reorders each sibling group to match existing `id` values (keyed on
  `paths.path_key`), recursively — and exists solely so
  `storage.py` can enforce the invariant before writing, without touching
  `.items` directly. Editing an item's `priority`/`tags`/`due_date` does *not*
  trigger a resort, so under a non-`created_at` `default_sort` (including
  `default_sort due_date`) an edited item can visibly sit out of sort
  order until the next add or `default_sort` change — a known, accepted
  gap. Re-parenting via `-e --under` **does** resort (the item lands in
  `default_sort` order within its new sibling group), unlike other `-e`
  edits. Every id-taking method (`get_item`, `edit_item`, `add_tags`,
  `mark_done`/`mark_undone`/`mark_in_progress`, `remove_item`,
  `copy_item`, `move_item`) accepts `str | int` and normalises via
  `str()`, so existing int-passing call sites keep working; `get_item`
  searches `walk_items(self.items)` and raises `ItemNotFoundError` for a
  missing id — there's no plural/batch variant on the model.
  `remove_item`/`copy_item`/`move_item`/`mark_*` are thin wrappers that
  `get_item` the id and delegate to a `*_ref` variant
  (`remove_item_ref`/`copy_item_ref`/`move_item_ref`/`mark_*_ref`) taking
  an already-resolved `TaskliItem`; `remove_item_ref` finds the
  containing sibling list by identity and drops the item with its whole
  subtree (cascade), then `reindex()`es. `reparent_item` /
  `reparent_item_ref` are the same wrapper/`*_ref` pair: an identity
  splice that detaches the item + subtree and re-appends it under the
  new parent (or `self.items` when `parent_path` is `None`), preserving
  `status` / `completed_at` / `modified_at`, with a cycle guard raising
  `InvalidReparentError` when the target is the item itself or one of
  its descendants — `-mv`/`--move` stays cross-list only. Held refs
  survive `reindex()` (it
  mutates `item.id` in place, not identity). `logic`'s batch commands
  (`-d`/`-u`/`-i`/`-rm`/`-mv`/`--copy`) resolve every id to a ref up front
  via `_resolve_items` and then mutate by reference, rather than looping
  raw ids and catching per id (see below).
  `add_item(text, attrs=None, *, created_at=None, modified_at=None,
  parent_path=None)` and
  `edit_item(item_id, attrs)` take one typed mapping of field name →
  value instead of per-field kwargs: `add_item` splats it into the
  `TaskliItem(...)` constructor (full pydantic validation), `edit_item`
  applies it with a bare `setattr` per key (no `validate_assignment` on
  `TaskliItem` — value correctness is the caller's job, done by
  `logic._resolve_modifiers` running each attribute's registry `parse`);
  an empty `attrs` on `edit_item` is a no-op that leaves `modified_at`
  untouched. `add_item`'s `parent_path` (a dotted item path) nests the
  new item under that parent's `children` instead of at the top level,
  with a provisional child id the following `resort`/`reindex` finalises.
  `edit_item` itself has no `parent_path` — re-parenting is a separate
  `reparent_item` call `logic.edit` makes after `edit_item`.
  `copy_item_ref` builds its attr mapping generically from
  `registry.modifiable("add")` (re-copying the `tags` list into a fresh
  object), so a new settable field is copied with no `copy_item_ref`
  edit, then recurses each child into the new item's `children` via
  `_copy_subtree` (fresh items, `status` reset to the `TaskliItem`
  default since it isn't an add-modifier).
  `filtered_items(item_filter)` takes a single `Filter` (`query.py`) and
  returns **deep-copied** narrowed subtrees — an item is kept when it or
  any descendant matches, `children` pruned to the kept copies and the
  originals left untouched (so a filtered forest can never reach
  `save_list`). AND-combining multiple criteria
  (tag + priority) lives in `Filter.matches` / `Criterion.matches`,
  not in this method. `prune()` works bottom-up: it drops a done item
  only when its *entire* subtree is done (a done leaf always goes, a done
  parent with a surviving un-done descendant stays), returns every
  removed item as one flat list, and `reindex()`es. `add_tags(item_id,
  tags)` appends new tags to an item's
  existing tags (deduplicated, order-preserving) — this backs `-e/--edit`'s
  `--add-tag`, as opposed to passing `tags` in `edit_item`'s mapping,
  which replaces the whole list. `copy_item(item_id, target)` recreates an
  item and its whole subtree in another
  `TaskliList` as fresh items (new dotted ids, status reset) via
  `add_item` + `_copy_subtree`; `move_item(item_id, target)` does the
  same and then removes the original subtree from `self`. Neither resorts
  `target` — callers resort once
  after a whole batch, same as `add_item`. `modified_at` defaults to
  `created_at` on `add_item`, and is bumped to `datetime.now()` by
  `mark_done`, `mark_undone`, and `add_tags` unconditionally, and by
  `edit_item` whenever its `attrs` mapping is non-empty (not compared
  against the existing value, so passing the same
  value still bumps it). `mark_undone` resets `status` to `Status.TODO`
  from either `DONE` or `IN_PROGRESS` (not just from `DONE`) and clears
  `completed_at`; `mark_in_progress` sets `status` to `IN_PROGRESS` and
  also clears `completed_at`; `mark_done` sets `status` to `DONE` and
  stamps `completed_at`. All three set `status` unconditionally, with no
  guard on the item's prior state. `copy_item` (and `move_item`, via delegation)
  deliberately deviates from `add_item`'s normal "everything is now"
  default: it passes the **source** item's `created_at` through to the
  new item but leaves `modified_at` to be stamped with the copy time,
  via `add_item`'s `created_at`/`modified_at` override params.
- **`hierarchy.py`** — pure list-name hierarchy helpers (`ancestor_chain`,
  `parent_list_name`, `child_list_names`, `descendant_list_names`): dotted-name
  string splitting only, no filesystem, imports nothing from the package.
  Imported by `storage.py`, `render.py`, and `cli.py` (each was previously
  reaching into `storage` for these). `child_list_names`/`parent_list_name`
  have no non-test callers yet but move with the family.
- **`migrations.py`** — versioned schema migrations for on-disk files, a
  stdlib-only leaf beside `hierarchy.py` / `exceptions.py` that operates
  on already-parsed dicts (no `json`, no package imports). Every list and
  config file carries a top-level `version` key; `file_version(raw)`
  reads it (absent/`null`/non-int → 0). Two ordered chains,
  `_LIST_MIGRATIONS` / `_CONFIG_MIGRATIONS` (index *i* migrates version
  *i* → *i*+1), currently one step each (`base → v1`):
  `_list_base_to_v1` folds a legacy `done: bool` into `status`, fills a
  missing `modified_at` from `created_at`, unwraps a `priority` /
  `status` dict to its `"label"`, and (for the subtasks shape)
  stringifies each `item["id"]` and adds `item["children"] = []`;
  `_config_base_to_v1` unwraps a `default_priority` dict. The subtasks
  change rides this existing step with **no `CURRENT_LIST_VERSION` bump**
  (still `1`) — v1 is redefined to be the subtasks shape because no real
  data is on v1 yet. It needs a migration step at all — unlike the
  purely-additive `due_date` / `description`, which pydantic just
  back-fills on `model_validate` — because `id` changing type (`int ->
  str`) fails `model_validate` on an int-id file. `migrate_list` / `migrate_config` deep-copy
  their input, apply every step above the file's version, stamp
  `version = CURRENT_LIST_VERSION` / `CURRENT_CONFIG_VERSION` (both `1`),
  and are idempotent. `list_needs_migration` / `config_needs_migration`
  are `file_version(raw) < CURRENT_*_VERSION`. The historical label
  strings (`"done"`, `"todo"`, `"high"`, …) are hard-coded, not imported
  from `attributes.py` — a migration freezes a past on-disk shape, so a
  later enum-label rename must not retroactively change what it means.
  `tk --migrate` (`storage.migrate_all` → `logic.migrate`) is the only
  thing that rewrites an outdated file; `load_*` raises instead of
  healing.
- **`env.py`** — stdlib-only leaf beside `hierarchy.py` / `migrations.py` /
  `exceptions.py` (imports only `os` / `pathlib`, nothing from the package),
  and the one leaf that touches the filesystem: `CONFIG_FILE_NAME`
  (`.taskli.json`), `resolve_storage_dir() -> Path` (expands `TASKLI_PATH`
  or `~/.taskli` and `mkdir`s it), and `scan_list_names(storage_dir) ->
  list[str]` (a sorted `glob("*.json")` stem scan excluding the config
  file). It exists so `cli.py`'s parser / tab-completion path
  (`import taskli.cli`) can resolve the storage dir and enumerate list
  names without importing `storage.py` — and therefore pydantic.
  `storage.config_file_path` / `storage.list_all_lists` delegate to it, and
  `logic.py` / `cli.py` import `resolve_storage_dir` from `env` directly.
- **`storage.py`** — filesystem persistence. Each list is one JSON file at
  `$TASKLI_PATH/<name>.json` (`TASKLI_PATH` defaults to `~/.taskli`,
  resolved by `env.resolve_storage_dir`). List names double as both the on-disk
  filename and the sublist path: `work.meetings` is a real file
  `work.meetings.json`, not a directory — `hierarchy.py`'s
  `ancestor_chain`/`parent_list_name`/`child_list_names`/
  `descendant_list_names` do the dot-splitting to derive hierarchy from that
  flat file layout. Nesting is hard-capped at 2 sublist levels
  (`list_file_path` raises `TooManyAncestorListsError` past that).
  `ensure_ancestors` auto-creates missing parent lists when a nested name is
  first written to — this is why `tk work.meetings -a "..."` works with no
  prior `tk work --new`. `create_list` / `ensure_ancestors` /
  `load_or_create_list` each take a `config: Config | None = None` keyword:
  when a `Config` is passed, a new (sub)list created with no explicit color
  inherits the nearest existing ancestor list's color (via module-private
  `_inherited_color` walking `ancestor_chain` nearest-first, then
  `_new_list_color` resolving explicit > inherited > `config.default_color`),
  gated on `Config.inherit_sublist_color`; `config=None` keeps the prior
  model-default behavior and only `rename_list` still calls that way. The
  `ensure_ancestors` loop saves each ancestor before resolving the next, so
  a deep chain inherits top-down (`work.meetings` sees `work` a beat before
  `work.meetings.q3` sees `work.meetings`). `save_list` refuses to persist a `view_only`
  (filtered, deep-copied) list — `raise RuntimeError` — a never-happens
  backstop, since `logic` never hands a filtered view to it. `save_list`
  calls `sort_by_index()` before
  writing and `load_list` calls `reindex()` right after parsing — together
  these are the two points that enforce the id-order invariant above, so a
  hand-edited file with non-contiguous ids self-heals on next load.
  `load_list` and `load_config` now `json.loads` the file first and gate
  the raw dict through `migrations.list_needs_migration` /
  `config_needs_migration` **before** `model_validate`: an older-schema
  file **raises** `OutdatedListFileError` / `OutdatedConfigFileError`
  (message names `tk --migrate`) instead of being silently healed — the
  old load-time `backfill_modified_at()` shim is gone, and a missing
  `modified_at` is now filled by the `base → v1` list migration (which is
  why the field stays `Optional` on the model despite always being set
  going forward). `save_list` / `save_config` inject a top-level `version`
  key (`migrations.CURRENT_LIST_VERSION` / `CURRENT_CONFIG_VERSION`) into
  the dumped JSON. `_atomic_write(path, text)` writes a sibling `.tmp`
  file then `os.replace`s it into place — used only by `migrate_all`.
  `migrate_all(storage_dir) -> list[tuple[str, str]]` walks the config
  file then every list from `list_all_lists`, returning `(name, outcome)`
  pairs where `outcome` is `"migrated"` (a pending migration applied),
  `"current"` (already up to date), or `"unreadable"` (JSON parse
  failure); it is idempotent and is the only thing that rewrites an
  outdated file — load never auto-heals. It backs `tk --migrate` via
  `logic.migrate`.
  `resort_all_lists(storage_dir, sort)` walks every list via
  `list_all_lists`, skipping any that fail to load (`TaskliError`), and
  `resort`s + saves each — `sort` is a `Sort` value object (`logic`
  passes `Sort.from_default_sort(config.default_sort)`). This is what
  `--config default_sort <value>` calls, so that config change rewrites
  every list file on disk, not just future adds.
- **`render.py`** — all `rich` output (tables, tree views, error lines).
  Nothing else in the package prints directly. Every styled span is built
  as a `rich.text.Text` (`.append` / `Text.assemble`), never bracket-tag
  markup: the old `_add_bold` / `_add_color` string helpers are one
  `Text`-returning `_label(name, color, *, bold=False)` (a `"bold"` +
  `str(color)` style string). `_label`, every styled `_items_table` /
  `render_agenda` cell, and `render_config`'s cells go through
  `_span(text, style="")` — `Text().append(text, style=...)`, a
  span-scoped style so a table's cell padding stays unstyled (a bare
  `Text(text, style=...)` paints the padding too); an unstyled item
  cell still passes as raw `str`. `render_list_tree` builds
  the nested tree view of a list plus (optionally) its descendants used
  by the default view. `_items_table` (shared by `render_items` and
  `render_list_tree`) leads with one bespoke `Task` column built in
  `render.py` (#104): `_task_rows(items)` walks the item tree pre-order,
  yielding each item with its `├── ` / `└── ` tree-branch prefix, and
  `_task_cell` assembles that prefix, the `status.marker` glyph (painted
  `status.marker_style` — a `Status` property returning `"dim"` for a done
  item, else the status color), the trailing-dot id (built inline,
  `"2.1" -> "2.1."`), and the item text (`"dim strike"` when done) as one
  `Text` of independently-styled `.append` spans. The
  remaining columns — `Priority` / `Tags` / `Due` — still come from
  `registry.renderable()` (`column_header` / `column_justify` per column,
  `render_format` then optional `render_style` per cell), so a new
  *attribute* render column is a registry entry, but the
  task/id/state/text presentation is a `render.py` edit — the same
  sanctioned bespoke-table pattern `render_agenda` uses. Cells are typed
  `list[str | Text]`: a plain `str` when unstyled, `_span(cell, style)`
  when the column's `render_style` yields one. `TaskliList.get_item`
  still iterates `walk_items`; only `_items_table` switched to
  `_task_rows`. The `Due` column's `render_style` is `"red"` for an
  overdue item, `"yellow"` for one due today, `None` otherwise or when
  done — a plain registry entry, no `render.py` edit. `render_message`
  prints a plain status line, `render_config` a key/value table
  (`_span` cells), and `render_value` a raw value (a path, a config
  value) — all three wrap their strings in an unstyled `Text`, so
  `markup=False` is no longer needed (`Text` never interprets markup)
  and `[`-containing values and long paths survive unmangled;
  `render_value` still passes `highlight=False` / `soft_wrap=True`
  (unrelated concerns). `render_message` / `render_value` replace every bare
  `print()` `cli.py` used to do. One accepted consequence of the
  all-`Text` switch: `render_error` / `render_warning` / `render_reminder`
  no longer run rich's repr-highlighter over the message (quoted names,
  digits render plain now) — the bold-colour prefix is unaffected. `render_reminder(overdue, due_today)`
  prints the bold-yellow due/overdue banner to `_err_console`
  (stderr) — unlike `render_warning`, which (despite its docstring)
  prints to `_console` (stdout); `render_reminder` only borrows its
  bold-yellow styling, not its stream. It joins whichever of "N
  overdue" / "M due today" are nonzero into one line; `cli._dispatch`
  only calls it when at least one count is nonzero.
  `render_agenda(rows: list[tuple[str, TaskliItem]], delimiter=".")`
  (#94) is `render_reminder`'s detailed companion — a flat `List` /
  `Task` / `Due` table across every list, one row per
  `(list_name, item)` pair from `logic.agenda`, already sorted
  chronologically. It's a deliberate bespoke table, **not** routed
  through `registry.renderable()`/`_items_table` — those are shaped for
  one list's items, not cross-list `(name, item)` pairs — but it does
  build its `Task` cell via the shared `_task_cell(item, "")` (#116, same
  helper `_items_table` and `render_item_details`'s subtasks block use)
  and its `Due` cell via module-local `_due_display(item)` (shared
  with `render_item_details`) — `(formatted, style)` off
  `registry.ATTRIBUTES["due_date"]`'s `render_format`/`render_style`, the
  same red-overdue/yellow-due-today logic `_items_table`'s `Due` column
  uses — and `TaskliList(name=name).display_name(delimiter)`
  (same pattern `logic.delete_prompt` uses) to turn each row's raw list
  name into a display name. Empty `rows` prints a dim "nothing on the
  agenda." line, matching `render_list_names`'s empty-state style.
  `render_item_details(task_list, item, delimiter=".")` (#96) prints one
  task's full detail as a `rich.Panel` (title `"<list> / <id>"`,
  `border_style="dim"`): a bold (bold-strike when done) header line, a
  `Table.grid` of `status`/`priority`/`tags`/`due`/`created`/`modified`
  rows (empty rows skipped, `priority` via `_span`), then an optional
  dim-headed `description` block and an optional `subtasks` block that
  reuses `_task_rows`/`_task_cell` for the child tree. The `due` row calls
  `_due_display(item)` (shared with `render_agenda`) and appends a
  relative-day hint from module-local `_relative_due`, which reads the
  `today()` seam (`from .models.dates import today`).
  `render_list_names` picks each node's style with a `bold` bool
  (`i == default_name`) fed to `_label`, not the old
  `_add_bold`-vs-`_add_color` function reference. `render_error`,
  `render_warning`, and `render_reminder` compose their prefix + message
  via `Text.assemble` (`("error:", "bold red")` etc.) rather than a
  bracket-markup f-string.
- **`logic.py`** — per-command orchestration, one public function per
  command (`add`, `edit`, `batch_actions` (with `mark_done`/`mark_undone`/
  `mark_in_progress`/`remove_items` as thin delegators to it),
  `move`, `copy`, `prune`, `set_list_color`, `new_list`,
  `rename`, `delete_prompt`/`delete_confirmed`, `set_config`, `migrate`
  (takes no `Config` — it may be repairing it), `list_entries`,
  `list_view`, `all_views`, `storage_path`, `check_reminders`, `agenda`,
  `item_details` (returns plain `tuple[TaskliList, TaskliItem]` —
  `load_list` + `get_item`, letting `ItemNotFoundError` propagate to
  `cli._dispatch`'s `@_handle_errors`; precedent = `agenda`);
  plus private `_mutate` / `_grouped_lists` /
  `_resolve_modifiers` / `_per_item` / `_all_items`). Each loads via
  `storage`, mutates via `TaskliList` methods, saves, and returns either
  a `CommandResult` (`messages`/`warnings`/`exit_code` + at most one of
  `item_view` / `tree_view`) or plain data (`list_view` →
  `list[TaskliList]`, `all_views` → `list[list[TaskliList]]`,
  `list_entries` → `[(name, color)]`, `agenda` →
  `list[tuple[str, TaskliItem]]`, `item_details` →
  `tuple[TaskliList, TaskliItem]`). `logic.py` imports no `render` and
  prints nothing.
  Batch handlers (`batch_actions`, `move`, `copy`) collect one
  message per id and one warning per missing id, and set
  `exit_code = 1 if warnings else 0` — the split `messages`/`warnings`
  lists mean the CLI emits all successes then all warnings (the pre-split
  code interleaved them in id order). `batch_actions(list_name, config, *,
  done=None, undone=None, in_progress=None, remove=None)` is the single
  entrypoint for `-d`/`-i`/`-u`/`-rm` (combinable in one invocation, see
  `cli.py` below): one `load_list`, then `_resolve_items` per group
  (`drop_covered=False` for the three marks, `True` for `remove`), then
  **all marks, then all removals** (so a removed subtree's cascade +
  `reindex` can't strand a just-marked ref), then one `save_list` and one
  `item_view`. The four `mark_done`/`mark_undone`/`mark_in_progress`/
  `remove_items` names remain as one-line delegators (call sites and tests
  unchanged). An id under both a mark flag and `remove` is honoured for
  both — only reachable via distinct raw strings (`-d 1.1 -rm 1`), since
  the CLI rejects the same raw string under two of the four flags.
  All batch handlers resolve
  their ids to `TaskliItem` refs up front via `_resolve_items`
  (identity-deduped, one warning per missing id), then mutate by
  reference in user-supplied order — iteration order no longer matters
  (`reindex` mutates `item.id`, not identity), and duplicate ids
  collapse to a single action. Messages now come out in user order
  (previously descending for `remove_items`/`move`). Their id params are
  `list[str]` (dotted item paths) now, not `list[int]`; `move`/`copy`
  still default an empty id list to the source's **top-level** items
  only, each subtree travelling with its root.
  `add(list_name, texts, modifiers, config, parent_path=None)` and
  `edit(list_name,
  item_id, modifiers, config, parent_path=None)` take one raw
  `modifiers: dict[str, object]`
  (field name → unparsed string) instead of per-field params.
  `_resolve_modifiers` runs each attribute's
  `registry.ATTRIBUTES[name].parse` (passthrough when `None`), wrapping
  any `KeyError`/`ValueError`/`TaskliError` from a parser as
  `InvalidModifierValueError` naming the attribute and bad value. `add`
  defaults a missing `priority` to `config.default_priority` before
  resolving, then `_per_item` shallow-copies the typed mapping per item
  so two added items never share one `tags` list; `edit` pops the
  reserved `add_tag` key (append semantics) before resolving the rest.
  `add` threads one `parent_path` (from `cli`'s `--under`) into every
  `add_item` call, so a repeated `-a` nests every new item under the
  same parent. `edit` likewise takes `parent_path` — when not `None` it
  calls `TaskliList.reparent_item(item_id, parent_path or None)` (so
  `--under ""` un-nests) then `resort`s before reading the id back for
  the message; a plain `-e` with no `--under` still does not resort.
  `_all_items(storage_dir) -> list[tuple[str, TaskliItem]]` is the
  shared, filter-free walk both `check_reminders` and `agenda` build on:
  one pass over every list via `walk_items`, skipping one that fails to
  load (`TaskliError`, same pattern as `list_entries`/`resort_all_lists`).
  Deliberately filter-free rather than filter-taking, so a caller needing
  two filters (`check_reminders`) doesn't reparse every list file twice —
  it loads once and applies both filters per item in the same loop.
  `check_reminders() -> tuple[int, int]` counts, over one
  `_all_items` pass, items matching `due_to_criteria("overdue")` against
  those matching `due_to_criteria("today")` plus a `done EQ False`
  criterion — reusing `due_to_criteria` rather than rebuilding its LT/EQ
  formula by hand. It backs the `cli._dispatch` reminder banner
  (`Config.show_reminders` below).
  `agenda(window: str | None, config) -> list[tuple[str, TaskliItem]]`
  is `check_reminders`'s detailed companion (`tk --agenda`, #94): resolves
  `window or config.agenda_window`, builds one `Filter(agenda_criteria(token))`
  (`query.py`), filters an `_all_items` pass, and sorts the result by
  `registry.ATTRIBUTES["due_date"].sort_key` — chronological, cross-list,
  subtasks included via the same `walk_items` flatten. Returns plain
  data, same precedent as `list_entries`, not a `CommandResult`; `cli.py`
  calls `render.render_agenda` on the result directly.
- **`cli.py`** — argparse routing and command dispatch built from four
  small "register" functions (`_register_list_args`,
  `_register_item_action_args`, `_register_modifier_args`,
  `_register_config_args`), assembled into one parser by
  `_compose_parser`; every command is a flag, so there's no
  `argv[0]`-based dispatch and no reserved bare word a list name could
  collide with.
  - `logic` / `render` / `storage.load_config` are **function-local
    imports**, so the argcomplete / tab-completion path (`import
    taskli.cli`, reached on every `<TAB>`) never loads pydantic or rich —
    module scope imports only `.__version__`, `.exceptions`, `.env`
    (`resolve_storage_dir` / `scan_list_names`), `.models` (`registry`),
    and the pydantic-free `models` leaves (`attributes`, `paths`,
    `query`); `Config` / `TaskliList` / `CommandResult` annotations are
    quoted forward refs under `TYPE_CHECKING`. `_complete_list_names`
    enumerates list names via `env.scan_list_names(resolve_storage_dir())`,
    not `logic`.
  - `list` is the only positional (defaults to `config.default_list`
    when omitted). Flags fall into four **option groups**, each backed
    by its own enum: list management (`ListCommands` —
    `-n/--new`, `--delete`, `-l/--lists`, `--prune`, `--rename`,
    `--migrate`), item action
    (`ItemActionCommands` — `-a`, `STATUS` covering
    `-rm/--remove`/`-d`/`-u`/`-i/--in-progress` as one combinable op,
    `-e`, `-D/--details`, `-mv/--move`, `--copy`),
    config
    (`ConfigCommands` — `--config`),
    and the default view
    (`ListCommands.VIEW`, when nothing from the other three is given).
    Modifiers (`-p/--priority`, `--tag`, `--add-tag`, `--all`, `--under`,
    `-t/--text`, `--due`, `--desc`, `--color`) are a separate,
    non-mutually-exclusive group layered on top of whichever op is
    resolved. Every modifier except `--all` and `--under` (both scope
    flags, not attributes — `--under PATH` works with `-a`, naming the
    parent item for a new subtask, **and** with `-e`, re-nesting an
    existing item + subtree under `PATH`, where `--under ""` un-nests to
    the top level) is declared in one module-level
    `MODIFIER_FLAGS` table
    keyed by the same field-name strings the registry uses
    (`priority`/`tags`/`due_date`/`text`/`description`/`color`);
    `_register_modifier_args` iterates it to emit the `add_argument`
    calls. Each value is a `ModifierSpec` carrying the argparse args plus
    an optional `filter_dest` (filterable ones) and `to_criteria` (a
    token → `tuple[Criterion, ...]` builder — only `due_date` sets one,
    to `query.due_to_criteria`); it no longer carries `parse` — that
    moved onto the registry entry. This table is the deliberate,
    developer-approved exception to the "no new `cli.py` module
    constants" rule — the registry can't carry argparse vocabulary
    (Rule 2), so the flag spec lives here. Consequence: adding a
    filterable/sortable/settable attribute is a two-table edit — the
    `models/registry.py` `Attribute` entry (`parse` / `modifier_ops`
    plus any filter/sort facets) AND the `MODIFIER_FLAGS` entry (argparse
    vocab, plus `filter_dest` / `to_criteria` as needed) — kept honest by
    `test_cli.py::TestModifierRegistryParity`. `_modifier_values(op,
    namespace)` builds the raw modifier mapping passed to `logic.add` /
    `logic.edit` by iterating `MODIFIER_FLAGS` ∩ `registry.modifiable(op)`,
    including a key whenever its namespace value `is not None` — so
    `--desc ""` is included (and `description`'s `parse`, `lambda s: s or
    None`, then turns it into a clear) while an omitted `--desc`
    (namespace default `None`) is left untouched.
    The VIEW filter loop in `_dispatch` iterates `registry.filterable()`,
    reading `MODIFIER_FLAGS[name].filter_dest` off the namespace, then
    branching on `spec.to_criteria` if set, else falling back to the
    registry entry's `parse` + `filter_default_operator`.
  - `_resolve_op` picks the op to run: it checks the three flag groups
    in a fixed priority order — list management, then item action, then
    config — and takes the first one with anything set. If two or more
    groups have something set, it calls `render_warning` (naming the
    winning op and the ignored group(s)) instead of erroring; the old
    "list-mgmt + item-action chained in one call" behavior no longer
    exists — exactly one op runs per invocation, full stop (the four
    status flags `-d`/`-i`/`-u`/`-rm` combine *within* the single
    `ItemActionCommands.STATUS` op, resolved before `ADD` so a
    `-a … -d …` combo still lands in the STATUS validation case). Falls
    back to `ListCommands.VIEW` when nothing is set. Bare `--color` (no other
    list-management flag) resolves to `ListCommands.COLOR` — recoloring
    an existing list; `--color` alongside `--new` still resolves to
    `NEW`, with color as the creation modifier.
  - `_validate` is a `match/case` over the resolved op (mutually
    exclusive by construction, since `_resolve_op` already picked one),
    rejecting modifiers that don't apply via `parser.error(...)` (exit
    2). The ~8 repeated `(namespace.priority or namespace.tag or ...)`
    tuples are now one `_reject_modifiers(namespace, parser, message,
    allowed)` helper, called per case with a per-op set of allowed
    modifier dests (dest universe = `MODIFIER_FLAGS` dests `| {"all",
    "under"}`);
    the `_reject_modifiers` message strings are unchanged. E.g.
    `-D`/`--config`/`--delete`/`--lists`/`--rename`/`--migrate`
    reject every modifier; the `STATUS` case (`-d`/`-i`/`-u`/`-rm`) also
    rejects every modifier (`"no modifiers are valid with -d/-i/-u/-rm."`),
    rejects combining any of the four with `-a`/`-e`/`-D`/`-mv`/`--copy`
    (`"…cannot be combined with…"`, exit 2), and rejects the same raw id
    string given to more than one of the four (`"id X given to more than
    one action flag."`, exit 2) — a duplicate *within* one flag stays
    silent (`_resolve_items` collapses it); `--prune` allows only `--all`;
    `--new` and bare
    `--color` allow only `--color`; `-a` allows
    `-p`/`--tag`/`--due`/`--desc`/`--under` and `-e` those plus
    `-t`/`--add-tag`,
    both rejecting `--all`; the default VIEW allows
    `-p`/`--tag`/`--all`/`--due`; `-e`
    additionally rejects giving both `--tag` (replaces) and `--add-tag`
    (appends) in the same call; `-mv`/`--copy` reject every modifier too
    and additionally validate that every id after `TARGET_LIST` parses
    as a dotted item path via `models.paths.path_key` (error "ID must be an
    item path like 1 or 1.2.", exit 2), since `nargs="+"` can't
    type-check the list itself.
  - `-d`/`-u`/`-i`/`-rm` (and `-e`/`-D`) no longer carry `type=int` — an id is
    a dotted item path (`1.2`), and a malformed one falls through to
    `ItemNotFoundError` (exit 1), not an argparse error (exit 2);
    `-mv`/`--copy` keep an explicit `path_key` check in `_validate`
    (exit 2).
  - `-D/--details` (`ItemActionCommands.DETAILS`, `nargs=1`) is a
    read-only item view: `_dispatch` has its own `case` before the
    generic `ItemActionCommands()` arm that calls `logic.item_details`
    (plain `(TaskliList, TaskliItem)` in) then `render_item_details`
    directly and returns 0 — no `CommandResult`/`_emit`, same shape as
    `--agenda`/`--lists`. `_validate` rejects every modifier for it; a
    malformed or missing id falls through to `ItemNotFoundError`
    (exit 1), like `-e`. `_run_item_action` never sees it. `-d`/`-u`/`-i`/`-rm`
    each take one or more ids (`nargs="+"`), are combinable in one
    invocation (each with its own id list), and route through one
    `logic.batch_actions` call
    with
    partial-success semantics: it resolves each group's ids to `TaskliItem`
    refs up front (`_resolve_items`, one `CommandResult.warnings` entry
    per missing id), applies **all marks then all removals**, then mutates
    by reference, and sets `exit_code` to 1
    if any id failed. Because the mutation targets a held ref, not a
    re-looked-up id, iteration order is irrelevant even though
    `remove_item_ref` reindexes on every call.
  - `-mv/--move`/`--copy` take `TARGET_LIST` plus zero or more ids
    (`nargs="+"`, first token is the list, the rest are ids) — omitting
    every id acts on the whole source list. `logic.move`/`logic.copy`
    auto-create `TARGET_LIST` via `load_or_create_list`, same as `-a`.
    Both resolve ids to `TaskliItem` refs up front (`_resolve_items`)
    before mutating, so iteration order doesn't matter. Both resort the
    target once after the batch, and return the target as `item_view`
    (source is also saved for `-mv`, since it changed).
  - `-a` is repeatable (`nargs="+", action="append"`); each occurrence
    is one item, and a single `-p`/`--tag` pool applies to every item
    added in the same invocation — there's no per-`-a` priority/tags. A
    single `--under PATH` (threaded as `logic.add`'s `parent_path`)
    likewise nests every item from that invocation under the same
    parent item.
  - `--prune` supports `--all`, scoped the same way as the default
    view's `--all`: without it, prunes just `list`; with it and an
    explicit `LIST`, prunes `list` plus every descendant
    (`descendant_list_names`) — a missing explicit `list` still raises,
    same as without `--all`; with it and no `LIST` given (falls back to
    `default_list`), prunes every list on disk instead, skipping any
    that fail to load. `logic.prune` returns one summary line per list in
    `messages` and every pruned list in `tree_view`.
  - The default view builds one opaque `Filter` (from `--tag`,
    `-p/--priority`, and `--due`) in `_dispatch` and threads it unchanged
    through
    `TaskliList.filtered_items`, `logic._grouped_lists`,
    `logic.list_view`, and `logic.all_views` — none of these take
    separate `tag`/`priority` params any more, so a new filterable
    attribute doesn't grow their signatures. `--all` (with a target)
    recurses through every descendant via `logic._grouped_lists`, or
    (without a target) every root list via `logic.all_views`. Whether a
    filter is set is `Filter.active` (the old `logic._filter_active`
    helper is gone).
  - `_dispatch` (not each handler) is wrapped in `_handle_errors`, which
    catches `TaskliError` subclasses, renders them via `render_error`,
    and returns exit code 1 — the moved `logic.*` functions carry no
    decorator. `_dispatch` calls the `logic.*` function for the resolved
    op, then `_emit(result, config)` turns the returned `CommandResult`
    into `render_message` / `render_warning` / list-view calls (the
    message/warning loop is factored into `_render_notices`, shared with
    the `--migrate` path); view ops
    (`--lists`, `--config` read, default view) call `render_*` directly
    with the data `logic` returns. `--migrate` rejects every modifier
    (like `--lists`), and `_dispatch` short-circuits it — calling
    `_render_notices(logic.migrate())` directly (no config, no view) —
    *before* it calls
    `load_config(resolve_storage_dir())`, so `tk --migrate` still runs
    against an outdated or corrupt config; `main()` no longer loads
    config, and because `load_config` now runs inside `@_handle_errors`,
    a stale/corrupt config renders cleanly instead of crashing.
    `--delete` is a two-call split:
    `logic.delete_prompt` builds the text, `cli._confirm` prompts
    (`input()` stays cli-side, as does the `"aborted."` line), then
    `logic.delete_confirmed` deletes. argparse's own validation failures
    (and `_validate`'s `parser.error` calls) raise `SystemExit`
    independently and surface as exit code 2 — the two error paths are
    not unified.
  - Right after that `load_config`, `_dispatch` runs the due/overdue
    reminder banner — gated on `Config.show_reminders` (default
    `True`, plain bool, no migration needed since it's additive with a
    Python default) — calling `logic.check_reminders()` and, when
    either count is nonzero, `render_reminder(overdue, due_today)`.
    This runs before `list_name` resolution and the `match op:` block,
    so it fires on every op except `ListCommands.MIGRATE` (already
    short-circuited above this point) and `ListCommands.AGENDA` — the
    banner check is explicitly gated off for `--agenda`
    (`config.show_reminders and op is not ListCommands.AGENDA`) since the
    agenda table it would sit above already shows the same overdue/
    due-today items in full detail; skipping it also avoids a second,
    redundant `_all_items` walk of every list file in the same
    invocation. `--config show_reminders false` already works
    for free through the generic `Config.set_value`/`get_value` path,
    same as `auto_prune` — it needed no `MODIFIER_FLAGS` or
    `models/registry.py` entry, since it isn't a per-item attribute.
  - `ListCommands.AGENDA` (`--agenda`, #94) is a fifth member of the
    list-management mutually-exclusive `ops` group, registered with
    `nargs="?", const="", default=None` so `tk --agenda` (no value) and
    `tk --agenda WEEK` both resolve `namespace.agenda is not None` (the
    `is not None` check, not truthiness, mirrors `ConfigCommands`'s
    `namespace.config is not None` — `const=""` for "flag given, no
    override" is falsy). It ignores `LIST`/`list_name` entirely, same as
    `--lists`: `_dispatch`'s case calls
    `render_agenda(logic.agenda(namespace.agenda or None, config),
    config.sublist_delimiter)` directly and returns 0 — plain data in, a
    `render_*` call, no `CommandResult`/`_emit`, same shape as
    `ListCommands.LISTS`. `_validate` rejects every modifier for it (same
    grouped case as `--delete`/`--lists`/`--rename`/`--migrate`). A bad
    window token surfaces as `InvalidModifierValueError` from
    `logic.agenda` → `query.agenda_criteria` → `dates.parse_agenda_window`,
    caught by the existing `@_handle_errors` on `_dispatch` — same path
    a bad `--due` value already takes, no special handling needed.
    `Config.agenda_window: str = "week"` (validated by
    `dates.parse_agenda_window`) is the fallback when `--agenda` is given
    with no override; `--config agenda_window week` already works for
    free through the generic `Config.set_value`/`get_value` path, same
    as `show_reminders`/`auto_prune` above.
- **`exceptions.py`** — flat `TaskliError` subclass hierarchy; every
  domain-level failure (missing list, missing item, invalid name,
  nesting too deep, corrupted JSON, outdated schema version, invalid
  modifier value — `InvalidModifierValueError`, invalid re-parent —
  `InvalidReparentError`) is caught
  centrally in `cli.py`, so new
  storage/model errors should extend `TaskliError` to get free CLI handling.

## Testing conventions

- `tests/unit/` mirrors `src/taskli/` (`test_cli.py`, `test_models.py`,
  `test_storage.py`, `test_migrations.py`), grouped into one
  `Test<Feature>` class per command/
  behavior area (see `TestAdd` in `test_cli.py`).
- The `taskli_env` fixture (`tests/conftest.py`) points `TASKLI_PATH` at
  `tmp_path` via `monkeypatch` — always use it (or an equivalent override)
  in any test touching storage, so tests never read/write the real
  `~/.taskli`.
- CLI tests call `taskli.cli.main(argv)` directly and assert on its return
  code plus `capsys` output, rather than shelling out to the `tk`/`taskli`
  binary.
- `tests/resources/` holds JSON fixtures (e.g. the legacy vs. v1 list /
  config files the migration tests exercise), loaded through
  `tests/utils.py`'s `resource_text` / `resource_dict` helpers rather
  than inlined in the test modules.
