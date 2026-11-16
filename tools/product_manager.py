#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Collect what the Product Manager workflows read, and apply what they return.

The New Ideas and the Grooming workflow run the commands around Claude Code:

``collect``  write the issues to a file: every issue ever opened, so New Ideas
             proposes nothing twice, or the open ones with their text, for
             Grooming to judge. Also print the version of the checkout.
``open``     for New Ideas: read the proposals, five features and up to five
             bug fixes, and open an issue for each with ``gh``, in the
             sections of the repository's issue templates. An issue is
             labelled with its type, ``Triage`` and its priority; a proposal
             whose title an issue already has is skipped.
``groom``    for Grooming: read the labels and the priority each open issue
             should have, and change the issues that differ.

In GitHub Actions the repository, the step outputs and the run summary come
from the environment; by hand, options name them.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import click
from common import (
    append,
    gh,
    git,
    main,
    output_option,
    repo_option,
    repository,
    summary_option,
)

ROOT = Path(__file__).resolve().parent.parent
PRIORITIES = ("High", "Medium", "Low")
# The labels Grooming decides, besides the priority: what an issue is and what
# it touches. It leaves every other label alone, Triage and Planned above all,
# which only a maintainer sets or removes.
GROOMED_LABELS = (
    "Bug",
    "Feature Request",
    "Enhancement",
    "Question",
    "Documentation",
    "Security",
    "Test",
    "Developer Experience",
    "Dependencies",
)
FEATURES = 5
MAX_BUGS = 5
TITLE_PREFIX = re.compile(r"^\[(bug|feature request)\]:\s*", re.IGNORECASE)

Proposal = dict[str, Any]


@click.group()
def cli() -> None:
    """Collect what the Product Manager workflows read, apply what they return."""


@cli.command()
@repo_option
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="The JSON file to write the issues to.",
)
@click.option(
    "--state",
    type=click.Choice(["all", "open"]),
    default="all",
    show_default=True,
    help="The issues to write: every one ever opened, or the open ones.",
)
@click.option("--with-body", is_flag=True, help="Write the text of each issue as well.")
@output_option
def collect(
    repo: str | None,
    output: Path,
    state: str,
    with_body: bool,
    github_output: Path | None,
) -> None:
    """Write the issues to a file and print the version."""
    fields = "number,title,state,labels" + (",body" if with_body else "")
    listed = json.loads(
        gh(
            "issue",
            "list",
            "--repo",
            repository(repo),
            "--state",
            state,
            "--limit",
            "1000",
            "--json",
            fields,
        )
    )
    issues = [
        {**issue, "labels": [label["name"] for label in issue["labels"]]}
        for issue in listed
    ]
    output.write_text(json.dumps(issues, indent=2) + "\n")
    click.echo(f"Wrote {len(issues)} issues to {output}")

    version = (ROOT / "VERSION").read_text().strip()
    commit = git("rev-parse", "--short", "HEAD", cwd=ROOT)
    append(github_output, f"version={version} ({commit})\n")


def read_json(source: str, what: str) -> Any:
    """Read ``what`` as JSON from a file, or from stdin when ``source`` is -."""
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    if not text.strip():
        raise RuntimeError(f"There is no {what} to read")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"The {what} is not valid JSON: {e}") from e


def load_proposals(source: str) -> tuple[list[Proposal], list[Proposal], str]:
    """Read and validate the proposals; return features, bugs and the shortfall."""
    proposals = read_json(source, "list of proposals")
    features = proposals.get("features", [])
    bugs = proposals.get("bugs", [])
    if len(features) != FEATURES or len(bugs) > MAX_BUGS:
        raise RuntimeError(
            f"Expected {FEATURES} features and up to {MAX_BUGS} bugs, "
            f"got {len(features)} and {len(bugs)}"
        )
    for proposal in [*features, *bugs]:
        if proposal.get("priority") not in PRIORITIES:
            raise RuntimeError(
                f"'{proposal.get('title')}' has a priority other than "
                f"{', '.join(PRIORITIES)}"
            )
    return features, bugs, proposals.get("bugs_shortfall_reason", "")


def normalize(title: str) -> str:
    """Reduce a title to what makes two issues the same proposal."""
    return re.sub(r"\s+", " ", TITLE_PREFIX.sub("", title.strip())).lower()


def criteria(items: list[str]) -> str:
    """Render the acceptance criteria as a task list."""
    return "\n".join(f"- [ ] {item}" for item in items)


def footer(run_url: str | None) -> str:
    """Say where the issue comes from and what to do with it."""
    workflow = f"[New Ideas]({run_url})" if run_url else "New Ideas"
    return (
        "---\n"
        f"_Proposed by the {workflow} workflow. Triage it, and label it "
        "`Planned` to have the Engineer workflow implement it._"
    )


def feature_body(proposal: Proposal, run_url: str | None) -> str:
    """Render a feature in the sections of the Feature Request template."""
    return "\n\n".join(
        [
            f"### Description\n\n{proposal['description']}",
            f"### Use Case\n\n{proposal['use_case']}",
            f"### Alternatives Considered\n\n{proposal['alternatives'] or '_None._'}",
            f"### Acceptance Criteria\n\n{criteria(proposal['acceptance_criteria'])}",
            footer(run_url),
        ]
    )


def bug_body(proposal: Proposal, version: str, run_url: str | None) -> str:
    """Render a bug in the sections of the Bug Report template."""
    log = proposal["log_output"].strip()
    log_section = f"```shell\n{log}\n```" if log else "_None._"
    return "\n\n".join(
        [
            f"### What happened?\n\n{proposal['what_happened']}",
            f"### Expected Behavior\n\n{proposal['expected_behavior']}",
            f"### Steps to Reproduce\n\n{proposal['steps_to_reproduce']}",
            f"### Version\n\n{version}",
            "### Operating System\n\nLinux",
            f"### Relevant Log Output\n\n{log_section}",
            f"### Acceptance Criteria\n\n{criteria(proposal['acceptance_criteria'])}",
            footer(run_url),
        ]
    )


