#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Find the pull request the Code Review workflow reviews when run by hand.

``resolve``  take the link of a pull request of this repository, check that it
             is open, and print its number.

In GitHub Actions the repository and the step outputs come from the
environment; by hand, options name them.
"""

import json
import sys
from pathlib import Path

import click
from common import (
    append,
    gh,
    main,
    number_from_link,
    output_option,
    repo_option,
    repository,
)


@click.group()
def cli() -> None:
    """Find the pull request the Code Review workflow reviews when run by hand."""


@cli.command()
@repo_option
@click.option(
    "--pull-request",
    "link",
    required=True,
    metavar="LINK",
    help="The link of the pull request to review.",
)
@output_option
def resolve(repo: str | None, link: str, github_output: Path | None) -> None:
    """Print the number of the open pull request that LINK names."""
    repo = repository(repo)
    number = number_from_link(link, repo, "pull")
    pull = json.loads(
        gh("pr", "view", str(number), "--repo", repo, "--json", "number,state")
    )
    if pull["state"] != "OPEN":
        raise RuntimeError(f"Pull request #{number} is {pull['state'].lower()}")
    append(github_output, f"number={number}\n")


if __name__ == "__main__":
    sys.exit(main(cli))
