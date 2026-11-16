# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""What tools/engineer.py and tools/product_manager.py share.

Running ``gh`` and ``git``, the options that GitHub Actions fills from the
environment, and the entry point that reports an error and exits.
"""

import shutil
import subprocess
from pathlib import Path

import click

repo_option = click.option(
    "--repo",
    envvar="GITHUB_REPOSITORY",
    show_envvar=True,
    help="The repository, OWNER/NAME; the one gh infers when not given.",
)
summary_option = click.option(
    "--summary",
    envvar="GITHUB_STEP_SUMMARY",
    show_envvar=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="A Markdown file to append the summary to.",
)
output_option = click.option(
    "--github-output",
    envvar="GITHUB_OUTPUT",
    show_envvar=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="A file to append the outputs to.",
)


def executable(tool: str) -> str:
    """Return the path of ``tool``, which must be installed."""
    path = shutil.which(tool)
    if path is None:
        raise RuntimeError(f"{tool} is not installed")
    return path


def capture(tool: str, *args: str, cwd: Path | None = None) -> str:
    """Run ``tool`` with ``args`` and return its output."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [executable(tool), *args], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        command = " ".join([tool, *args[:2]])
        raise RuntimeError(f"{command} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def gh(*args: str) -> str:
    """Run ``gh`` with ``args`` and return its output."""
    return capture("gh", *args)


def git(*args: str, cwd: Path | None = None) -> str:
    """Run ``git`` with ``args``, in ``cwd`` if given, and return its output."""
    return capture("git", *args, cwd=cwd)


def repository(repo: str | None) -> str:
    """Return the repository, OWNER/NAME: the given one, or the one gh infers."""
    return repo or gh(
        "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
    )


def append(path: Path | None, text: str) -> None:
    """Print ``text``, and append it to the file if one is given."""
    click.echo(text, nl=False)
    if path:
        with path.open("a") as file:
            file.write(text)


def main(cli: click.Group) -> int:
    """Run the commands of ``cli`` from the command line; return the exit code."""
    try:
        cli()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return 1
    return 0
