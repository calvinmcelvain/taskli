# todo-cli

[![CI](https://github.com/calvinmcelvain/todo-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/calvinmcelvain/todo-cli/actions/workflows/ci.yml)
[![Release](https://github.com/calvinmcelvain/todo-cli/actions/workflows/release.yml/badge.svg)](https://github.com/calvinmcelvain/todo-cli/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Type checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)

Simple, elegant CLI for tracking todo lists.

## Install

```bash
<<<<<<< Updated upstream
||||||| Stash base
$ todo "Buy groceries"
added #1 to 'inbox'.

$ todo work "Finish report"
added #1 to 'work'.

$ todo work.meetings add "Review roadmap"
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
- [The routing grammar](#the-routing-grammar)
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
- **Terse grammar.** `todo work "Ship it"` just works — you rarely need to
  type `add` or `list` explicitly. See [routing grammar](#routing-grammar).
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
pipx install git+https://github.com/calvinmcelvain/Taskli.git
```

### Install from source

Clone the repository and install it in editable mode for local development.

```bash
git clone https://github.com/calvinmcelvain/Taskli.git
cd Taskli

=======
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
pipx install git+https://github.com/calvinmcelvain/Taskli.git
```

### Install from source

Clone the repository and install it in editable mode for local development.

```bash
git clone https://github.com/calvinmcelvain/Taskli.git
cd Taskli

>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
| Command | Description |
|---|---|
| `todo lists` | Show all list names, as a tree if any are nested. |
| `todo new-list NAME` | Create a new, empty list (or sublist, via `.`). |
| `todo rm-list NAME` | Delete a list and all its items (and any sublists). |
| `todo [LIST] add TEXT` | Add a new item to a list. |
| `todo [LIST]` / `todo [LIST] list` | Show items in a list, plus any sublist sections. |
| `todo [LIST] done ITEM_ID` | Mark an item done. |
| `todo [LIST] undone ITEM_ID` | Mark an item not done. |
| `todo [LIST] rm ITEM_ID` | Delete an item from a list. |
| `todo [LIST] edit ITEM_ID` | Edit an existing item's text, priority, or tags. |
| `todo [LIST] tags` | Show all distinct tags used in a list. |
| `todo [LIST] prune` | Remove all done items from a list. |
||||||| Stash base
```bash
todo "Buy groceries"       # == todo inbox add "Buy groceries"
todo done 1                # == todo inbox done 1
```
=======
```bash
todo -a "Buy groceries"    # == todo inbox -a "Buy groceries"
todo -d 1                  # == todo inbox -d 1
```
>>>>>>> Stashed changes

<<<<<<< Updated upstream
### Additional args
||||||| Stash base
Lists other than `inbox` don't need to be created up front — `add`
auto-creates the target list (and any missing parent, for a nested name) the
first time you use it. Use `new-list` only when you want to set a color at
creation time or create an empty list ahead of use.
=======
Lists other than `inbox` don't need to be created up front — `-a/--add`
auto-creates the target list (and any missing parent, for a nested name) the
first time you use it. Use `new-list` only when you want to set a color at
creation time or create an empty list ahead of use.
>>>>>>> Stashed changes

<<<<<<< Updated upstream
| Flag | Applies to | Description |
||||||| Stash base
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
  $ todo work.meetings add "Review roadmap"
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
todo work add "Ship v2" -p high -t urgent -t release
```

> [!NOTE]
> There's no built-in "urgent" priority — use it as a tag instead, as above.

Filtering by tag (`list`'s `-t/--tag`) takes a single tag, matched exactly
and case-insensitively, and applies to every visible sublist section too:

```bash
$ todo work --tag urgent
work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text        ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ Prep slides │ high     │ urgent │
└────┴──────┴─────────────┴──────────┴────────┘
```

> [!IMPORTANT]
> `edit`'s `-t/--tag` **replaces** an item's entire tag list — it does not
> add to the existing tags. Omit `-t` entirely to leave tags untouched.

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

`todo [LIST] [ACTION ...]` — both `LIST` and `ACTION` are optional, and
Taskli infers the missing piece from what's actually typed:

| You type | Resolves to | Why |
=======
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
>>>>>>> Stashed changes
|---|---|---|
<<<<<<< Updated upstream
| `-p, --priority [low\|medium\|high]` | `add`, `edit` | Set item priority (default: `medium`). |
| `-t, --tag TAG` | `add`, `edit` | Attach a tag; repeatable. |
| `-t, --tag TAG` | `list` | Filter shown items by tag (sublist sections too). |
| `--text TEXT` | `edit` | Replace item text. |
||||||| Stash base
| `todo` | `todo inbox list` | no args → default list, default action |
| `todo done 5` | `todo inbox done 5` | first token is an action word → `inbox` prepended |
| `todo milk` | `todo inbox add milk` | one leftover word, `milk` isn't an existing list → treated as item text |
| `todo work` | `todo work list` | one leftover word, `work` **is** an existing list → shown |
| `todo buy milk` | `todo buy add milk` (creates list `buy`) | two tokens, first isn't an action word → always a list name |
| `todo "buy milk"` | `todo add buy milk` | First token isn't an action word → `add` |
| `todo work "Ship it"` | `todo work add "Ship it"` | second token isn't an action word → `add` |
| `todo work -t urgent` | `todo work list -t urgent` | only a flag is left → default action |
=======
| `todo` | `todo inbox` (view) | no args → default list, default (view) action |
| `todo -d 5` | `todo inbox -d 5` | no `LIST` given → `inbox` |
| `todo work` | view `work` | no action flag → default view |
| `todo work -a "Ship it"` | add "Ship it" to `work` | explicit `-a` |
| `todo -a "x" -a "y"` | adds two items to `inbox` | `-a` is repeatable |
| `todo buy milk` | **error** (exit 2, unrecognized argument) | `buy` fills `LIST`; `milk` has nowhere to go — no more silent list creation |
| `todo "buy milk"` | **error** (exit 1, list not found) | one token fills `LIST` as the literal name `buy milk`, which doesn't exist |

Because the action is always a flag, list names can no longer collide
with what used to be reserved action words — `todo add -a "buy milk"`
now targets a list literally named `add`. Only the 4 top-level
commands below (`lists`, `new-list`, `rm-list`, `edit-list`) stay
reserved bare words, since they're parsed before `LIST` is ever
considered.
>>>>>>> Stashed changes

<<<<<<< Updated upstream
## Command reference
||||||| Stash base
> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers — `rm` and
> `prune` renumber the remaining items starting from 1. Don't hardcode an ID
> across a sequence of commands that also removes items.
=======
> [!IMPORTANT]
> Item IDs are positions within a list, not permanent identifiers — `-r`
> and `--prune` renumber the remaining items starting from 1. Don't
> hardcode an ID across a sequence of commands that also removes items.
>>>>>>> Stashed changes

Every example below builds on the same running session — `TODOS_PATH`
starts empty.

<<<<<<< Updated upstream
### `todo lists`
||||||| Stash base
| Command | Purpose | Example |
|---|---|---|
| `add TEXT` | Add an item to a list | `todo work add "Ship v2" -p high` |
| `list` | Show a list's items (default action) | `todo work list --tag urgent` |
| `done ID` | Mark an item done | `todo work done 1` |
| `undone ID` | Mark an item not done | `todo work undone 1` |
| `edit ID` | Change an item's text, priority, or tags | `todo work edit 1 --text "Ship v2.1"` |
| `rm ID` | Remove an item | `todo work rm 1` |
| `tags` | List distinct tags used in a list | `todo work tags` |
| `prune` | Remove all done items from a list | `todo work prune` |
| `lists` | Show every list, nested as a tree | `todo lists` |
| `new-list NAME` | Create an empty list | `todo new-list groceries -c teal` |
| `edit-list NAME` | Change a list's color | `todo edit-list work -c coral` |
| `rm-list NAME` | Delete a list and its sublists | `todo rm-list groceries` |
=======
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
| `new-list NAME` | Create an empty list | `todo new-list groceries -c teal` |
| `edit-list NAME` | Change a list's color | `todo edit-list work -c coral` |
| `rm-list NAME` | Delete a list and its sublists | `todo rm-list groceries` |
>>>>>>> Stashed changes

<<<<<<< Updated upstream
Shows every list name. Sublists print indented under their parent as a
tree, not mixed into one flat alphabetical dump.
||||||| Stash base
All 8 list-scoped actions (everything except `lists`/`new-list`/`rm-list`/
`edit-list`) run against `LIST`, which defaults to `inbox` — see
[The routing grammar](#the-routing-grammar).
=======
All 8 list-scoped flags (everything except `lists`/`new-list`/`rm-list`/
`edit-list`) run against `LIST`, which defaults to `inbox` — see
[Routing grammar](#routing-grammar).
>>>>>>> Stashed changes

<<<<<<< Updated upstream
```
$ todo lists
no lists yet.
||||||| Stash base
## Workflows

<details>
<summary><strong>Morning triage in the inbox</strong></summary>

```bash
$ todo "Buy groceries"
added #1 to 'inbox'.

$ todo "Call the dentist" -p high
added #2 to 'inbox'.

$ todo done 1
marked #1 done in 'inbox'.

$ todo inbox --tag urgent
inbox
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text            ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴─────────────────┴──────────┴──────┘

$ todo prune
pruned 1 item(s) from 'inbox'.
=======
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
>>>>>>> Stashed changes
```

### `todo new-list`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ todo new-list groceries
created list 'groceries'.

<<<<<<< Updated upstream
$ todo new-list work.meetings
created list 'work.meetings'.
||||||| Stash base
$ todo work.meetings add "Review roadmap"
added #1 to 'work.meetings'.

$ todo work add "Finish report" -p high -t urgent
added #1 to 'work'.
=======
$ todo work.meetings -a "Review roadmap"
added #1 to 'work.meetings'.

$ todo work -a "Finish report" -p high -t urgent
added #1 to 'work'.
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
```
$ todo work done 1
marked #1 done in 'work'.

$ todo work undone 1
marked #1 not done in 'work'.
```

### `todo edit`

Updates an existing item's text, priority, and/or tags. Only the flags you
pass are changed — everything else is left as-is.

```
$ todo work edit 2 --text "buy oat milk" -p low
updated #2 in 'work'.

$ todo work
                        work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
│  2 │      │ buy oat milk  │ low      │ errand │
└────┴──────┴───────────────┴──────────┴────────┘
```

### `todo rm`

Deletes a single item from a list by `ID`. Remaining items are renumbered
sequentially.

```
$ todo work rm 2
removed #2 from 'work'.
```

### `todo tags`

Lists every distinct tag used anywhere in a list, one per line, sorted.

```
$ todo work tags
urgent
```

### `todo prune`

Removes every done item from a list in one shot and reports how many were
removed.

```
$ todo work done 1
||||||| Stash base
```bash
$ todo work done 1
=======
```bash
$ todo work -d 1
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
**Viewing a list groups in its immediate sublists.** `todo work` shows
`work`'s own items, then a separate titled table per direct sublist. Only
*immediate* children are grouped in — a grandchild like
`work.meetings.notes` shows up under `todo work.meetings`, not under
`todo work`:
||||||| Stash base
<details>
<summary><strong>List-scoped actions</strong> (<code>todo [LIST] ACTION ...</code>, LIST defaults to <code>inbox</code>)</summary>
=======
<details>
<summary><strong>List-scoped actions</strong> (<code>todo [LIST] [ACTION-FLAG] [MODIFIERS]</code>, LIST defaults to <code>inbox</code>)</summary>
>>>>>>> Stashed changes

<<<<<<< Updated upstream
```
$ todo work.meetings add "sync with design" -p high
added #1 to 'work.meetings'.
||||||| Stash base
| Command | Flags | Notes |
|---|---|---|
| `todo [LIST] add TEXT` | `-t, --tag TAG` (repeatable) · `-p, --priority {low,medium,high}` (default `medium`) | Auto-creates `LIST` (and missing ancestors) if needed. |
| `todo [LIST] list` | `-t, --tag TAG` | Default action. Filter also applies to any visible sublist sections. |
| `todo [LIST] done ID` | — | `ID` is an integer. |
| `todo [LIST] undone ID` | — | |
| `todo [LIST] rm ID` | — | Remaining items are renumbered starting from 1. |
| `todo [LIST] edit ID` | `--text TEXT` · `-p, --priority {low,medium,high}` · `-t, --tag TAG` (repeatable) | Only the flags you pass are changed. `-t` **replaces** the whole tag list. |
| `todo [LIST] tags` | — | Distinct tags in `LIST`, one per line, sorted. |
| `todo [LIST] prune` | — | Removes every done item; reports how many were removed. |
=======
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
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
(`work.meetings`'s one item has no `urgent` tag, so its section doesn't
print at all here.)
||||||| Stash base
Reserved words that can't be used as a list name: `add`, `list`, `done`,
`undone`, `rm`, `edit`, `tags`, `prune`, `lists`, `new-list`, `rm-list`,
`edit-list`.
=======
Reserved words that can't be used as a list name: `lists`, `new-list`,
`rm-list`, `edit-list`.
>>>>>>> Stashed changes

**Deleting a list cascades to its sublists.** `todo rm-list` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ todo rm-list work
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ todo lists
no lists yet.
```

<<<<<<< Updated upstream
## Storage

Lists are stored as JSON files under `$TODOS_PATH` (defaults to
`~/.todos`), one file per list. A sublist's dotted name maps straight to
its filename — `work.meetings` is stored as `work.meetings.json` in the
same flat directory as every other list.
||||||| Stash base
`inbox` is created automatically the first time it's read. Any other list
is created automatically the first time you `add` to it.
=======
`inbox` is created automatically the first time it's read. Any other list
is created automatically the first time you `-a/--add` to it.
>>>>>>> Stashed changes
