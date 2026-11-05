# Shell completion

Taskli ships [`argcomplete`](https://github.com/kislyuk/argcomplete)-based
tab-completion for flags, flag values (`--color`, `--priority`), and the
names of lists you've already created. Free-form flags (`--due`, `--desc`,
`-t/--text`) take no completion.

The shim scripts are pre-generated, checked into `completions/`, and
installed to `<prefix>/share/taskli/completions/`. There is no per-terminal
generation cost and nothing needs to be on your `PATH`: you `source` one
script, once, from your shell rc.

## Enable it

**bash**: add to `~/.bashrc`:

```bash
# installed via uv
source "$(uv tool dir)/taskli-cli/share/taskli/completions/taskli.sh"
# installed via pipx
# source "$(pipx environment --value PIPX_LOCAL_VENVS)/taskli-cli/share/taskli/completions/taskli.sh"
# from a source checkout
# source /path/to/taskli/completions/taskli.sh
```

**zsh**: add the same line to `~/.zshrc`, but it **must come after
`compinit`**. When sourced (rather than placed on `fpath`), the script falls
through to `compdef _python_argcomplete tk taskli`, which needs the completion
system already initialized.

```zsh
autoload -Uz compinit && compinit
source "$(uv tool dir)/taskli-cli/share/taskli/completions/taskli.sh"
```

**PowerShell**: dot-source the `.ps1` into `$PROFILE` (PowerShell uses
`. path`, not `source`):

```powershell
. "$(uv tool dir)\taskli-cli\share\taskli\completions\taskli.ps1"
# from a source checkout, use the path to completions\taskli.ps1
# installed via pipx, use "$(pipx environment --value PIPX_LOCAL_VENVS)" in place of "$(uv tool dir)"
```

## Try it

Start a new shell:

```bash
tk gro<TAB>                   # -> tk groceries
tk groceries --c<TAB>         # -> tk groceries --color
tk groceries --color t<TAB>   # -> teal
tk work --pri<TAB>            # -> tk work --priority
```

The scripts are generated output; see
[`completions/README.md`](../completions/README.md) for how they're produced
and regenerated.
