# Taskli

[![CI](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml)
[![Release](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Type checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)

Simple CLI for tracking task lists.

```bash
$ tk -a "Buy groceries"
added #1 to 'inbox'.

$ tk work -a "Finish report"
added #1 to 'work'.

$ tk work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ tk work --all
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
│  1 │      │ Finish report │ medium   │      │
└────┴──────┴───────────────┴──────────┴──────┘
└── meetings
    ┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
    ┃ ID ┃ Done ┃ Text           ┃ Priority ┃ Tags ┃
    ┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
    │  1 │      │ Review roadmap │ medium   │      │
    └────┴──────┴────────────────┴──────────┴──────┘
```

## Table of contents

- [Why Taskli](#why-Taskli)
- [Installation](#installation)
- [Usage](#usage)
- [Commands overview](#commands-overview)
- [Routing grammar](#routing-grammar)
- [Workflows](#workflows)
- [Sublists](#sublists)
- [Configuration](#configuration)

## Why Taskli

- **Nested lists.** `work.meetings` is a sublist of `work`, up to two levels
  deep. Parents auto-create on demand; `--all` and deleting a list both
  reach every descendant.
- **Zero config.** Each list is one JSON file, readable, greppable, and
  backed up with any tool you already have.
- **Explicit, flag-based grammar.** `tk work -a "Ship it"` — every
  action is an unambiguous flag, so it never guesses whether you meant
  a list name or item text. See [routing grammar](#routing-grammar).
- **Colorized, tree-rendered output** via [`rich`](https://github.com/Textualize/rich):
  priorities are color-coded, lists can be given their own accent color, and
  nested lists render as an actual tree.

## Installation

> [!NOTE]
> **Taskli** isn't published to PyPI yet. Install it directly from GitHub.

Requires **Python 3.11+**.

### Install with `pipx` (recommended)

For most users, `pipx` provides an isolated installation and makes the `tk`
command available globally without affecting your other Python
environments.

```bash
pipx install git+https://github.com/calvinmcelvain/taskli.git
```

### Install from source

Clone the repository and install it in editable mode for local development.

```bash
git clone https://github.com/calvinmcelvain/taskli.git
cd taskli

python3 -m venv .venv
source .venv/bin/activate      # Git Bash on Windows: source .venv/Scripts/activate
pip install -e ".[dev]"
```

### Global install

For a "global" install (i.e., ability to use `tk` in the terminal across local environments), you will need to use `pipx`:

```bash
# after doing the above...
pip install pipx
pipx install . --force
```

## Usage

```
tk [LIST] [FLAG ...]
```

`LIST` is optional and defaults to `inbox` (or your configured
`default_list`). Every action — adding, viewing, editing, deleting a
whole list, and so on — is an explicit flag, never a bare word:

```bash
tk -a "buy milk"                          # == tk inbox -a "buy milk"
tk work -a "finish report" -p high --tag urgent
tk work                                   # view work's items
tk                                        # view inbox's items
tk groceries --new --color teal           # create an empty, teal-colored list
```

Lists can be nested into **sublists** by separating names with a `.`, e.g.
`work.meetings`. See [Sublists](#sublists) below for how nesting, grouped
views, and cascading deletes work.

> [!NOTE]
> The package also installs a `taskli` entry point identical to `tk` — use
> whichever you prefer; the examples below all use the shorter `tk`.

## Commands overview

```bash
tk -a "Buy groceries"    # == tk inbox -a "Buy groceries"
tk -d 1                  # == tk inbox -d 1
```

Lists other than `inbox` don't need to be created up front — `-a/--add`
auto-creates the target list (and any missing parent, for a nested name)
the first time you use it. Use `--new` only when you want to set a
color at creation time or create an empty list ahead of use. Use
`tk --all` to print every list's items in one shot, instead of viewing
each list one at a time; `tk work --all` scopes that same recursive
view to `work` and its descendants instead of every list.

### Nested lists

Join names with a `.` to nest a list under another, e.g. `work.meetings`.

- Nesting is capped at **2 sublist levels** (3 name segments total —
  `work.meetings.standup` is fine, a fourth segment is rejected):

  ```bash
  $ tk work.meetings.standup.daily --new
  error: 'work.meetings.standup.daily' is nested too deep (max 2 sublist levels).
  ```

- Creating or adding to a sublist **auto-creates any missing parent**:

  ```bash
  $ tk work.meetings -a "Review roadmap"
  added #1 to 'work.meetings'.
  ```

- The default view shows only that list's own items. Add `--all` to
  recurse through **every descendant at any depth**, not just direct
  children, rendered as one tree (see the transcript above).
- `--delete` on a parent **cascades**: it names every descendant in a
  single confirmation prompt and deletes them all together.

  ```bash
  $ tk work --delete
  delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
  deleted list 'work' and 1 sublist(s).
  ```

### Priorities & tags

Items have one of three priorities — `low`, `medium` (default), `high` —
and any number of free-form tags:

```bash
tk work -a "Ship v2" -p high --tag urgent --tag release
```

> [!NOTE]
> There's no built-in "urgent" priority — use it as a tag instead, as above.

`--tag` is dual-purpose: with `-a`/`-e` it **sets** (`-e`: replaces) an
item's tags; with no other option given it instead **filters** the default
view by a single tag, matched exactly and case-insensitively, applying to
every visible sublist section too:

```bash
$ tk work --tag urgent
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Done ┃ Text        ┃ Priority ┃ Tags            ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│  1 │      │ Ship v2     │ high     │ urgent, release │
└────┴──────┴─────────────┴──────────┴─────────────────┘
```

`-p/--priority` works the same way — set on `-a`/`-e`, filter on the
default view.

> [!IMPORTANT]
> `-e/--edit`'s `--tag` **replaces** an item's entire tag list — it does
> not add to the existing tags. Use `--add-tag` instead to append one or
> more tags without disturbing the rest:
>
> ```bash
> $ tk work -e 1 --add-tag release
> updated #1 in 'work'.
> ```
>
> Passing `-p`/`--tag` alongside repeated `-a` flags applies that
> priority/tags to **every** item added in the same invocation.

### Colors

Lists can carry one of 16 named colors, set via `--color` — as a modifier
on `--new`, or on its own to recolor an existing list:

<details>
<summary>All 16 color choices</summary>

`white`, `red`, `coral`, `orange`, `yellow`, `lime`, `green`, `teal`, `cyan`,
`sky`, `blue`, `indigo`, `violet`, `purple`, `magenta`, `pink`

</details>

```bash
tk groceries --new --color teal
tk work --color coral
```

A list created without `--color` has no color set. `--new`'s color is
optional; giving bare `--color` (with no other list-management flag) is
what recolors an existing list.

## Routing grammar

`tk [LIST] [FLAG] [MODIFIERS]` — `LIST` is an optional positional
(defaults to `inbox`); every action, including list management, is an
explicit flag (`-a`, `-d`, `-u`, `-rm`, `-e`, `-mv`, `--copy`, `--prune`,
`--new`, `--delete`, `--color`, `--config`, `--lists`, `--all`), never a bare
word — a list can be named anything, including `add` or `config`, with no
collision risk.

| You type | Resolves to | Why |
|---|---|---|
| `tk` | `tk inbox` (view) | no args → default list, default (view) action |
| `tk -d 5` | `tk inbox -d 5` | no `LIST` given → `inbox` |
| `tk work` | view `work` | no action flag → default view |
| `tk work -a "Ship it"` | add "Ship it" to `work` | explicit `-a` |
| `tk -a "x" -a "y"` | adds two items to `inbox` | `-a` is repeatable |
| `tk buy milk` | **error** (exit 2, unrecognized argument) | `buy` fills `LIST`; `milk` has nowhere to go |
| `tk "buy milk"` | **error** (exit 1, list not found) | one token fills `LIST` as the literal name `buy milk`, which doesn't exist |

Every command falls into exactly one of four **option groups**: list
management (`-n/--new`, `--delete`, `-l/--lists`, `--prune`), item action
(`-a`, `-rm`, `-d`, `-u`, `-e`), config (`--config`), or the default view
(nothing from the other three given). At most one group applies per
call — if more than one is given, Taskli picks by fixed priority (list
management, then item action, then config, then the view) and prints a
warning naming which one ran and which were ignored, rather than erroring
or chaining them together:

```bash
$ tk groceries --new -a "buy milk"
warning: multiple option groups given; using list management ('new'), ignoring item action.
created list 'groceries'.
groceries
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘
```

The list is created but "buy milk" is never added — run the two as
separate calls if you want both.

> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers —
> `-rm` and `--prune` renumber the remaining items starting from 1. Don't
> hardcode an ID across a sequence of commands that also removes items.

Every example below builds on the same running session — `TASKLI_PATH`
starts empty.

| Flag | Purpose | Example |
|---|---|---|
| `-a, --add TEXT` | Add an item to a list (repeatable) | `tk work -a "Ship v2" -p high` |
| `-d, --done ID...` | Mark one or more items done | `tk work -d 1 2` |
| `-u, --undone ID...` | Mark one or more items not done | `tk work -u 1 2` |
| `-e, --edit ID` | Change an item's text, priority, or tags | `tk work -e 1 --text "Ship v2.1"` |
| `-mv, --move TARGET_LIST [ID...]` | Move item(s) from `LIST` to `TARGET_LIST` (creates `TARGET_LIST` if missing) | `tk work -mv groceries 1 2` |
| `--copy TARGET_LIST [ID...]` | Copy item(s) from `LIST` to `TARGET_LIST`, leaving `LIST` unchanged | `tk work --copy groceries 1 2` |
| `-rm, --remove ID...` | Remove one or more items | `tk work -rm 1 2` |
| `--prune` | Remove all done items from `LIST` (or `LIST` + its descendants with `--all`) | `tk work --prune` / `tk work --prune --all` |
| `-l, --lists` | Show every list, nested as a tree | `tk --lists` |
| `--all` | Modifier: include descendants in the default view or `--prune`. Without `LIST`, the default view shows every list's items and `--prune` removes done items from every list | `tk work --all` / `tk --all` / `tk --prune --all` |
| `-n, --new` | Create LIST as an empty list | `tk groceries --new --color teal` |
| `--color` | Recolor an existing LIST (or set the initial color on `--new`) | `tk work --color coral` |
| `--delete` | Delete LIST and its sublists | `tk groceries --delete` |
| `--config [KEY] [VALUE]` | View or edit config settings | `tk --config default_priority high` |

There's no explicit view flag — the absence of any item-action flag is
what shows a list's items. `--lists`/`--config` ignore `LIST` entirely;
`--all` uses `LIST` when given (scoping the recursive view to that
list's subtree) and falls back to every list only when `LIST` is
omitted; every other flag runs against `LIST`, which defaults to
`inbox`.

A batch of ids (`-d`/`-u`/`-rm`/`-mv`/`--copy`) uses **partial success**: a
missing id prints its own warning and the rest of the batch still runs,
and the whole call exits 1 if any id failed —

```bash
$ tk work -d 1 99
marked #1 done in 'work'.
warning: no item with id 99 in list 'work'.
```

## Workflows

<details>
<summary><strong>Morning triage in the inbox</strong></summary>

```bash
$ tk -a "Buy groceries"
added #1 to 'inbox'.

$ tk -a "Call the dentist" -p high
added #2 to 'inbox'.

$ tk -d 1
marked #1 done in 'inbox'.

$ tk inbox --tag urgent
inbox
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘

$ tk --prune
pruned 1 item(s) from 'inbox'.
```

### `--new`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ tk groceries --new
created list 'groceries'.

$ tk work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ tk work -a "Finish report" -p high --tag urgent
added #1 to 'work'.

$ tk --lists
groceries
work
  meetings
```

Note `work` didn't need to exist first — creating `work.meetings` silently
created the empty `work` parent too.

### `--delete`

Deletes a list and everything in it, after a confirmation prompt. If the
list has sublists, they're listed in the prompt and deleted along with it
— see [Sublists](#sublists).

```
$ tk groceries --delete
delete list 'groceries' and all its items? [y/N]: y
deleted list 'groceries'.

$ tk work --delete
delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
deleted list 'work' and 1 sublist(s).

$ tk --lists
no lists yet.
```

### `-a/--add`

Adds an item to a list, creating the list (and, for a sublist name, any
missing parent lists) if it doesn't exist yet.

```
$ tk work -a "finish report" -p high --tag urgent
added #1 to 'work'.

$ tk work -a "buy milk" --tag errand
added #2 to 'work'.
```

### Default view

Shows a list's own items. This is what runs when you give just a list
name (`tk work`) with no item-action flag. Sublists are **not**
included by default — add `--all` to also render each descendant as its
own titled section right after the parent's table — see
[Sublists](#sublists) for the grouped view and how `--tag` interacts
with it.

```
$ tk work
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
│  2 │      │ buy milk      │ medium   │ errand │
└────┴──────┴───────────────┴──────────┴────────┘
```

### `-d/--done` / `-u/--undone`

Marks one or more items done or not done by their `ID` (the leftmost
column in the table above); both are repeatable in a single call.

```bash
$ tk work -d 1
marked #1 done in 'work'.

$ tk work --prune
pruned 1 item(s) from 'work'.

$ tk work
work
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘
```

### `-mv/--move` / `--copy`

Moves or copies one or more items into another list by `ID`, auto-creating
the target list (and any missing parent, for a nested name) the same way
`-a/--add` does. Omit every `ID` to act on the whole list. `--copy` leaves
the source list untouched; `-mv/--move` removes the item(s) from the
source.

```bash
$ tk work -mv groceries 1
moved #1 from 'work' to 'groceries'.

$ tk work --copy errands
copied #1 from 'work' to 'errands'.
```

Both share the same partial-success batch semantics as `-d`/`-u`/`-rm` —
see [Routing grammar](#routing-grammar).

A copied or moved item keeps its original creation time rather than
getting a fresh one, so under `default_sort=created_at` it sorts into the
target list by that original time instead of always landing last. If the
target already has newer items, this can shift their `ID`s.

## Sublists

Any list name can be nested under another by joining names with a `.`,
e.g. `work.meetings` is a sublist of `work`. Nesting is capped at **2
sublist levels** (3 name segments total, e.g. `work.meetings.notes`) —
going deeper raises a clean error instead of silently truncating:

```
$ tk work.meetings.notes --new
created list 'work.meetings.notes'.

$ tk work.meetings.notes.extra --new
error: 'work.meetings.notes.extra' is nested too deep (max 2 sublist levels).
```

**Creating a sublist auto-creates missing parents.** `tk work.meetings
--new` (or `tk work.meetings -a ...`) creates an empty `work`
first if it doesn't already exist — you never have to create the chain
top-down by hand.

<details>
<summary><strong>List-scoped actions</strong> (<code>tk [LIST] [FLAG] [MODIFIERS]</code>, LIST defaults to <code>inbox</code>)</summary>

Exactly one option group may apply per invocation — see
[Routing grammar](#routing-grammar) for what happens if more than one is
given. Omitting an item-action flag defaults to the view action.

| Flag | Modifiers | Notes |
|---|---|---|
| `-a, --add TEXT...` | `--tag TAG` (repeatable) · `-p, --priority {low,medium,high}` (default `medium`) | Repeatable — each `-a` adds one item. Auto-creates `LIST` (and missing ancestors) if needed. Modifiers apply to every item added in the same invocation. |
| `-d, --done ID...` | — | One or more integer ids; partial success on a bad id (see [Routing grammar](#routing-grammar)). |
| `-u, --undone ID...` | — | Same batch behavior as `-d`. |
| `-rm, --remove ID...` | — | Same batch behavior as `-d`. Remaining items are renumbered starting from 1. |
| `-e, --edit ID` | `-t, --text TEXT` · `-p, --priority {low,medium,high}` · `--tag TAG` (repeatable, replaces) · `--add-tag TAG` (repeatable, appends) | Only the flags you pass are changed. `--tag` and `--add-tag` can't be combined in the same call. |
| `-mv, --move TARGET_LIST [ID...]` | — | Moves item(s) into `TARGET_LIST`, auto-creating it (and missing ancestors) if needed. Omit `ID` to move every item. Same batch/partial-success behavior as `-d`. |
| `--copy TARGET_LIST [ID...]` | — | Same as `-mv`, but leaves the source list unchanged. |
| `--prune` | `--all` | Removes every done item from `LIST`. With `--all`, also prunes every descendant of `LIST`; without a `LIST` (falls back to `default_list`), `--all` prunes every list instead. Reports how many were removed, per list. |

Passing a modifier that doesn't apply to the chosen action (e.g.
`--tag`/`-p` with `-d`, or `--all` with `-a`) is an argument error (exit 2).

The default view shows only `LIST`'s own items; add `--all` to also
render each descendant as its own titled section:

```
$ tk work --all
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
└── meetings
    ┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
    ┃ ID ┃ Done ┃ Text             ┃ Priority ┃ Tags ┃
    ┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
    │  1 │      │ sync with design │ high     │      │
    └────┴──────┴──────────────────┴──────────┴──────┘
```

Section headers show the **full dotted name** (`work.meetings`, not just
`meetings`), so you can act on that item directly with
`tk work.meetings -d 1`.

**A tag or priority filter applies to every section.** `tk work --all
--tag urgent` filters `work`'s own items *and* each sublist's items by
the same tag (`-p` works the same way); a sublist with no matches still
renders as its own section, just with an empty table. Without `--all`,
the filter only applies to `work`'s own items, since no sublists are
shown:

```
$ tk work --all --tag urgent
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
└── meetings
    ┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
    ┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
    ┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
    └────┴──────┴──────┴──────────┴──────┘
```

**Deleting a list cascades to its sublists.** `--delete` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ tk work --delete
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ tk --lists
no lists yet.
```

The configured `default_list` (`inbox` by default) is created
automatically the first time it's read. Any other list is created
automatically the first time you `-a/--add` to it.

</details>

## Configuration

Taskli keeps a single settings file at `$TASKLI_PATH/.taskli.json`
(next to your list files, `~/.taskli/.taskli.json` by default). Edit it
by hand, or through `tk --config`:

```
$ tk --config
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Key               ┃ Value      ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ auto_prune        │ False      │
│ sublist_delimiter │ .          │
│ default_list      │ inbox      │
│ default_sort      │ created_at │
│ default_priority  │ medium     │
│ default_color     │ #F8FAFC    │
└───────────────────┴────────────┘

$ tk --config default_priority
medium

$ tk --config default_priority high
set 'default_priority' to 'high'.
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `auto_prune` | `true`/`false` | `false` | Automatically removes done items whenever a list is viewed (`tk LIST`/`tk --all`), same effect as `--prune`. |
| `sublist_delimiter` | one of `.`, `/`, `-`, `\|` | `.` | The delimiter used when typing or displaying nested list names. Storage always uses `.` internally, so lists created under one delimiter are unaffected by later changing it, but existing nested list names containing the old delimiter character may stop resolving as sublists until renamed. Like `.` today, the configured character can't appear literally inside a single segment's name — it always denotes a nesting boundary (e.g. with `-`, `my-list` is parsed as sublist `list` under `my`). |
| `default_list` | string | `inbox` | The list used when `LIST` is omitted, and the list auto-created on first read. |
| `default_sort` | `tags`/`priority`/`created_at` | `created_at` | Sort key applied to items shown by `tk LIST`/`tk --all`. |
| `default_priority` | `low`/`medium`/`high` | `medium` | Priority used for new items added via `-a` when `-p` is omitted. |
| `default_color` | color name (see [Colors](#colors)) | `white` | Default color for lists created via `--new` when `--color` is omitted. |

An unknown key or an invalid value for a key is an error (exit 1):

```
$ tk --config nope
error: 'nope' is not a config key.

$ tk --config auto_prune sortof
error: 'sortof' is not a valid value for 'auto_prune'.
```
