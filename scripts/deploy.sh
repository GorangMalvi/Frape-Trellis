#!/usr/bin/env bash
# Deploy Sprint to a server from your machine (no CI service needed).
#
#   bash scripts/deploy.sh staging              # deploys origin/dev
#   bash scripts/deploy.sh production           # deploys origin/main
#   bash scripts/deploy.sh production v0.1.0   # deploy a tag/SHA (rollback)
#
# Server details live in .deploy/<env>.env (git-ignored — never commit it):
#   SSH_HOST=203.0.113.10
#   SSH_USER=frappe
#   SSH_PORT=22                         # optional
#   SSH_KEY=~/.ssh/sprint_deploy        # optional, else your default key/agent
#   BENCH_PATH=/home/frappe/frappe-bench
#   SITE_NAME=sprint.example.com
#   WEB_PORT=8000                       # optional
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_NAME="${1:-}"
case "$ENV_NAME" in
	staging) DEFAULT_REF=origin/dev ;;
	production) DEFAULT_REF=origin/main ;;
	*) echo "usage: bash scripts/deploy.sh <staging|production> [ref]"; exit 2 ;;
esac

CONF=".deploy/$ENV_NAME.env"
[ -f "$CONF" ] || { echo "Missing $CONF — see the header of this script."; exit 2; }
# shellcheck disable=SC1090
source "$CONF"
: "${SSH_HOST:?}" "${SSH_USER:?}" "${BENCH_PATH:?}" "${SITE_NAME:?}"

git fetch --quiet --prune --tags origin
REF="${2:-$DEFAULT_REF}"
SHA="$(git rev-parse --verify "$REF^{commit}")"

# The server pulls from GitHub, so the commit must already be pushed — and
# production only ever runs code that has been merged to main.
git merge-base --is-ancestor "$SHA" origin/dev 2>/dev/null \
	|| git merge-base --is-ancestor "$SHA" origin/main \
	|| { echo "!! $REF ($SHA) is not on origin/dev or origin/main — push/merge it first."; exit 1; }
if [ "$ENV_NAME" = production ] && ! git merge-base --is-ancestor "$SHA" origin/main; then
	echo "!! Production deploys must come from main (merge a release PR first)."; exit 1
fi

echo "About to deploy to $ENV_NAME ($SSH_USER@$SSH_HOST, site $SITE_NAME):"
git log -1 --format='   %h %s (%an, %ar)' "$SHA"
read -r -p "Type the environment name to confirm: " answer
[ "$answer" = "$ENV_NAME" ] || { echo "Aborted."; exit 1; }

SSH_OPTS=(-p "${SSH_PORT:-22}")
[ -n "${SSH_KEY:-}" ] && SSH_OPTS+=(-i "${SSH_KEY/#\~/$HOME}")

ssh "${SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" \
	"BENCH_PATH='$BENCH_PATH' SITE_NAME='$SITE_NAME' DEPLOY_REF='$SHA' WEB_PORT='${WEB_PORT:-8000}' bash -s" \
	< scripts/remote-deploy.sh
