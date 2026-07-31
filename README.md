# Taskli

[![CI](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/ci.yml)
[![Release](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml/badge.svg)](https://github.com/calvinmcelvain/taskli/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Type checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)

Simple CLI for tracking todo lists.

```bash
$ todo -a "Buy groceries"
added #1 to 'inbox'.

$ todo work -a "Finish report"
added #1 to 'work'.

$ todo work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ todo work
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
- [Core concepts](#core-concepts)
- [Routing grammar](#routing-grammar)
- [Command overview](#command-overview)
- [Workflows](#workflows)
- [Full command reference](#full-command-reference)
- [Data storage](#data-storage)
- [Development](#development)

## Why Taskli

- **Nested lists.** `work.meetings` is a sublist of `work`, up to two levels
  deep. Parents auto-create on demand; viewing or deleting a list reaches
  every descendant.
- **Zero config.** Each list is one JSON file, readable, greppable, and
  backed up with any tool you already have.
- **Explicit, flag-based grammar.** `todo work -a "Ship it"` — every
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

For most users, `pipx` provides an isolated installation and makes the `todo` command available globally without affecting your other Python environments.

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

For a "global" install (i.e., ability to use `todo` in the terminal across local environments), you will need to use `pipx`:

```bash
# after doing the above...
pip install pipx
pipx install . --force
```

## Usage

```
todo [LIST] [ACTION ...]
```

`LIST` is optional and defaults to `inbox`. `ACTION` is optional too and
defaults to `list` or `add`, depending on what's left after `LIST`:

```bash
todo add "buy milk"             # == todo inbox add "buy milk"
todo "buy milk"                 # == todo inbox add "buy milk" (add omitted)
todo work add "finish report" -p high -t urgent
todo work "buy milk"            # == todo work add "buy milk" (add omitted)
todo work                       # == todo work list, if 'work' already exists
todo                            # == todo inbox list
```

A bare word with nothing after it (`todo work`) is only treated as a list
name if that list already exists — `inbox` always counts as existing. A recognized action word still wins in
second position, though: `todo work "list"` shows `work`'s items, it does
not add a task named "list".

Lists can be nested into **sublists** by separating names with a `.`, e.g.
`work.meetings`. See [Sublists](#sublists) below for how nesting, grouped
views, and cascading deletes work.

## Commands overview

```bash
todo -a "Buy groceries"    # == todo inbox -a "Buy groceries"
todo -d 1                  # == todo inbox -d 1
```

Lists other than `inbox` don't need to be created up front — `-a/--add`
auto-creates the target list (and any missing parent, for a nested name) the
first time you use it. Use `new-list` only when you want to set a color at
creation time or create an empty list ahead of use. Use `todo all` to print
every list's items in one shot, instead of viewing each list one at a time.

### Nested lists

Join names with a `.` to nest a list under another, e.g. `work.meetings`.

- Nesting is capped at **2 sublist levels** (3 name segments total —
  `work.meetings.standup` is fine, a fourth segment is rejected):

  ```bash
  $ todo new-list work.meetings.standup.daily
  error: 'work.meetings.standup.daily' is nested too deep (max 2 sublist levels).
  ```

- Creating or adding to a sublist **auto-creates any missing parent**:

  ```bash
  $ todo work.meetings -a "Review roadmap"
  added #1 to 'work.meetings'.
  ```

- Viewing a list recurses through **every descendant at any depth**, not
  just direct children, rendered as one tree (see the transcript above).
- `rm-list` on a parent **cascades**: it names every descendant in a single
  confirmation prompt and deletes them all together.

  ```bash
  $ todo rm-list work
  delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
  deleted list 'work' and 1 sublist(s).
  ```

### Priorities & tags

Items have one of three priorities — `low`, `medium` (default), `high` —
and any number of free-form tags:

```bash
todo work -a "Ship v2" -p high -t urgent -t release
```

> [!NOTE]
> There's no built-in "urgent" priority — use it as a tag instead, as above.

`-t/--tag` (used with `-a`/`-e`) **sets** tags on an item. Filtering a
view by tag uses a separate flag, `-f/--filter-tag`, which takes a
single tag, matched exactly and case-insensitively, and applies to
every visible sublist section too:

```bash
$ todo work -f urgent
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
> untouched. Passing `-t`/`-p` alongside repeated `-a` flags applies
> that priority/tags to **every** item added in the same invocation.

### Colors

Lists can carry one of 16 named colors, set via `-c/--color` on `new-list`
or `edit-list`:

<details>
<summary>All 16 color choices</summary>

`white`, `red`, `coral`, `orange`, `yellow`, `lime`, `green`, `teal`, `cyan`,
`sky`, `blue`, `indigo`, `violet`, `purple`, `magenta`, `pink`

</details>

```bash
todo new-list groceries -c teal
todo edit-list work -c coral
```

A list created without `-c` has no color set. `new-list`'s color is
optional; `edit-list`'s `-c` is **required** — there's no way to edit a list
without also specifying a color.

## Routing grammar

`todo [LIST] [ACTION-FLAG] [MODIFIERS]` — `LIST` is an optional
positional (defaults to `inbox`); the action is always an explicit
flag (`-a`, `-d`, `-u`, `-r`, `-e`, `-l`, `--tags`, `--prune`), never a
bare word, so it can never collide with a list name:

| You type | Resolves to | Why |
|---|---|---|
| `todo` | `todo inbox` (view) | no args → default list, default (view) action |
| `todo -d 5` | `todo inbox -d 5` | no `LIST` given → `inbox` |
| `todo work` | view `work` | no action flag → default view |
| `todo work -a "Ship it"` | add "Ship it" to `work` | explicit `-a` |
| `todo -a "x" -a "y"` | adds two items to `inbox` | `-a` is repeatable |
| `todo buy milk` | **error** (exit 2, unrecognized argument) | `buy` fills `LIST`; `milk` has nowhere to go — no more silent list creation |
| `todo "buy milk"` | **error** (exit 1, list not found) | one token fills `LIST` as the literal name `buy milk`, which doesn't exist |

Because the action is always a flag, list names can no longer collide
with what used to be reserved action words — `todo add -a "buy milk"`
now targets a list literally named `add`. Only the 5 top-level
commands below (`lists`, `all`, `new-list`, `rm-list`, `edit-list`) stay
reserved bare words, since they're parsed before `LIST` is ever
considered.

> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers — `-r`
> and `--prune` renumber the remaining items starting from 1. Don't
> hardcode an ID across a sequence of commands that also removes items.

Every example below builds on the same running session — `TODOS_PATH`
starts empty.

| Flag | Purpose | Example |
|---|---|---|
| `-a, --add TEXT` | Add an item to a list (repeatable) | `todo work -a "Ship v2" -p high` |
| `-l, --list` | Show a list's items (default action) | `todo work -f urgent` |
| `-d, --done ID` | Mark an item done | `todo work -d 1` |
| `-u, --undone ID` | Mark an item not done | `todo work -u 1` |
| `-e, --edit ID` | Change an item's text, priority, or tags | `todo work -e 1 --text "Ship v2.1"` |
| `-r, --rm ID` | Remove an item | `todo work -r 1` |
| `--tags` | List distinct tags used in a list | `todo work --tags` |
| `--prune` | Remove all done items from a list | `todo work --prune` |
| `lists` | Show every list, nested as a tree | `todo lists` |
| `all` | Show every list's items | `todo all` |
| `new-list NAME` | Create an empty list | `todo new-list groceries -c teal` |
| `edit-list NAME` | Change a list's color | `todo edit-list work -c coral` |
| `rm-list NAME` | Delete a list and its sublists | `todo rm-list groceries` |

All 8 list-scoped flags (everything except `lists`/`all`/`new-list`/
`rm-list`/`edit-list`) run against `LIST`, which defaults to `inbox` — see
[Routing grammar](#routing-grammar).

## Workflows

<details>
<summary><strong>Morning triage in the inbox</strong></summary>

```bash
$ todo -a "Buy groceries"
added #1 to 'inbox'.

$ todo -a "Call the dentist" -p high
added #2 to 'inbox'.

$ todo -d 1
marked #1 done in 'inbox'.

$ todo inbox -f urgent
inbox
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text            ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴─────────────────┴──────────┴──────┘

$ todo --prune
pruned 1 item(s) from 'inbox'.
```

### `todo new-list`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ todo new-list groceries
created list 'groceries'.

$ todo work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ todo work -a "Finish report" -p high -t urgent
added #1 to 'work'.

$ todo lists
groceries
work
  meetings
```

Note `work` didn't need to exist first — creating `work.meetings` silently
created the empty `work` parent too.

### `todo rm-list`

Deletes a list and everything in it, after a confirmation prompt. If the
list has sublists, they're listed in the prompt and deleted along with it
— see [Sublists](#sublists).

```
$ todo rm-list groceries
delete list 'groceries' and all its items? [y/N]: y
deleted list 'groceries'.

$ todo rm-list work
delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
deleted list 'work' and 1 sublist(s).

$ todo lists
no lists yet.
```

### `todo add`

Adds an item to a list, creating the list (and, for a sublist name, any
missing parent lists) if it doesn't exist yet.

```
$ todo work add "finish report" -p high -t urgent
added #1 to 'work'.

$ todo work add "buy milk" -t errand
added #2 to 'work'.
```

### `todo list` (default action)

Shows a list's items. This is what runs when you give just a list name
(`todo work`) or `todo work list` explicitly. If the list has immediate
sublists, each one renders as its own titled section right after the
parent's table — see [Sublists](#sublists) for the grouped view and how
`-t/--tag` interacts with it.

```
$ todo work
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
│  2 │      │ buy milk      │ medium   │ errand │
└────┴──────┴───────────────┴──────────┴────────┘
```

### `todo done` / `todo undone`

Marks an item done or not done by its `ID` (the leftmost column in the
table above).

```bash
$ todo work -d 1
marked #1 done in 'work'.

$ todo work --prune
pruned 1 item(s) from 'work'.

$ todo work
                 work
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘
```

## Sublists

Any list name can be nested under another by joining names with a `.`,
e.g. `work.meetings` is a sublist of `work`. Nesting is capped at **2
sublist levels** (3 name segments total, e.g. `work.meetings.notes`) —
going deeper raises a clean error instead of silently truncating:

```
$ todo new-list work.meetings.notes
created list 'work.meetings.notes'.

$ todo new-list work.meetings.notes.extra
error: 'work.meetings.notes.extra' is nested too deep (max 2 sublist levels).
```

**Creating a sublist auto-creates missing parents.** `todo new-list
work.meetings` (or `todo work.meetings add ...`) creates an empty `work`
first if it doesn't already exist — you never have to create the chain
top-down by hand.

<details>
<summary><strong>List-scoped actions</strong> (<code>todo [LIST] [ACTION-FLAG] [MODIFIERS]</code>, LIST defaults to <code>inbox</code>)</summary>

Exactly one action flag may be given per invocation (they're mutually
exclusive); omitting one defaults to the view action.

| Flag | Modifiers | Notes |
|---|---|---|
| `-a, --add TEXT...` | `-t, --tag TAG` (repeatable) · `-p, --priority {low,medium,high}` (default `medium`) | Repeatable — each `-a` adds one item. Auto-creates `LIST` (and missing ancestors) if needed. Modifiers apply to every item added in the same invocation. |
| `-l, --list` | `-f, --filter-tag TAG` | Default action (same as passing no action flag at all). Filter also applies to any visible sublist sections. |
| `-d, --done ID` | — | `ID` is an integer. |
| `-u, --undone ID` | — | |
| `-r, --rm ID` | — | Remaining items are renumbered starting from 1. |
| `-e, --edit ID` | `--text TEXT` · `-p, --priority {low,medium,high}` · `-t, --tag TAG` (repeatable) | Only the flags you pass are changed. `-t` **replaces** the whole tag list. |
| `--tags` | — | Distinct tags in `LIST`, one per line, sorted. |
| `--prune` | — | Removes every done item; reports how many were removed. |

Passing a modifier that doesn't apply to the chosen action (e.g.
`-t`/`-p` with `-d`, or `-f` with `-a`) is an argument error (exit 2).

$ todo work
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
`todo work.meetings done 1`.

**A tag filter applies to every section.** `todo work -t urgent` filters
`work`'s own items *and* each sublist's items by the same tag; a sublist
with no matches is dropped from the output entirely:

```
$ todo work -t urgent
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
```

Reserved words that can't be used as a list name: `lists`, `all`,
`new-list`, `rm-list`, `edit-list`.

**Deleting a list cascades to its sublists.** `todo rm-list` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ todo rm-list work
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ todo lists
no lists yet.
```

`inbox` is created automatically the first time it's read. Any other list
is created automatically the first time you `-a/--add` to it.
