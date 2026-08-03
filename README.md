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

$ task work
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
  deep. Parents auto-create on demand; viewing or deleting a list reaches
  every descendant.
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
task [LIST] [ACTION ...]
```

`LIST` is optional and defaults to `inbox`. `ACTION` is optional too and
defaults to `list` or `add`, depending on what's left after `LIST`:

```bash
task add "buy milk"             # == task inbox add "buy milk"
task "buy milk"                 # == task inbox add "buy milk" (add omitted)
task work add "finish report" -p high -t urgent
task work "buy milk"            # == task work add "buy milk" (add omitted)
task work                       # == task work list, if 'work' already exists
task                            # == task inbox list
```

A bare word with nothing after it (`task work`) is only treated as a list
name if that list already exists — `inbox` always counts as existing. A recognized action word still wins in
second position, though: `task work "list"` shows `work`'s items, it does
not add a task named "list".

Lists can be nested into **sublists** by separating names with a `.`, e.g.
`work.meetings`. See [Sublists](#sublists) below for how nesting, grouped
views, and cascading deletes work.

## Commands overview

```bash
task -a "Buy groceries"    # == task inbox -a "Buy groceries"
task -d 1                  # == task inbox -d 1
```

Lists other than `inbox` don't need to be created up front — `-a/--add`
auto-creates the target list (and any missing parent, for a nested name) the
first time you use it. Use `new-list` only when you want to set a color at
creation time or create an empty list ahead of use. Use `task all` to print
every list's items in one shot, instead of viewing each list one at a time.

### Nested lists

Join names with a `.` to nest a list under another, e.g. `work.meetings`.

- Nesting is capped at **2 sublist levels** (3 name segments total —
  `work.meetings.standup` is fine, a fourth segment is rejected):

  ```bash
  $ task new-list work.meetings.standup.daily
  error: 'work.meetings.standup.daily' is nested too deep (max 2 sublist levels).
  ```

- Creating or adding to a sublist **auto-creates any missing parent**:

  ```bash
  $ task work.meetings -a "Review roadmap"
  added #1 to 'work.meetings'.
  ```

- Viewing a list recurses through **every descendant at any depth**, not
  just direct children, rendered as one tree (see the transcript above).
- `rm-list` on a parent **cascades**: it names every descendant in a single
  confirmation prompt and deletes them all together.

  ```bash
  $ task rm-list work
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
task new-list groceries -c teal
task edit-list work -c coral
```

A list created without `-c` has no color set. `new-list`'s color is
optional; `edit-list`'s `-c` is **required** — there's no way to edit a list
without also specifying a color.

## Routing grammar

`task [LIST] [ACTION-FLAG] [MODIFIERS]` — `LIST` is an optional
positional (defaults to `inbox`); the action is always an explicit
flag (`-a`, `-d`, `-u`, `-r`, `-e`, `-l`, `--tags`, `--prune`), never a
bare word, so it can never collide with a list name:

| You type | Resolves to | Why |
|---|---|---|
| `task` | `task inbox` (view) | no args → default list, default (view) action |
| `task -d 5` | `task inbox -d 5` | no `LIST` given → `inbox` |
| `task work` | view `work` | no action flag → default view |
| `task work -a "Ship it"` | add "Ship it" to `work` | explicit `-a` |
| `task -a "x" -a "y"` | adds two items to `inbox` | `-a` is repeatable |
| `task buy milk` | **error** (exit 2, unrecognized argument) | `buy` fills `LIST`; `milk` has nowhere to go — no more silent list creation |
| `task "buy milk"` | **error** (exit 1, list not found) | one token fills `LIST` as the literal name `buy milk`, which doesn't exist |

Because the action is always a flag, list names can no longer collide
with what used to be reserved action words — `task add -a "buy milk"`
now targets a list literally named `add`. Only the 6 top-level
commands below (`lists`, `all`, `new-list`, `rm-list`, `edit-list`,
`config`) stay reserved bare words, since they're parsed before `LIST`
is ever considered.

> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers — `-r`
> and `--prune` renumber the remaining items starting from 1. Don't
> hardcode an ID across a sequence of commands that also removes items.

Every example below builds on the same running session — `taskS_PATH`
starts empty.

| Flag | Purpose | Example |
|---|---|---|
| `-a, --add TEXT` | Add an item to a list (repeatable) | `task work -a "Ship v2" -p high` |
| `-l, --list` | Show a list's items (default action) | `task work -f urgent` |
| `-d, --done ID` | Mark an item done | `task work -d 1` |
| `-u, --undone ID` | Mark an item not done | `task work -u 1` |
| `-e, --edit ID` | Change an item's text, priority, or tags | `task work -e 1 --text "Ship v2.1"` |
| `-r, --rm ID` | Remove an item | `task work -r 1` |
| `--tags` | List distinct tags used in a list | `task work --tags` |
| `--prune` | Remove all done items from a list | `task work --prune` |
| `lists` | Show every list, nested as a tree | `task lists` |
| `all` | Show every list's items | `task all` |
| `new-list NAME` | Create an empty list | `task new-list groceries -c teal` |
| `edit-list NAME` | Change a list's color | `task edit-list work -c coral` |
| `rm-list NAME` | Delete a list and its sublists | `task rm-list groceries` |
| `config [KEY] [VALUE]` | View or edit config settings | `task config default_priority high` |

All 8 list-scoped flags (everything except `lists`/`all`/`new-list`/
`rm-list`/`edit-list`/`config`) run against `LIST`, which defaults to
`inbox` — see [Routing grammar](#routing-grammar).

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

### `task new-list`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ task new-list groceries
created list 'groceries'.

$ task work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ task work -a "Finish report" -p high -t urgent
added #1 to 'work'.

$ task lists
groceries
work
  meetings
```

