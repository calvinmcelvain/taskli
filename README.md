# todo-cli

[![CI](https://github.com/calvinmcelvain/todo-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/calvinmcelvain/todo-cli/actions/workflows/ci.yml)
[![Release](https://github.com/calvinmcelvain/todo-cli/actions/workflows/release.yml/badge.svg)](https://github.com/calvinmcelvain/todo-cli/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Type checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue)

Simple, elegant CLI for tracking todo lists.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate      # Git Bash on Windows: source .venv/Scripts/activate
pip install -e ".[dev]"
```

## Usage

```
todo [LIST] [ACTION ...]
```

`LIST` is optional and defaults to `inbox`. `ACTION` is optional too and
defaults to `list`:

```bash
todo add "buy milk"            # == todo inbox add "buy milk"
todo work add "finish report" -p high -t urgent
todo work                      # == todo work list
todo                           # == todo inbox list
```

Lists can be nested into **sublists** by separating names with a `.`, e.g.
`work.meetings`. See [Sublists](#sublists) below for how nesting, grouped
views, and cascading deletes work.

## Commands overview

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

### Additional args

| Flag | Applies to | Description |
|---|---|---|
| `-p, --priority [low\|medium\|high]` | `add`, `edit` | Set item priority (default: `medium`). |
| `-t, --tag TAG` | `add`, `edit` | Attach a tag; repeatable. |
| `-t, --tag TAG` | `list` | Filter shown items by tag (sublist sections too). |
| `--text TEXT` | `edit` | Replace item text. |

## Command reference

Every example below builds on the same running session — `TODOS_PATH`
starts empty.

### `todo lists`

Shows every list name. Sublists print indented under their parent as a
tree, not mixed into one flat alphabetical dump.

```
$ todo lists
no lists yet.
```

### `todo new-list`

Creates a new, empty list. Name it with a `.` (e.g. `work.meetings`) to
create a **sublist** — see [Sublists](#sublists) for the full behavior
(auto-created parents, the depth cap, cascading delete).

```
$ todo new-list groceries
created list 'groceries'.

$ todo new-list work.meetings
created list 'work.meetings'.

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
marked #1 done in 'work'.

$ todo work prune
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

**Viewing a list groups in its immediate sublists.** `todo work` shows
`work`'s own items, then a separate titled table per direct sublist. Only
*immediate* children are grouped in — a grandchild like
`work.meetings.notes` shows up under `todo work.meetings`, not under
`todo work`:

```
$ todo work.meetings add "sync with design" -p high
added #1 to 'work.meetings'.

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

(`work.meetings`'s one item has no `urgent` tag, so its section doesn't
print at all here.)

**Deleting a list cascades to its sublists.** `todo rm-list` lists any
sublists in the confirmation prompt and removes all of them together:

```
$ todo rm-list work
delete list 'work' and its 2 sublist(s) (work.meetings, work.meetings.notes) and all their items? [y/N]: y
deleted list 'work' and 2 sublist(s).

$ todo lists
no lists yet.
```

## Storage

Lists are stored as JSON files under `$TODOS_PATH` (defaults to
`~/.todos`), one file per list. A sublist's dotted name maps straight to
its filename — `work.meetings` is stored as `work.meetings.json` in the
same flat directory as every other list.
