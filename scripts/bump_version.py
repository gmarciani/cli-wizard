#!/usr/bin/env python3
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Bump the project version.

Writes the version to ``VERSION`` and opens its section in ``CHANGELOG.md``,
which is what the Bump Version workflow commits.
"""

import argparse
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
CHANGELOG_TITLE = "# Changelog\n"


def bump_version(root: Path, version: str) -> list[Path]:
    """Bump the project under ``root`` to ``version``; return the files changed.

    What is already at ``version`` is left as it is, with a warning.
    """
    if not VERSION_PATTERN.fullmatch(version):
        raise RuntimeError(f"Invalid version '{version}', expected X.Y.Z")
    changed = []
    version_file = root / "VERSION"
    if version_file.read_text().strip() == version:
        print(
            f"Warning: {version_file.name} is already {version}, leaving it as it is",
            file=sys.stderr,
        )
    else:
        version_file.write_text(f"{version}\n")
        changed.append(version_file)
    changelog = root / "CHANGELOG.md"
    if _open_changelog_section(changelog, version):
        changed.append(changelog)
    return changed


def _open_changelog_section(changelog: Path, version: str) -> bool:
    """Insert a ``## version`` section at the top of the changelog, once."""
    content = changelog.read_text()
    if re.search(rf"^## {re.escape(version)}\s*$", content, re.MULTILINE):
        print(
            f"Warning: {changelog.name} already has a '## {version}' section, "
            "leaving it as it is",
            file=sys.stderr,
        )
        return False
    if not content.startswith(CHANGELOG_TITLE):
        raise RuntimeError(
            f"{changelog} does not start with '{CHANGELOG_TITLE.strip()}'"
        )
    body = content[len(CHANGELOG_TITLE) :].lstrip("\n")
    changelog.write_text(f"{CHANGELOG_TITLE}\n## {version}\n\n\n{body}")
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the bump from the command line; return the exit code."""
    parser = argparse.ArgumentParser(description="Bump the project version.")
    parser.add_argument("version", help="the target version, X.Y.Z")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="the project directory (default: the repository root)",
    )
    args = parser.parse_args(argv)
    try:
        changed = bump_version(args.root, args.version)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    for path in changed:
        print(f"Updated {path.relative_to(args.root)}")
    if not changed:
        print(f"Nothing to do: the project is already at version {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
