"""Guard that the committed completion scripts match the generator."""

import importlib.metadata
import shutil
import subprocess
from pathlib import Path

import pytest

# keep in sync with completions/README.md; bump on every regeneration.
EXPECTED_ARGCOMPLETE = "3.7.2"


def script_text(name: str) -> str:
    """Return the raw text of a script from the repo ``completions`` dir.

    Parameters
    ----------
    name : str
        The script file name.

    Returns
    -------
    str
        The file contents.
    """

    root = Path(__file__).resolve().parent.parent

    return (root / "completions" / name).read_text()


def run_generator(shell: str) -> str:
    """Return ``register-python-argcomplete`` output for ``shell``.

    Skips the calling test when the generator console script is not on
    ``PATH``, or when the installed ``argcomplete`` differs from the
    version that produced the committed scripts.

    Parameters
    ----------
    shell : str
        The ``-s`` shell flavor to generate for.

    Returns
    -------
    str
        The generator's stdout.
    """

    exe = shutil.which("register-python-argcomplete")
    if exe is None:
        pytest.skip("register-python-argcomplete not on PATH")
    installed = importlib.metadata.version("argcomplete")
    if installed != EXPECTED_ARGCOMPLETE:
        pytest.skip(
            f"argcomplete {installed} != {EXPECTED_ARGCOMPLETE} that "
            "generated the committed scripts; regenerate completions/ "
            "and bump EXPECTED_ARGCOMPLETE"
        )
    result = subprocess.run(
        [exe, "-s", shell, "tk", "taskli"],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout


class TestCompletionScripts:
    def test_sh_matches_generator(self) -> None:
        generated = run_generator("bash")

        assert script_text("taskli.sh") == generated

    def test_ps1_matches_generator(self) -> None:
        generated = run_generator("powershell")

        assert script_text("taskli.ps1") == generated

    def test_sh_registers_both_entry_points(self) -> None:
        text = script_text("taskli.sh")
        bash_line = (
            "complete -o nospace -o default -o bashdefault "
            "-F _python_argcomplete tk taskli"
        )

        assert bash_line in text
        assert "compdef _python_argcomplete tk taskli" in text

    def test_ps1_registers_both_entry_points(self) -> None:
        text = script_text("taskli.ps1")

        assert "Register-ArgumentCompleter -Native -CommandName tk" in text
        assert "Register-ArgumentCompleter -Native -CommandName taskli" in text
