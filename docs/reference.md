# Command reference

```
tk [LIST] [FLAG ...]
```

`LIST` is optional and defaults to `inbox` (or your configured
[`default_list`](config.md)). Every action is an explicit flag, never a bare
word, so a list can be named anything, including `add` or `config`.

`taskli` is an alias for `tk`; use whichever you prefer.

## All flags

| Flag | Purpose | Example |
|---|---|---|
| `-a, --add TEXT` | Add an item (repeatable). Creates the list if needed. | `tk work -a "Ship v2" -p high` |
| `-d, --done ID...` | Mark items done. | `tk work -d 1 2` |
| `-i, --in-progress ID...` | Mark items in progress. | `tk work -i 3` |
| `-u, --undone ID...` | Reset items to not started (from done or in progress). | `tk work -u 1` |
| `-rm, --remove ID...` | Remove items (and their subtasks). | `tk work -rm 4` |
| `-e, --edit ID` | Change an item's text, priority, tags, due date, description, or parent. | `tk work -e 1 -t "Ship v2.1"` |
| `-D, --details ID` | Show one item in full (description, timestamps, subtasks). | `tk work -D 1` |
| `-mv, --move TARGET [ID...]` | Move items to another list (all items if no ID). | `tk work -mv later 2 3` |
| `--copy TARGET [ID...]` | Copy items to another list, leaving the source alone. | `tk work --copy later 2` |
| `--prune` | Remove done items from `LIST` (`--all`: and its sublists, or every list when no `LIST`). | `tk work --prune` |
| `-n, --new` | Create an empty list. | `tk groceries --new --color green` |
| `--color [COLOR]` | Set the color at `--new`, or recolor an existing list. | `tk work --color coral` |
| `--rename NEW` | Rename a list and its sublists. | `tk work --rename job` |
| `--delete` | Delete a list and its sublists (asks first). | `tk groceries --delete` |
| `-l, --lists` | Show every list as a tree. | `tk --lists` |
| `--agenda [WINDOW]` | Everything due across all lists, chronologically. | `tk --agenda 3` |
| `--config [KEY [VALUE]]` | View or change [settings](config.md). | `tk --config default_sort priority` |
| `--migrate` | Upgrade list and config files to the current schema. | `tk --migrate` |
| `--version` | Print the installed version. | `tk --version` |
| `--path` | Print the storage directory in use. | `tk --path` |

### Modifiers

Modifiers layer on top of an action.

| Modifier | Meaning |
|---|---|
| `-p, --priority {low,medium,high}` | Set on `-a`/`-e`; filter on the default view. |
| `--tag TAG` (repeatable) | Set on `-a`; **replace** tags on `-e`; filter on the default view. |
| `--add-tag TAG` (repeatable) | Append tags on `-e`. Cannot be combined with `--tag`. |
| `--due WHEN` | Set on `-a`/`-e` (one value); filter on the default view (repeatable, OR-combined). See [due dates](tasks.md#due-dates). |
| `--today` | Default view only: shorthand for `--due today`. |
| `--undated` | Default view only: shorthand for `--due none`. |
| `-t, --text TEXT` | New text for `-e`. |
| `--desc TEXT` | Set a description on `-a`/`-e`; `--desc ""` clears it. |
| `--under PATH` | With `-a`: nest the new item under `PATH`. With `-e`: re-nest the item; `--under ""` moves it to the top level. |
| `--all` | Default view or `--prune`: include sublists (or every list when no `LIST`). |

A modifier that doesn't apply to the chosen action is an argument error
(exit 2), e.g. `tk work -d 1 --tag urgent`.

## `--agenda`

`tk --agenda [WINDOW]` lists not-done items with a due date, across every
list, soonest first. `WINDOW` is one of:

| Window | Shows |
|---|---|
| `today` | Items due today. |
| `week` | Items due within the next 7 days (default, via `agenda_window`). |
| `N` | Items due within the next `N` days. |
| `overdue` | Only items already past due. |

Overdue items are folded into the other windows by default; set
[`agenda_include_overdue`](config.md) to `false` for window-only output.

## Routing grammar

| You type | Resolves to | Why |
|---|---|---|
| `tk` | view `inbox` | no args: default list, default (view) action |
| `tk -d 5` | `tk inbox -d 5` | no `LIST` given: `inbox` |
| `tk work` | view `work` | no action flag: default view |
| `tk work -a "Ship it"` | add to `work` | explicit `-a` |
| `tk -a "x" -a "y"` | add two items to `inbox` | `-a` is repeatable |
| `tk buy milk` | error (exit 2) | `buy` fills `LIST`; `milk` has nowhere to go |
| `tk "buy milk"` | error (exit 1) | one token is the list name `buy milk`, which doesn't exist |

### One option group per call

Every command falls into exactly one group:

1. **List management**: `-n`, `--delete`, `--rename`, `-l`, `--prune`,
   `--migrate`, `--agenda`
2. **Item action**: `-a`, `-rm`, `-d`, `-u`, `-i`, `-e`, `-D`, `-mv`, `--copy`
3. **Config**: `--config`
4. **Default view**: nothing from the groups above

If you give flags from more than one group, taskli runs the first group in
that order, prints a warning naming what ran and what was ignored, and
does **not** chain them:

```console
$ tk groceries --new -a "buy milk"
warning: multiple option groups given; using list management ('new'), ignoring item action.
created list 'groceries'.
```

`-d`, `-i`, `-u`, and `-rm` are the exception: they all belong to one
status op and can be combined in a single call
(`tk work -d 1 -i 2 -rm 3`). The same id can't appear under two of them.

## Batches and partial success

`-d`/`-i`/`-u`/`-rm`/`-mv`/`--copy` take several ids. A missing id prints a
warning and the rest of the batch still runs; the call exits `1` if any id
failed:

```console
$ tk work -d 1 99
marked #1 done in 'work'.
warning: no item with id 99 in list 'work'.
```

## Item ids

An id is an item's **position**, written as a dotted path for subtasks
(`1`, `1.2`, `1.2.1`). Ids are renumbered after `-rm` and `--prune`, so don't
reuse an id across a sequence of commands that removes items.

`-mv` and `--copy` carry an item's whole subtree to the target list (state
reset to not started) and keep the item's original creation time.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | A domain error (missing list or item, invalid value, outdated schema) or any id in a batch failed. |
| `2` | Invalid command line (unknown flag, modifier not valid for the action). |