Note `work` didn't need to exist first — creating `work.meetings` silently
created the empty `work` parent too.

### `task rm-list`

Deletes a list and everything in it, after a confirmation prompt. If the
list has sublists, they're listed in the prompt and deleted along with it
— see [Sublists](#sublists).

```
$ task rm-list groceries
delete list 'groceries' and all its items? [y/N]: y
deleted list 'groceries'.

$ task rm-list work
delete list 'work' and its 1 sublist(s) (work.meetings) and all their items? [y/N]: y
deleted list 'work' and 1 sublist(s).

$ task lists
no lists yet.
```

### `task add`

Adds an item to a list, creating the list (and, for a sublist name, any
missing parent lists) if it doesn't exist yet.

```
$ task work add "finish report" -p high -t urgent
added #1 to 'work'.

$ task work add "buy milk" -t errand
added #2 to 'work'.
```

### `task list` (default action)

Shows a list's items. This is what runs when you give just a list name
(`task work`) or `task work list` explicitly. If the list has immediate
sublists, each one renders as its own titled section right after the
parent's table — see [Sublists](#sublists) for the grouped view and how
`-t/--tag` interacts with it.

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

### `task done` / `task undone`

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

## Sublists

Any list name can be nested under another by joining names with a `.`,
e.g. `work.meetings` is a sublist of `work`. Nesting is capped at **2
sublist levels** (3 name segments total, e.g. `work.meetings.notes`) —
going deeper raises a clean error instead of silently truncating:

```
$ task new-list work.meetings.notes
created list 'work.meetings.notes'.

$ task new-list work.meetings.notes.extra
error: 'work.meetings.notes.extra' is nested too deep (max 2 sublist levels).
```

**Creating a sublist auto-creates missing parents.** `task new-list
work.meetings` (or `task work.meetings add ...`) creates an empty `work`
first if it doesn't already exist — you never have to create the chain
top-down by hand.

<details>
<summary><strong>List-scoped actions</strong> (<code>task [LIST] [ACTION-FLAG] [MODIFIERS]</code>, LIST defaults to <code>inbox</code>)</summary>

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

$ task work
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
`task work.meetings done 1`.

**A tag filter applies to every section.** `task work -t urgent` filters
`work`'s own items *and* each sublist's items by the same tag; a sublist
with no matches is dropped from the output entirely:

```
$ task work -t urgent
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
└────┴──────┴───────────────┴──────────┴────────┘
```

Reserved words that can't be used as a list name: `lists`, `all`,
`new-list`, `rm-list`, `edit-list`, `config`.

**Deleting a list cascades to its sublists.** `task rm-list` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ task rm-list work
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ task lists
no lists yet.
```

The configured `default_list` (`inbox` by default) is created
automatically the first time it's read. Any other list is created
automatically the first time you `-a/--add` to it.

</details>

## Configuration

Taskli keeps a single settings file at `$TASKLI_PATH/.taskli.json`
(next to your list files, `~/.taskli/.taskli.json` by default). Edit it
by hand, or through `task config`:

```
$ task config
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

$ task config default_priority
medium

$ task config default_priority high
set 'default_priority' to 'high'.
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `auto_prune` | `true`/`false` | `false` | Automatically removes done items whenever a list is viewed (`task LIST`/`task all`), same effect as `--prune`. |
| `sublist_delimiter` | one of `.`, `/`, `-`, `\|` | `.` | The delimiter used when typing or displaying nested list names. Storage always uses `.` internally, so lists created under one delimiter are unaffected by later changing it, but existing nested list names containing the old delimiter character may stop resolving as sublists until renamed. Like `.` today, the configured character can't appear literally inside a single segment's name — it always denotes a nesting boundary (e.g. with `-`, `my-list` is parsed as sublist `list` under `my`). |
| `default_list` | string | `inbox` | The list used when `LIST` is omitted, and the list auto-created on first read. |
| `default_sort` | `tags`/`priority`/`created_at` | `created_at` | Sort key applied to items shown by `task LIST`/`task all`. |
| `default_priority` | `low`/`medium`/`high` | `medium` | Priority used for new items added via `-a` when `-p` is omitted. |
| `default_color` | color name (see [Colors](#colors)) | `white` | Default color for lists created via `new-list` when `-c` is omitted. |

An unknown key or an invalid value for a key is an error (exit 1):

```
$ task config nope
error: 'nope' is not a config key.

$ task config auto_prune sortof
error: 'sortof' is not a valid value for 'auto_prune'.
```
