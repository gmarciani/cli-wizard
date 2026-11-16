#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Take an issue from approved to a draft pull request, for the Engineer workflow.

The workflow runs the commands in order:

``select``    list the issues to implement: the one a link names, or the open
              issues labelled Planned, oldest first.
``read``      write an approved issue's title and body for Claude Code to read.
``submit``    run by Claude Code once its change is committed: run the
              project's checks and, only if they pass, push the branch and
              open the draft pull request.
``conclude``  when the run ends without a pull request, explain why on the
              issue and remove Planned, so the issue is not retried until it
              is labelled again.

An issue is approved when it is open, labelled Planned, and its title and body
have not changed since it was last labelled Planned.

In GitHub Actions the repository, the step outputs and the run summary come
from the environment; by hand, options name them.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

PLANNED = "Planned"
SKIP_CHANGELOG = "Skip Changelog Update"
DEFAULT_MAX_ISSUES = 3
ISSUE_FILE = "claude-issue.md"
PR_BODY_FILE = "claude-pr.md"
CHANGELOG = "CHANGELOG.md"
WORKFLOWS = ".github/workflows/"
ISSUE_LINK = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/issues/(\d+)/?")

# What a change must pass before it is submitted: the tox environments the
# Test workflow runs on a pull request.
CHECKS: tuple[tuple[str, ...], ...] = (("tox", "-e", "lint,type,test"),)

