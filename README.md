# Taskli

[![CI](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml)
[![Release](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Type checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)

Simple CLI for tracking task lists.

```bash
$ task -a "Buy groceries"
added #1 to 'inbox'.

$ task work -a "Finish report"
added #1 to 'work'.

$ task work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ task work --all
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
- **Explicit, flag-based grammar.** `task work -a "Ship it"` — every
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

For most users, `pipx` provides an isolated installation and makes the `task` command available globally without affecting your other Python environments.

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

For a "global" install (i.e., ability to use `task` in the terminal across local environments), you will need to use `pipx`:

```bash
# after doing the above...
pip install pipx
pipx install . --force
```

## Usage

```
task [LIST] [FLAG ...]
```

`LIST` is optional and defaults to `inbox` (or your configured
`default_list`). Every action — adding, viewing, editing, deleting a
whole list, and so on — is an explicit flag, never a bare word:

```bash
task -a "buy milk"                       # == task inbox -a "buy milk"
task work -a "finish report" -p high -t urgent
task work                                # view work's items
task                                     # view inbox's items
task groceries --new-list -c teal        # create an empty, teal-colored list
```

Lists can be nested into **sublists** by separating names with a `.`, e.g.
`work.meetings`. See [Sublists](#sublists) below for how nesting, grouped
views, and cascading deletes work.

## Commands overview

```bash
task -a "Buy groceries"    # == task inbox -a "Buy groceries"
task -d 1                  # == task inbox -d 1
```

Lists other than `inbox` don't need to be created up front — `-a/--add`
auto-creates the target list (and any missing parent, for a nested name)
the first time you use it. Use `--new-list` only when you want to set a
color at creation time or create an empty list ahead of use. Use
`task --all` to print every list's items in one shot, instead of viewing
each list one at a time; `task work --all` scopes that same recursive
view to `work` and its descendants instead of every list.

### Nested lists

Join names with a `.` to nest a list under another, e.g. `work.meetings`.

- Nesting is capped at **2 sublist levels** (3 name segments total —
  `work.meetings.standup` is fine, a fourth segment is rejected):

  ```bash
  $ task work.meetings.standup.daily --new-list
  error: 'work.meetings.standup.daily' is nested too deep (max 2 sublist levels).
  ```

- Creating or adding to a sublist **auto-creates any missing parent**:

  ```bash
  $ task work.meetings -a "Review roadmap"
  added #1 to 'work.meetings'.
  ```

- The default view shows only that list's own items. Add `--all` to
  recurse through **every descendant at any depth**, not just direct
  children, rendered as one tree (see the transcript above).
- `--rm-list` on a parent **cascades**: it names every descendant in a
  single confirmation prompt and deletes them all together.

  ```bash
  $ task work --rm-list
  delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
  deleted list 'work' and 1 sublist(s).
  ```

### Priorities & tags

Items have one of three priorities — `low`, `medium` (default), `high` —
and any number of free-form tags:

```bash
task work -a "Ship v2" -p high -t urgent -t release
```

> [!NOTE]
> There's no built-in "urgent" priority — use it as a tag instead, as above.

`-t/--tag` (used with `-a`/`-e`) **sets** tags on an item. Filtering a
view by tag uses a separate flag, `-f/--filter-tag`, which takes a
single tag, matched exactly and case-insensitively, and applies to
every visible sublist section too:

```bash
$ task work -f urgent
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text        ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ Prep slides │ high     │ urgent │
└────┴──────┴─────────────┴──────────┴────────┘
```

> [!IMPORTANT]
> `-e/--edit`'s `-t/--tag` **replaces** an item's entire tag list — it
> does not add to the existing tags. Omit `-t` entirely to leave tags
> untouched. With repeated `-a`, `-p`/`-t` bind to the **nearest
> preceding** `-a` only — each new `-a` starts fresh at the configured
> default priority and no tags unless given its own `-p`/`-t`:
>
> ```bash
> task work -a "low-pri item" -p low -t someday -a "high-pri item" -p high -t urgent
> ```

### Colors

Lists can carry one of 16 named colors, set via `-c/--color` on
`--new-list` or `--edit-list`:

<details>
<summary>All 16 color choices</summary>

`white`, `red`, `coral`, `orange`, `yellow`, `lime`, `green`, `teal`, `cyan`,
`sky`, `blue`, `indigo`, `violet`, `purple`, `magenta`, `pink`

</details>

```bash
task groceries --new-list -c teal
task work --edit-list -c coral
```

A list created without `-c` has no color set. `--new-list`'s color is
optional; `--edit-list`'s `-c` is **required** — there's no way to edit a
list without also specifying a color.

## Routing grammar

`task [LIST] [FLAG] [MODIFIERS]` — `LIST` is an optional positional
(defaults to `inbox`); every action, including list management, is an
explicit flag (`-a`, `-d`, `-u`, `-r`, `-e`, `--tags`, `--prune`,
`--new-list`, `--rm-list`, `--edit-list`, `--config`, `--lists`,
`--all`), never a bare word — a list can be named anything, including
`add` or `config`, with no collision risk.

| You type | Resolves to | Why |
|---|---|---|
| `task` | `task inbox` (view) | no args → default list, default (view) action |
| `task -d 5` | `task inbox -d 5` | no `LIST` given → `inbox` |
| `task work` | view `work` | no action flag → default view |
| `task work -a "Ship it"` | add "Ship it" to `work` | explicit `-a` |
| `task -a "x" -a "y"` | adds two items to `inbox` | `-a` is repeatable |
| `task buy milk` | **error** (exit 2, unrecognized argument) | `buy` fills `LIST`; `milk` has nowhere to go |
| `task "buy milk"` | **error** (exit 1, list not found) | one token fills `LIST` as the literal name `buy milk`, which doesn't exist |

A list-management flag and an item-action flag can be combined in one
call — the list operation runs first, then the item action runs against
the same list:

```bash
task groceries --new-list -c teal -a "buy milk"
task work --edit-list -c red -d 1
```

> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers — `-r`
> and `--prune` renumber the remaining items starting from 1. Don't
> hardcode an ID across a sequence of commands that also removes items.
> Removing several ids in one `-r` call (`task work -r 2 4`) reindexes
> once at the end, not once per id, so all the ids you pass are
> resolved against the list's state before that call.

Every example below builds on the same running session — `TASKLI_PATH`
starts empty.

| Flag | Purpose | Example |
|---|---|---|
| `-a, --add TEXT` | Add an item to a list (repeatable) | `task work -a "Ship v2" -p high` |
| `-d, --done ID...` | Mark one or more items done (combinable with `-u`/`-r`) | `task work -d 1 3` |
| `-u, --undone ID...` | Mark one or more items not done (combinable with `-d`/`-r`) | `task work -u 2` |
| `-e, --edit ID` | Change an item's text, priority, or tags | `task work -e 1 --text "Ship v2.1"` |
| `-r, --rm ID...` | Remove one or more items (combinable with `-d`/`-u`) | `task work -r 2 4` |
| `--tags` | List distinct tags used in a list | `task work --tags` |
| `--prune` | Remove all done items from a list | `task work --prune` |
| `--lists` | Show every list, nested as a tree | `task --lists` |
| `--all` | Modifier: include descendants in the default view. Without `LIST`, shows every list's items | `task work --all` / `task --all` |
| `--new-list` | Create LIST as an empty list | `task groceries --new-list -c teal` |
| `--edit-list` | Change LIST's color | `task work --edit-list -c coral` |
| `--rm-list` | Delete LIST and its sublists | `task groceries --rm-list` |
| `--config [KEY] [VALUE]` | View or edit config settings | `task --config default_priority high` |

There's no explicit view flag — the absence of any item-action flag is
what shows a list's items. `--lists`/`--config` ignore `LIST` entirely;
`--all` uses `LIST` when given (scoping the recursive view to that
list's subtree) and falls back to every list only when `LIST` is
omitted; every other flag runs against `LIST`, which defaults to
`inbox`.

## Workflows

<details>
<summary><strong>Morning triage in the inbox</strong></summary>

```bash
$ task -a "Buy groceries"
added #1 to 'inbox'.

$ task -a "Call the dentist" -p high
added #2 to 'inbox'.

$ task -d 1
marked #1 done in 'inbox'.

$ task inbox -f urgent
inbox
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text            ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴─────────────────┴──────────┴──────┘

$ task --prune
pruned 1 item(s) from 'inbox'.
```

### `--new-list`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ task groceries --new-list
created list 'groceries'.

$ task work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ task work -a "Finish report" -p high -t urgent
added #1 to 'work'.

$ task --lists
groceries
work
  meetings
```

Note `work` didn't need to exist first — creating `work.meetings` silently
created the empty `work` parent too.

### `--rm-list`

Deletes a list and everything in it, after a confirmation prompt. If the
list has sublists, they're listed in the prompt and deleted along with it
— see [Sublists](#sublists).

```
$ task groceries --rm-list
delete list 'groceries' and all its items? [y/N]: y
deleted list 'groceries'.

$ task work --rm-list
delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
deleted list 'work' and 1 sublist(s).

$ task --lists
no lists yet.
```

### `-a/--add`

Adds an item to a list, creating the list (and, for a sublist name, any
missing parent lists) if it doesn't exist yet.

```
$ task work -a "finish report" -p high -t urgent
added #1 to 'work'.

$ task work -a "buy milk" -t errand
added #2 to 'work'.
```

Repeat `-a` to add several items in one call — each gets its own
`-p`/`-t` bound to the `-a` immediately before it (see
[Priorities & tags](#priorities--tags) for the exact binding rule).

### Default view

Shows a list's own items. This is what runs when you give just a list
name (`task work`) with no item-action flag. Sublists are **not**
included by default — add `--all` to also render each descendant as its
own titled section right after the parent's table — see
[Sublists](#sublists) for the grouped view and how `-t/--tag` interacts
with it.

```
$ task work
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
│  2 │      │ buy milk      │ medium   │ errand │
└────┴──────┴───────────────┴──────────┴────────┘
```

### `-d/--done` / `-u/--undone`

Marks an item done or not done by its `ID` (the leftmost column in the
table above).

```bash
$ task work -d 1
marked #1 done in 'work'.

$ task work --prune
pruned 1 item(s) from 'work'.

$ task work
                 work
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘
```

`-d`, `-u`, and `-r` each take one or more ids and can be combined in a
single call — done ids are applied first, then undone, then removed
last:

```bash
$ task work -a "a" -a "b" -a "c" -a "d" -a "e"
added #1 to 'work'.
added #2 to 'work'.
added #3 to 'work'.
added #4 to 'work'.
added #5 to 'work'.

$ task work -d 1 3 -u 2 -r 5
marked #1 done in 'work'.
marked #3 done in 'work'.
marked #2 not done in 'work'.
removed #5 from 'work'.
```

If any id doesn't exist, the valid ones are still applied and saved —
only the bad id's line reports an error, and the whole command exits 1:

```bash
$ task work -d 1 99
marked #1 done in 'work'.
error: no item with id 99 in list 'work'.
```

## Sublists

Any list name can be nested under another by joining names with a `.`,
e.g. `work.meetings` is a sublist of `work`. Nesting is capped at **2
sublist levels** (3 name segments total, e.g. `work.meetings.notes`) —
going deeper raises a clean error instead of silently truncating:

```
$ task work.meetings.notes --new-list
created list 'work.meetings.notes'.

$ task work.meetings.notes.extra --new-list
error: 'work.meetings.notes.extra' is nested too deep (max 2 sublist levels).
```

**Creating a sublist auto-creates missing parents.** `task work.meetings
--new-list` (or `task work.meetings -a ...`) creates an empty `work`
first if it doesn't already exist — you never have to create the chain
top-down by hand.

<details>
<summary><strong>List-scoped actions</strong> (<code>task [LIST] [FLAG] [MODIFIERS]</code>, LIST defaults to <code>inbox</code>)</summary>

Exactly one item-action flag may be given per invocation (they're
mutually exclusive); omitting one defaults to the view action.

| Flag | Modifiers | Notes |
|---|---|---|
| `-a, --add TEXT...` | `-t, --tag TAG` (repeatable) · `-p, --priority {low,medium,high}` (default `medium`) | Repeatable — each `-a` adds one item. Auto-creates `LIST` (and missing ancestors) if needed. Modifiers apply to every item added in the same invocation. |
| `-d, --done ID` | — | `ID` is an integer. |
| `-u, --undone ID` | — | |
| `-r, --rm ID` | — | Remaining items are renumbered starting from 1. |
| `-e, --edit ID` | `--text TEXT` · `-p, --priority {low,medium,high}` · `-t, --tag TAG` (repeatable) | Only the flags you pass are changed. `-t` **replaces** the whole tag list. |
| `--tags` | — | Distinct tags in `LIST`, one per line, sorted. |
| `--prune` | — | Removes every done item; reports how many were removed. |

Passing a modifier that doesn't apply to the chosen action (e.g.
`-t`/`-p` with `-d`, or `-f` with `-a`) is an argument error (exit 2).

The default view shows only `LIST`'s own items; add `--all` to also
render each descendant as its own titled section:

```
$ task work --all
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
                  work.meetings
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text             ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
│  1 │      │ sync with design │ high     │      │
└────┴──────┴──────────────────┴──────────┴──────┘
```

Section headers show the **full dotted name** (`work.meetings`, not just
`meetings`), so you can act on that item directly with
`task work.meetings -d 1`.

**A tag filter applies to every section.** `task work --all -f urgent`
filters `work`'s own items *and* each sublist's items by the same tag; a
sublist with no matches is dropped from the output entirely. Without
`--all`, `-f` only filters `work`'s own items, since no sublists are
shown:

```
$ task work --all -f urgent
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
```

**Deleting a list cascades to its sublists.** `task --rm-list` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ task work --rm-list
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ task --lists
no lists yet.
```

The configured `default_list` (`inbox` by default) is created
automatically the first time it's read. Any other list is created
automatically the first time you `-a/--add` to it.

</details>

## Configuration

Taskli keeps a single settings file at `$TASKLI_PATH/.taskli.json`
(next to your list files, `~/.taskli/.taskli.json` by default). Edit it
by hand, or through `task --config`:

```
$ task --config
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

$ task --config default_priority
medium

$ task --config default_priority high
set 'default_priority' to 'high'.
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `auto_prune` | `true`/`false` | `false` | Automatically removes done items whenever a list is viewed (`task LIST`/`task --all`), same effect as `--prune`. |
| `sublist_delimiter` | one of `.`, `/`, `-`, `\|` | `.` | The delimiter used when typing or displaying nested list names. Storage always uses `.` internally, so lists created under one delimiter are unaffected by later changing it, but existing nested list names containing the old delimiter character may stop resolving as sublists until renamed. Like `.` today, the configured character can't appear literally inside a single segment's name — it always denotes a nesting boundary (e.g. with `-`, `my-list` is parsed as sublist `list` under `my`). |
| `default_list` | string | `inbox` | The list used when `LIST` is omitted, and the list auto-created on first read. |
| `default_sort` | `tags`/`priority`/`created_at` | `created_at` | Sort key applied to items shown by `task LIST`/`task --all`. |
| `default_priority` | `low`/`medium`/`high` | `medium` | Priority used for new items added via `-a` when `-p` is omitted. |
| `default_color` | color name (see [Colors](#colors)) | `white` | Default color for lists created via `--new-list` when `-c` is omitted. |

An unknown key or an invalid value for a key is an error (exit 1):

```
$ task --config nope
error: 'nope' is not a config key.

$ task --config auto_prune sortof
error: 'sortof' is not a valid value for 'auto_prune'.
```
