#!/usr/bin/env bash
# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License
#
# Draft the GitHub release of the current version.
#
# Takes no input: the version is read from VERSION and the release notes from
# its section in CHANGELOG.md, both already in place. A version that is
# already released, drafted, or tagged on origin is refused.

set -euo pipefail

fail() {
  echo "Error: $*" >&2
  exit 1
}

cd "$(dirname "${BASH_SOURCE[0]}")/.."

command -v gh >/dev/null || fail "gh is not installed, see https://cli.github.com"

version="$(tr -d '[:space:]' <VERSION)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Invalid version '$version' in VERSION"
tag="v$version"

# The lines between '## <version>' and the next '## ' heading, without the
# leading blank lines; awk exits 1 when the heading is missing.
notes="$(awk -v version="$version" '
  $1 == "##" && found { exit }
  $1 == "##" && $2 == version && NF == 2 { found = 1; next }
  found { print }
  END { exit !found }
' CHANGELOG.md | sed '/./,$!d')" ||
  fail "CHANGELOG.md has no '## $version' section, bump the version with scripts/bump_version.py first"
[[ -n "${notes//[[:space:]]/}" ]] ||
  fail "The '## $version' section of CHANGELOG.md is empty, write the release notes first"

is_draft="$(gh release list --limit 1000 --json tagName,isDraft \
  --jq ".[] | select(.tagName == \"$tag\") | .isDraft")"
if [[ -n "$is_draft" ]]; then
  url="$(gh release view "$tag" --json url --jq .url)"
  [[ "$is_draft" == true ]] &&
    fail "$tag already has a draft release: $url, edit it or delete it with 'gh release delete $tag'"
  fail "$tag is already released: $url"
fi

tag_ref="$(gh api "repos/{owner}/{repo}/git/matching-refs/tags/$tag" \
  --jq ".[] | select(.ref == \"refs/tags/$tag\") | .ref")"
[[ -z "$tag_ref" ]] ||
  fail "Tag $tag already exists on origin without a release, delete it with 'git push origin :refs/tags/$tag' if it was a mistake"

url="$(printf '%s\n' "$notes" | gh release create "$tag" \
  --title "$tag" \
  --target main \
  --notes-file - \
  --latest \
  --draft)"
echo "Drafted release $url"