# The issue as of now: its text, its labels, and when its text last changed
# and when it was labelled.
ISSUE_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      number title body state lastEditedAt
      labels(first: 50) { nodes { name } }
      timelineItems(last: 100, itemTypes: [LABELED_EVENT, RENAMED_TITLE_EVENT]) {
        nodes {
          __typename
          ... on LabeledEvent { createdAt label { name } }
          ... on RenamedTitleEvent { createdAt }
        }
      }
    }
  }
}
"""

Issue = dict[str, Any]

repo_option = click.option(
    "--repo",
    envvar="GITHUB_REPOSITORY",
    show_envvar=True,
    help="The repository, OWNER/NAME; the one gh infers when not given.",
)
number_option = click.option(
    "--number", required=True, type=int, help="The issue number."
)
summary_option = click.option(
    "--summary",
    envvar="GITHUB_STEP_SUMMARY",
    show_envvar=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="A Markdown file to append a summary line to.",
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


def capture(tool: str, *args: str) -> str:
    """Run ``tool`` with ``args`` and return its output."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [executable(tool), *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        command = " ".join([tool, *args[:2]])
        raise RuntimeError(f"{command} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def gh(*args: str) -> str:
    """Run ``gh`` with ``args`` and return its output."""
    return capture("gh", *args)


def git(*args: str) -> str:
    """Run ``git`` with ``args`` in the current directory and return its output."""
    return capture("git", *args)


def repository(repo: str | None) -> str:
    """Return the repository, OWNER/NAME: the given one, or the one gh infers."""
    return repo or gh(
        "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
    )


def branch_of(number: int) -> str:
    """Return the branch an issue is implemented on."""
    return f"engineer/issue-{number}"


def open_pull_request(repo: str, number: int) -> str | None:
    """Return the link of the open pull request of an issue's branch, if any."""
    pulls = json.loads(
        gh(
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch_of(number),
            "--state",
            "open",
            "--json",
            "url",
        )
    )
    return pulls[0]["url"] if pulls else None


def note(message: str) -> None:
    """Print a message, as a notice on the run when in GitHub Actions."""
    click.echo(f"::notice::{message}" if os.environ.get("GITHUB_ACTIONS") else message)


def append(path: Path | None, text: str) -> None:
    """Print ``text``, and append it to the file if one is given."""
    click.echo(text, nl=False)
    if path:
        with path.open("a") as file:
            file.write(text)


def fetch_issue(repo: str, number: int) -> Issue:
    """Read an issue with what tells whether it is approved."""
    owner, name = repo.split("/", 1)
    response = json.loads(
        gh(
            "api",
            "graphql",
            "-f",
            f"query={ISSUE_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={name}",
            "-F",
            f"number={number}",
        )
    )
    issue: Issue | None = response["data"]["repository"]["issue"]
    if issue is None:
        raise RuntimeError(f"{repo} has no issue #{number}")
    return issue


def is_approved(issue: Issue) -> bool:
    """Tell whether the issue is open, Planned, and unchanged since labelled."""
    if issue["state"] != "OPEN":
        return False
    if PLANNED not in [label["name"] for label in issue["labels"]["nodes"]]:
        return False
    events = issue["timelineItems"]["nodes"]
    labelled = [
        event["createdAt"]
        for event in events
        if event["__typename"] == "LabeledEvent" and event["label"]["name"] == PLANNED
    ]
    if not labelled:
        return False
    edited = [
        event["createdAt"]
        for event in events
        if event["__typename"] == "RenamedTitleEvent"
    ]
    if issue["lastEditedAt"]:
        edited.append(issue["lastEditedAt"])
    # ISO 8601 timestamps in UTC compare as strings.
    return not edited or max(edited) <= max(labelled)


def issue_number_from(link: str, repo: str) -> int:
    """Return the number of the issue of ``repo`` that ``link`` names."""
    match = ISSUE_LINK.fullmatch(link.strip())
    if not match:
        raise RuntimeError(
            f"'{link}' is not an issue link, "
            f"expected https://github.com/{repo}/issues/<number>"
        )
    if match.group(1).lower() != repo.lower():
        raise RuntimeError(f"'{link}' is not an issue of {repo}")
    return int(match.group(2))


@click.group()
def cli() -> None:
    """Take an issue from approved to a draft pull request."""


@cli.command()
@repo_option
@click.option(
    "--issue",
    "link",
    default="",
    metavar="LINK",
    help="The link of the one issue to implement, retried even if it already "
    "had a pull request. Not with --max-issues.",
)
@click.option(
    "--max-issues",
    default="",
    metavar="N",
    help="The most Planned issues to implement, oldest first; "
    f"{DEFAULT_MAX_ISSUES} when not given. Not with --issue.",
)
@output_option
@summary_option
def select(
    repo: str | None,
    link: str,
    max_issues: str,
    github_output: Path | None,
    summary: Path | None,
) -> None:
    """List the issues to implement, as a JSON array of numbers."""
    # The workflow passes both options, empty when its input is not given.
    if link and max_issues:
        raise RuntimeError("--issue and --max-issues are mutually exclusive")
    repo = repository(repo)

    if link:
        candidates = [issue_number_from(link, repo)]
        limit = 1
    else:
        try:
            limit = int(max_issues) if max_issues else DEFAULT_MAX_ISSUES
        except ValueError:
            limit = 0
        if limit < 1:
            raise RuntimeError(
                f"--max-issues must be a positive number, got '{max_issues}'"
            )
        listed = json.loads(
            gh(
                "issue",
                "list",
                "--repo",
                repo,
                "--label",
                PLANNED,
                "--state",
                "open",
                "--limit",
                "200",
                "--json",
                "number",
            )
        )
        candidates = sorted(issue["number"] for issue in listed)

    selected: list[int] = []
    for number in candidates:
        if len(selected) >= limit:
            break
        if not is_approved(fetch_issue(repo, number)):
            note(
                f"Skipped #{number}: not open and labelled {PLANNED}, or edited "
                f"since it was labelled {PLANNED}."
            )
            continue
        # An issue named by its link is retried whatever its pull requests.
        if not link:
            pulls = json.loads(
                gh(
                    "pr",
                    "list",
                    "--repo",
                    repo,
                    "--head",
                    branch_of(number),
                    "--state",
                    "all",
                    "--json",
                    "number",
                )
            )
            if pulls:
                note(
                    f"Skipped #{number}: it already had a pull request; run the "
                    "workflow with its link to retry."
                )
                continue
        selected.append(number)

    issues = json.dumps(selected, separators=(",", ":"))
    append(github_output, f"issues={issues}\n")
    if summary:
        with summary.open("a") as file:
            file.write(f"Issues to implement: {issues}\n")


@cli.command()
@repo_option
@number_option
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=ISSUE_FILE,
    show_default=True,
    help="The file to write the issue to.",
)
@output_option
def read(
    repo: str | None, number: int, output: Path, github_output: Path | None
) -> None:
    """Write the issue's title and body to a file, if it is still approved."""
    issue = fetch_issue(repository(repo), number)
    approved = is_approved(issue)
    if approved:
        # The title and body as approved, read once here so the text Claude
        # Code reads is the text that was checked.
        output.write_text(f"# {issue['title']}\n\n{issue['body']}\n")
        # Keep the issue and the pull request description out of the commit.
        exclude = output.resolve().parent / ".git" / "info" / "exclude"
        if exclude.exists():
            with exclude.open("a") as ignored:
                ignored.write(f"{output.name}\n{PR_BODY_FILE}\n")
    else:
        note(f"Skipped #{number}: it changed after it was selected.")
    append(github_output, f"approved={str(approved).lower()}\n")


