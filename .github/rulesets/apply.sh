#!/usr/bin/env bash
# Applies the repo's merge rules + settings to GitHub. Idempotent: re-run after
# editing any JSON here. Needs the GitHub CLI logged in as a repo admin (`gh auth login`).
#
#   bash .github/rulesets/apply.sh [owner/repo]
set -euo pipefail
cd "$(dirname "$0")"
REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
echo "==> $REPO"

echo "==> Repository merge settings"
gh api -X PATCH "repos/$REPO" --silent \
	-f default_branch=dev \
	-F allow_merge_commit=true \
	-F allow_squash_merge=true \
	-F allow_rebase_merge=false \
	-F allow_auto_merge=true \
	-F allow_update_branch=true \
	-F delete_branch_on_merge=true \
	-f squash_merge_commit_title=PR_TITLE \
	-f squash_merge_commit_message=PR_BODY \
	-f merge_commit_title=PR_TITLE \
	-f merge_commit_message=PR_BODY

echo "==> Rulesets"
for f in main-protect.json main-review.json dev.json release-tags.json; do
	name="$(node -e "console.log(JSON.parse(require('fs').readFileSync('$f','utf8')).name)")"
	id="$(gh api "repos/$REPO/rulesets" --paginate -q ".[] | select(.name == \"$name\") | .id")"
	if [ -n "$id" ]; then
		gh api -X PUT "repos/$REPO/rulesets/$id" --input "$f" --silent && echo "    updated: $name"
	else
		gh api -X POST "repos/$REPO/rulesets" --input "$f" --silent && echo "    created: $name"
	fi
done

echo "==> GitHub Actions: off (this repo uses no paid/automated CI)"
gh api -X PUT "repos/$REPO/actions/permissions" -F enabled=false --silent
for env in staging production; do
	gh api -X DELETE "repos/$REPO/environments/$env" --silent 2>/dev/null && echo "    removed environment: $env" || true
done

echo "==> Done."
