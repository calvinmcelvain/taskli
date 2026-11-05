# Configuration

Settings live in `$TASKLI_PATH/.taskli.json` (next to your lists,
`~/.taskli/.taskli.json` by default). Edit it by hand or with `tk --config`:

```bash
tk --config                          # show every setting
tk --config default_priority         # show one
tk --config default_priority high    # change one
```

| Key | Values | Default | Description |
|---|---|---|---|
| `default_list` | any name | `inbox` | List used when `LIST` is omitted. |
| `default_priority` | `low` `medium` `high` | `medium` | Priority for new items when `-p` is omitted. |
| `default_color` | a [color](lists.md#colors) | `white` | Color for lists created without `--color`. |
| `default_sort` | `created_at` `priority` `tags` `due_date` | `created_at` | Sort key for items. Changing it re-sorts every list. `due_date` puts undated items last. |
| `auto_prune` | `true` `false` | `false` | Remove done items whenever a list is viewed. |
| `silent_prune` | `true` `false` | `false` | With `--prune`, print only the per-list summary and skip re-rendering the tree. Doesn't affect `auto_prune`. |
| `show_reminders` | `true` `false` | `true` | Print an "N overdue, M due today" line above commands. |
| `agenda_window` | `today` `week` `overdue` or `N` | `week` | Default window for `tk --agenda`. |
| `agenda_include_overdue` | `true` `false` | `true` | Whether `--agenda` windows also list items already overdue. |
| `inherit_sublist_color` | `true` `false` | `true` | New sublists inherit the nearest ancestor's color. |
| `sublist_delimiter` | `.` `/` `-` `\|` | `.` | Character used to type and display nested names. |

> [!WARNING]
> `sublist_delimiter` is a display and input choice; storage always uses `.`.
> Changing it can stop existing nested names containing the old character from
> resolving as sublists until you rename them. The configured character can
> never appear inside a single list name (with `-`, `my-list` means sublist
> `list` under `my`).

An unknown key or invalid value is an error (exit 1):

```console
$ tk --config nope
error: 'nope' is not a config key.

$ tk --config auto_prune sortof
error: 'sortof' is not a valid value for 'auto_prune'.
```

## Upgrading files

If you upgrade taskli and a list or config file uses an older schema, taskli
stops with an error telling you to run `tk --migrate`. It never rewrites your
files on its own.