@cli.command()
@repo_option
@number_option
@click.option(
    "--body-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=PR_BODY_FILE,
    show_default=True,
    help="The file holding the pull request description.",
)
@click.option(
    "--base", default="main", show_default=True, help="The branch to merge into."
)
@summary_option
def submit(
    repo: str | None, number: int, body_file: Path, base: str, summary: Path | None
) -> None:
    """Run the project's checks, then push the branch and open the draft pull request.

    Run from the issue's branch, with the change committed. Nothing is pushed
    unless every check passes.
    """
    repo = repository(repo)
    branch = branch_of(number)
    current = git("rev-parse", "--abbrev-ref", "HEAD")
    if current != branch:
        raise RuntimeError(f"On branch {current}, expected {branch}")
    if git("status", "--porcelain"):
        raise RuntimeError("There are uncommitted changes: commit them, then submit")
    fork_point = git("merge-base", f"origin/{base}", "HEAD")
    changed = git("diff", "--name-only", fork_point, "HEAD").split()
    if not changed:
        raise RuntimeError(f"Nothing to submit: {branch} changes nothing in {base}")
    if any(path.startswith(WORKFLOWS) for path in changed):
        raise RuntimeError(
            f"The change touches {WORKFLOWS}, which the workflow's token cannot push"
        )

    for check in CHECKS:
        click.echo(f"Running {' '.join(check)}")
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [executable(check[0]), *check[1:]]
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"'{' '.join(check)}' failed, so nothing was submitted: fix what "
                "it reports, amend the commit and submit again"
            )

    # The branch is this workflow's own: a retry replaces it.
    git("push", "--force", "origin", f"HEAD:refs/heads/{branch}")
    url = open_pull_request(repo, number)
    if url:
        line = f"Updated {url} for #{number}"
    else:
        body = body_file.read_text()
        closes = f"Closes #{number}"
        if closes not in body:
            body = f"{body.rstrip()}\n\n{closes}\n"
        # CLAUDE.md: a change with no changelog entry gets the label.
        label = [] if CHANGELOG in changed else ["--label", SKIP_CHANGELOG]
        url = gh(
            "pr",
            "create",
            "--repo",
            repo,
            "--draft",
            "--base",
            base,
            "--head",
            branch,
            "--title",
            git("log", "-1", "--format=%s"),
            "--body",
            body,
            *label,
        )
        line = f"Opened {url} for #{number}"
    append(summary, f"{line}\n")


@cli.command()
@repo_option
@number_option
@click.option(
    "--result", default="", help="The JSON Claude Code returned, with its reason."
)
@click.option("--claude-outcome", default="", help="How the Claude Code step ended.")
@click.option("--run-url", help="The workflow run to link.")
@summary_option
def conclude(
    repo: str | None,
    number: int,
    result: str,
    claude_outcome: str,
    run_url: str | None,
    summary: Path | None,
) -> None:
    """Explain on the issue why it has no pull request, and remove Planned.

    Does nothing when the issue's pull request is open. Otherwise the issue
    would stay Planned and be retried, unexplained, on every scheduled run.
    """
    repo = repository(repo)
    url = open_pull_request(repo, number)
    if url:
        click.echo(f"#{number} has {url}: nothing to explain")
        return
    try:
        reason = json.loads(result or "null")["reason"]
    except (json.JSONDecodeError, KeyError, TypeError):
        reason = ""
    reason = reason or (
        f"Claude Code did not finish ({claude_outcome or 'not run'}); "
        "see the workflow run."
    )
    workflow = f"[Engineer]({run_url})" if run_url else "Engineer"
    gh(
        "issue",
        "comment",
        str(number),
        "--repo",
        repo,
        "--body",
        f"The {workflow} workflow did not open a pull request for this issue."
        f"\n\n{reason}\n\n"
        f"Clarify the issue if needed, then label it `{PLANNED}` again to retry.",
    )
    gh("issue", "edit", str(number), "--repo", repo, "--remove-label", PLANNED)
    append(summary, f"#{number}: no pull request. {reason}\n")


def main() -> int:
    """Run a command from the command line; return the exit code."""
    try:
        cli()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
