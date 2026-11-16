#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Pick the issues the Engineer workflow implements, and report on each.

The workflow runs the three commands in order:

``select``  list the issues to implement: the one a link names, or the open
            issues labelled Planned, oldest first.
``read``    write an approved issue's title and body for Claude Code to read.
``report``  after Claude Code ran, start the Test workflow on the pull request
            it opened, or explain on the issue why there is none.

In GitHub Actions the repository, the step outputs and the run summary come
from the environment; by hand, options name them.

An issue is approved when it is open, labelled Planned, and its title and body
have not changed since it was last labelled Planned.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PLANNED = "Planned"
DEFAULT_MAX_ISSUES = 3
ISSUE_LINK = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/issues/(\d+)/?")

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


def gh(*args: str) -> str:
    """Run ``gh`` with ``args`` and return its output."""
    executable = shutil.which("gh")
    if executable is None:
        raise RuntimeError("gh is not installed, see https://cli.github.com")
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [executable, *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def env_path(name: str) -> Path | None:
    """Return the file an environment variable names, if it is set."""
    value = os.environ.get(name)
    return Path(value) if value else None


def repository(repo: str | None) -> str:
    """Return the repository, OWNER/NAME: the given one, or the one gh infers."""
    return repo or gh(
        "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
    )


def note(message: str) -> None:
    """Print a message, as a notice on the run when in GitHub Actions."""
    print(f"::notice::{message}" if os.environ.get("GITHUB_ACTIONS") else message)


def write_outputs(path: Path | None, outputs: dict[str, str]) -> None:
    """Print the outputs, and append them to the GitHub output file if given."""
    lines = "".join(f"{name}={value}\n" for name, value in outputs.items())
    print(lines, end="")
    if path:
        with path.open("a") as output:
            output.write(lines)


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


def select(args: argparse.Namespace) -> int:
    """List the issues to implement, as a JSON array of numbers."""
    if args.issue and args.max_issues:
        raise RuntimeError("--issue and --max-issues are mutually exclusive")
    repo = repository(args.repo)

    if args.issue:
        candidates = [issue_number_from(args.issue, repo)]
        limit = 1
    else:
        try:
            limit = int(args.max_issues) if args.max_issues else DEFAULT_MAX_ISSUES
        except ValueError:
            limit = 0
        if limit < 1:
            raise RuntimeError(
                f"--max-issues must be a positive number, got '{args.max_issues}'"
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
        if not args.issue:
            pulls = json.loads(
                gh(
                    "pr",
                    "list",
                    "--repo",
                    repo,
                    "--head",
                    f"engineer/issue-{number}",
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
    write_outputs(args.github_output, {"issues": issues})
    if args.summary:
        with args.summary.open("a") as summary:
            summary.write(f"Issues to implement: {issues}\n")
    return 0


def read(args: argparse.Namespace) -> int:
    """Write the issue's title and body to a file, if it is still approved."""
    issue = fetch_issue(repository(args.repo), args.number)
    approved = is_approved(issue)
    if approved:
        # The title and body as approved, read once here so the text Claude
        # Code reads is the text that was checked.
        args.output.write_text(f"# {issue['title']}\n\n{issue['body']}\n")
        # Keep the file out of what Claude Code commits.
        exclude = args.output.resolve().parent / ".git" / "info" / "exclude"
        if exclude.exists():
            with exclude.open("a") as ignored:
                ignored.write(f"{args.output.name}\n")
    else:
        note(f"Skipped #{args.number}: it changed after it was selected.")
    write_outputs(args.github_output, {"approved": str(approved).lower()})
    return 0


def report(args: argparse.Namespace) -> int:
    """Start the tests of the pull request, or explain why there is none."""
    repo = repository(args.repo)
    pulls = json.loads(
        gh(
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            args.branch,
            "--state",
            "open",
            "--json",
            "url",
        )
    )
    if pulls:
        # A pull request opened with the workflow's token triggers no workflow.
        gh("workflow", "run", "test.yaml", "--repo", repo, "--ref", args.branch)
        line = f"Opened {pulls[0]['url']} for #{args.number}"
    else:
        try:
            reason = json.loads(args.result or "null")["reason"]
        except (json.JSONDecodeError, KeyError, TypeError):
            reason = ""
        reason = reason or (
            f"Claude Code did not finish ({args.claude_outcome or 'not run'}); "
            "see the workflow run."
        )
        workflow = f"[Engineer]({args.run_url})" if args.run_url else "Engineer"
        gh(
            "issue",
            "comment",
            str(args.number),
            "--repo",
            repo,
            "--body",
            f"The {workflow} workflow did not open a pull request for this issue."
            f"\n\n{reason}\n\n"
            f"Clarify the issue if needed, then label it `{PLANNED}` again to retry.",
        )
        gh("issue", "edit", str(args.number), "--repo", repo, "--remove-label", PLANNED)
        line = f"#{args.number}: no pull request. {reason}"
    print(line)
    if args.summary:
        with args.summary.open("a") as summary:
            summary.write(f"{line}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a command from the command line; return the exit code."""
    parser = argparse.ArgumentParser(
        description="Pick the issues the Engineer workflow implements, and report."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="the repository, OWNER/NAME (default: $GITHUB_REPOSITORY, "
        "or the one gh infers)",
    )
    common.add_argument(
        "--summary",
        type=Path,
        default=env_path("GITHUB_STEP_SUMMARY"),
        help="a Markdown file to append a summary line to "
        "(default: $GITHUB_STEP_SUMMARY)",
    )
    outputs = argparse.ArgumentParser(add_help=False)
    outputs.add_argument(
        "--github-output",
        type=Path,
        default=env_path("GITHUB_OUTPUT"),
        help="a file to append the outputs to (default: $GITHUB_OUTPUT)",
    )

    selecting = commands.add_parser(
        "select", parents=[common, outputs], help="list the issues to implement"
    )
    selecting.add_argument(
        "--issue",
        default="",
        metavar="LINK",
        help="the link of the one issue to implement, retried even if it already "
        "had a pull request; not with --max-issues",
    )
    selecting.add_argument(
        "--max-issues",
        default="",
        metavar="N",
        help="the most Planned issues to implement, oldest first "
        f"(default: {DEFAULT_MAX_ISSUES}); not with --issue",
    )
    selecting.set_defaults(run=select)

    reading = commands.add_parser(
        "read", parents=[common, outputs], help="write an approved issue to a file"
    )
    reading.add_argument("--number", required=True, type=int, help="the issue number")
    reading.add_argument(
        "--output", required=True, type=Path, help="the file to write the issue to"
    )
    reading.set_defaults(run=read)

    reporting = commands.add_parser(
        "report", parents=[common], help="report what became of an issue"
    )
    reporting.add_argument("--number", required=True, type=int, help="the issue number")
    reporting.add_argument(
        "--branch", required=True, help="the branch Claude Code worked on"
    )
    reporting.add_argument(
        "--result", default="", help="the JSON Claude Code returned, with its reason"
    )
    reporting.add_argument(
        "--claude-outcome", default="", help="how the Claude Code step ended"
    )
    reporting.add_argument("--run-url", help="the workflow run to link")
    reporting.set_defaults(run=report)

    args = parser.parse_args(argv)
    try:
        return int(args.run(args))
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
