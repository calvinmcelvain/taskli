# todo-cli

[![CI](https://github.com//actions/workflows/ci.yml/badge.svg)](https://github.com//actions/workflows/ci.yml)
[![Release](https://github.com//actions/workflows/release.yml/badge.svg)](https://github.com//actions/workflows/release.yml)
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

### Core actions

| Command | Description |
|---|---|
| `todo lists` | Show all list names. |
| `todo new-list NAME` | Create a new, empty list. |
| `todo rm-list NAME` | Delete a whole list and all its items. |
| `todo [LIST] add TEXT` | Add a new item to a list. |
| `todo [LIST]` / `todo [LIST] list` | Show items in a list. |
| `todo [LIST] done ITEM_ID` | Mark an item done. |
| `todo [LIST] undone ITEM_ID` | Mark an item not done. |
| `todo [LIST] rm ITEM_ID` | Delete an item from a list. |
| `todo [LIST] edit ITEM_ID` | Edit an existing item's text, priority, or tags. |

### Additional args

| Flag | Applies to | Description |
|---|---|---|
| `-p, --priority [low\|medium\|high]` | `add`, `edit` | Set item priority (default: `medium`). |
| `-t, --tag TAG` | `add`, `edit` | Attach a tag; repeatable. |
| `-t, --tag TAG` | `list` | Filter shown items by tag. |
| `--text TEXT` | `edit` | Replace item text. |

### Extra list-scoped actions

| Command | Description |
|---|---|
| `todo [LIST] tags` | Show all distinct tags used in a list. |
| `todo [LIST] prune` | Remove all done items from a list. |

### Examples

```
$ todo work add "finish report" -p high -t urgent
added #1 to 'work'.

$ todo work add "buy milk" -t errand
added #2 to 'work'.

$ todo work
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ finish report │ high     │ urgent │
│  2 │      │ buy milk      │ medium   │ errand │
└────┴──────┴───────────────┴──────────┴────────┘

$ todo work done 1
marked #1 done in 'work'.

$ todo work
                      work
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text          ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │ x    │ finish report │ high     │ urgent │
│  2 │      │ buy milk      │ medium   │ errand │
└────┴──────┴───────────────┴──────────┴────────┘

$ todo work tags
errand
urgent

$ todo work prune
pruned 1 item(s) from 'work'.

$ todo work
                    work
┏━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Done ┃ Text     ┃ Priority ┃ Tags   ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│  1 │      │ buy milk │ medium   │ errand │
└────┴──────┴──────────┴──────────┴────────┘

$ todo lists
work

$ todo
                inbox
┏━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ ID ┃ Done ┃ Text ┃ Priority ┃ Tags ┃
┡━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━┩
└────┴──────┴──────┴──────────┴──────┘
```

## Storage

Lists are stored as JSON files under `$TODOS_PATH` (defaults to `~/.todos`), one file per list.
