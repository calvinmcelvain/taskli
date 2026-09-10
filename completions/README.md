# Shell completion scripts

Pre-generated [`argcomplete`](https://github.com/kislyuk/argcomplete) shims for
`tk` / `taskli` tab-completion. Both entry points are wired by both files.

| File | Shells |
|---|---|
| `taskli.sh` | bash, zsh |
| `taskli.ps1` | PowerShell |

They are checked in so a new terminal pays no generation cost and nothing needs
to be on `PATH`. End users `source` (bash/zsh) or dot-source (PowerShell) one
file — see the `## Shell completion` section of the top-level `README.md`.

Packaging (`pyproject.toml`) ships this directory in the sdist and maps it into
the wheel at `<prefix>/share/taskli/completions/`.

## Regenerating

These are the **verbatim** output of `register-python-argcomplete` — do not
hand-edit them. The shims are parser-independent (they exec `tk` with
`_ARGCOMPLETE=1` at TAB time), so regeneration is only needed when `argcomplete`
itself is upgraded.

```bash
register-python-argcomplete -s bash tk taskli       > completions/taskli.sh
register-python-argcomplete -s powershell tk taskli  > completions/taskli.ps1
```

Generated with **argcomplete 3.7.2**. When you regenerate, update that version
here and `EXPECTED_ARGCOMPLETE` in `tests/test_completions.py` — the guard test
compares the committed files against a fresh generation only when the installed
`argcomplete` matches that version.