@cli.command("open")
@repo_option
@click.argument("proposals")
@click.option(
    "--version",
    default=(ROOT / "VERSION").read_text().strip(),
    show_default="the VERSION file",
    help="The version a bug was reproduced on.",
)
@click.option("--run-url", help="The workflow run to link from each issue.")
@summary_option
@click.option(
    "--dry-run", is_flag=True, help="Print the issues instead of opening them."
)
def open_issues(
    repo: str | None,
    proposals: str,
    version: str,
    run_url: str | None,
    summary: Path | None,
    dry_run: bool,
) -> None:
    """Open an issue for each proposal in PROPOSALS, a JSON file or - for stdin."""
    features, bugs, shortfall = load_proposals(proposals)
    repo_args = ["--repo", repository(repo)]
    existing = json.loads(
        gh(
            "issue",
            "list",
            *repo_args,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "title",
        )
    )
    seen = {normalize(issue["title"]) for issue in existing}

    rows = ["| Type | Priority | Issue |", "|---|---|---|"]
    kinds = [
        ("Feature Request", features, lambda p: feature_body(p, run_url)),
        ("Bug", bugs, lambda p: bug_body(p, version, run_url)),
    ]
    for label, items, render in kinds:
        for proposal in items:
            title = re.sub(r"\s+", " ", proposal["title"]).strip()
            priority = proposal["priority"]
            if normalize(title) in seen:
                click.echo(f"Skipped, an issue already has this title: {title}")
                rows.append(f"| {label} | {priority} | skipped, duplicate: {title} |")
                continue
            seen.add(normalize(title))
            labels = [label, "Triage", f"{priority} Priority"]
            if dry_run:
                click.echo(
                    f"Would open '[{label}]: {title}' labelled {', '.join(labels)}"
                )
                click.echo(f"{render(proposal)}\n")
                rows.append(f"| {label} | {priority} | not opened, dry run: {title} |")
                continue
            url = gh(
                "issue",
                "create",
                *repo_args,
                "--title",
                f"[{label}]: {title}",
                "--body",
                render(proposal),
                *[option for name in labels for option in ("--label", name)],
            )
            click.echo(f"Opened {url}")
            rows.append(f"| {label} | {priority} | {url} |")

    if len(bugs) < MAX_BUGS:
        reason = shortfall or "no reason given"
        note = f"Only {len(bugs)} bug(s) could be reproduced: {reason}"
        click.echo(note)
        rows.extend(["", note])
    if summary:
        with summary.open("a") as file:
            file.write("## Proposals\n\n" + "\n".join(rows) + "\n")


@cli.command()
@repo_option
@click.argument("grooming")
@summary_option
@click.option(
    "--dry-run", is_flag=True, help="Print the changes instead of making them."
)
def groom(repo: str | None, grooming: str, summary: Path | None, dry_run: bool) -> None:
    """Label the open issues as GROOMING says, a JSON file or - for stdin.

    GROOMING gives, for each open issue, the labels saying what it is and
    what it touches, and its priority. Only an issue that differs is changed,
    and only in those labels: every other label is left alone.
    """
    wanted = read_json(grooming, "grooming").get("issues", [])
    for issue in wanted:
        labels = issue.get("labels") or []
        unknown = [label for label in labels if label not in GROOMED_LABELS]
        if not labels or unknown or issue.get("priority") not in PRIORITIES:
            raise RuntimeError(
                f"#{issue.get('number')} needs at least one label among "
                f"{', '.join(GROOMED_LABELS)}, and a priority among "
                f"{', '.join(PRIORITIES)}"
            )

    repo = repository(repo)
    listed = json.loads(
        gh(
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "1000",
            "--json",
            "number,labels",
        )
    )
    current = {
        issue["number"]: {label["name"] for label in issue["labels"]}
        for issue in listed
    }
    groomed = {*GROOMED_LABELS, *(f"{priority} Priority" for priority in PRIORITIES)}

    rows = []
    for issue in wanted:
        number = issue["number"]
        if number not in current:
            click.echo(f"Skipped #{number}: it is not an open issue")
            continue
        target = {*issue["labels"], f"{issue['priority']} Priority"}
        add = sorted(target - current[number])
        remove = sorted((current[number] & groomed) - target)
        if not add and not remove:
            continue
        if not dry_run:
            gh(
                "issue",
                "edit",
                str(number),
                "--repo",
                repo,
                *[option for label in add for option in ("--add-label", label)],
                *[option for label in remove for option in ("--remove-label", label)],
            )
        change = "; ".join(
            part
            for part in (
                f"added {', '.join(add)}" if add else "",
                f"removed {', '.join(remove)}" if remove else "",
            )
            if part
        )
        reason = re.sub(r"\s+", " ", issue.get("reason") or "").replace("|", "/")
        click.echo(f"{'Would change' if dry_run else 'Changed'} #{number}: {change}")
        rows.append(f"| #{number} | {change} | {reason} |")

    if rows:
        table = ["| Issue | Change | Reason |", "|---|---|---|", *rows]
        text = "## Grooming\n\n" + "\n".join(table) + "\n"
    else:
        text = "## Grooming\n\nEvery open issue is already labelled as proposed.\n"
        click.echo("Every open issue is already labelled as proposed")
    if dry_run:
        text = text.replace("## Grooming\n", "## Grooming, dry run\n")
    if summary:
        with summary.open("a") as file:
            file.write(text)


if __name__ == "__main__":
    sys.exit(main(cli))
