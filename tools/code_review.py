#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Find the pull request the Code Review workflow reviews when run by hand.

``resolve``  take the link of a pull request of this repository, check that it
             is open, and print its number.

In GitHub Actions the repository and the step outputs come from the
environment; by hand, options name them.

Examples, from the repository root::

    # Print the number of a pull request of this repository, if it is open
    tools/code_review.py resolve --pull-request https://github.com/OWNER/NAME/pull/42

    # A pull request of another repository
    link=https://github.com/OWNER/NAME/pull/42
    tools/code_review.py resolve --repo OWNER/NAME --pull-request "$link"

    # Also write number=42 to a file, as the workflow's step does
    tools/code_review.py resolve --pull-request "$link" --github-output out.txt
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
