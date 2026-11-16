#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Collect what the Product Manager workflow reads, and open what it proposes.

The workflow runs the two commands around Claude Code:

``collect``  write every existing issue to a file, so nothing is proposed
             twice, and print the version the proposals are made on.
``open``     read the proposals, five features and up to five bug fixes, as
             the JSON the workflow's schema describes, and open an issue for
             each with ``gh``, in the sections of the repository's issue
             templates. An issue is labelled with its type, ``Triage`` and its
             priority; a proposal whose title an issue already has is skipped.

In GitHub Actions the repository, the step outputs and the run summary come
from the environment; by hand, options name them.
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

ROOT = Path(__file__).resolve().parent.parent
PRIORITIES = ("High", "Medium", "Low")
FEATURES = 5
MAX_BUGS = 5
TITLE_PREFIX = re.compile(r"^\[(bug|feature request)\]:\s*", re.IGNORECASE)

Proposal = dict[str, Any]


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


def collect(args: argparse.Namespace) -> int:
    """Write the existing issues to a file and print the version."""
    repo = ["--repo", args.repo] if args.repo else []
    listed = json.loads(
        gh(
            "issue",
            "list",
            *repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,title,state,labels",
        )
    )
    issues = [
        {**issue, "labels": [label["name"] for label in issue["labels"]]}
        for issue in listed
    ]
    args.output.write_text(json.dumps(issues, indent=2) + "\n")
    print(f"Wrote {len(issues)} issues to {args.output}")

    git = shutil.which("git")
    commit = ""
    if git:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [git, "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()
    version = (ROOT / "VERSION").read_text().strip()
    line = f"version={version} ({commit})\n" if commit else f"version={version}\n"
    print(line, end="")
    if args.github_output:
        with args.github_output.open("a") as output:
            output.write(line)
    return 0


def load_proposals(source: str) -> tuple[list[Proposal], list[Proposal], str]:
    """Read and validate the proposals; return features, bugs and the shortfall."""
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    if not text.strip():
        raise RuntimeError("There are no proposals to read")
    try:
        proposals = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"The proposals are not valid JSON: {e}") from e
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
    workflow = f"[Product Manager]({run_url})" if run_url else "Product Manager"
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


def open_issues(args: argparse.Namespace) -> list[str]:
    """Open the issues; return the lines of the summary table."""
    features, bugs, shortfall = load_proposals(args.proposals)
    repo = ["--repo", args.repo] if args.repo else []
    existing = json.loads(
        gh(
            "issue",
            "list",
            *repo,
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
        ("Feature Request", features, lambda p: feature_body(p, args.run_url)),
        ("Bug", bugs, lambda p: bug_body(p, args.version, args.run_url)),
    ]
    for label, proposals, render in kinds:
        for proposal in proposals:
            title = re.sub(r"\s+", " ", proposal["title"]).strip()
            priority = proposal["priority"]
            if normalize(title) in seen:
                print(f"Skipped, an issue already has this title: {title}")
                rows.append(f"| {label} | {priority} | skipped, duplicate: {title} |")
                continue
            seen.add(normalize(title))
            labels = [label, "Triage", f"{priority} Priority"]
            if args.dry_run:
                print(f"Would open '[{label}]: {title}' labelled {', '.join(labels)}")
                print(f"{render(proposal)}\n")
                rows.append(f"| {label} | {priority} | not opened, dry run: {title} |")
                continue
            url = gh(
                "issue",
                "create",
                *repo,
                "--title",
                f"[{label}]: {title}",
                "--body",
                render(proposal),
                *[option for name in labels for option in ("--label", name)],
            )
            print(f"Opened {url}")
            rows.append(f"| {label} | {priority} | {url} |")

    if len(bugs) < MAX_BUGS:
        reason = shortfall or "no reason given"
        note = f"Only {len(bugs)} bug(s) could be reproduced: {reason}"
        print(note)
        rows.extend(["", note])
    return rows


def open_command(args: argparse.Namespace) -> int:
    """Open the issues and append the summary table, if asked."""
    rows = open_issues(args)
    if args.summary:
        with args.summary.open("a") as summary:
            summary.write("## Proposals\n\n" + "\n".join(rows) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a command from the command line; return the exit code."""
    parser = argparse.ArgumentParser(
        description="Collect what the Product Manager reads, open what it proposes."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="the repository, OWNER/NAME (default: $GITHUB_REPOSITORY, "
        "or the one gh infers)",
    )

    collecting = commands.add_parser(
        "collect", parents=[common], help="write the existing issues to a file"
    )
    collecting.add_argument(
        "--output", required=True, type=Path, help="the JSON file to write"
    )
    collecting.add_argument(
        "--github-output",
        type=Path,
        default=env_path("GITHUB_OUTPUT"),
        help="a file to append the version output to (default: $GITHUB_OUTPUT)",
    )
    collecting.set_defaults(run=collect)

    opening = commands.add_parser(
        "open", parents=[common], help="open an issue for each proposal"
    )
    opening.add_argument(
        "proposals", help="the JSON file holding the proposals, or - for stdin"
    )
    opening.add_argument(
        "--version",
        default=(ROOT / "VERSION").read_text().strip(),
        help="the version a bug was reproduced on (default: the VERSION file)",
    )
    opening.add_argument("--run-url", help="the workflow run to link from each issue")
    opening.add_argument(
        "--summary",
        type=Path,
        default=env_path("GITHUB_STEP_SUMMARY"),
        help="a Markdown file to append the summary table to "
        "(default: $GITHUB_STEP_SUMMARY)",
    )
    opening.add_argument(
        "--dry-run",
        action="store_true",
        help="print the issues instead of opening them",
    )
    opening.set_defaults(run=open_command)

    args = parser.parse_args(argv)
    try:
        return int(args.run(args))
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
