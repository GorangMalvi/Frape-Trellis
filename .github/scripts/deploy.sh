#!/usr/bin/env bash
# Runs ON the target server (piped over SSH by .github/workflows/deploy.yml).
#
# Expects (exported by the workflow):
#   BENCH_PATH   e.g. /home/frappe/frappe-bench
#   SITE_NAME    e.g. sprint.example.com
#   DEPLOY_REF   commit SHA to deploy (already pushed to origin)
#   WEB_PORT     optional, gunicorn port for the health check (default 8000)
#
# Assumes apps/sprint is a git clone of this repo with a read-only deploy key
# as its origin, and the bench runs under supervisor (`bench setup production`).
set -euo pipefail

: "${BENCH_PATH:?}" "${SITE_NAME:?}" "${DEPLOY_REF:?}"
APP_DIR="$BENCH_PATH/apps/sprint"
cd "$BENCH_PATH"

PREV_REF="$(git -C "$APP_DIR" rev-parse HEAD)"
echo "==> Deploying sprint $PREV_REF -> $DEPLOY_REF on $SITE_NAME"

maintenance_off() { bench --site "$SITE_NAME" set-maintenance-mode off || true; }

rollback() {
	echo "!!> Deploy failed — restoring code to $PREV_REF"
	git -C "$APP_DIR" checkout --force --detach "$PREV_REF"
	bench build --app sprint || true
	bench restart || true
	maintenance_off
	echo "!!> Code rolled back. The DB was NOT restored automatically; the pre-deploy"
	echo "!!> backup is in sites/$SITE_NAME/private/backups if a migration needs undoing."
	exit 1
}
trap rollback ERR

echo "==> Fetching"
git -C "$APP_DIR" fetch --prune --tags origin
git -C "$APP_DIR" cat-file -e "$DEPLOY_REF^{commit}"

echo "==> Backup (database + files)"
bench --site "$SITE_NAME" backup --with-files

echo "==> Maintenance mode on"
bench --site "$SITE_NAME" set-maintenance-mode on

echo "==> Checkout"
git -C "$APP_DIR" checkout --force --detach "$DEPLOY_REF"

echo "==> Python requirements"
bench setup requirements --python sprint

echo "==> Migrate (runs after_migrate ensure_* hooks)"
bench --site "$SITE_NAME" migrate

echo "==> Assets (frontend is prebuilt in the repo; this links/bundles Frappe-side assets)"
bench build --app sprint

echo "==> Restart"
bench restart
bench --site "$SITE_NAME" set-maintenance-mode off

echo "==> Health check (http://127.0.0.1:${WEB_PORT:-8000}, Host: $SITE_NAME)"
healthy() {
	for _ in $(seq 1 12); do
		curl -fsS -H "Host: $SITE_NAME" "http://127.0.0.1:${WEB_PORT:-8000}/api/method/ping" | grep -q pong && return 0
		sleep 5
	done
	return 1
}
healthy || { echo "!!> Health check failed"; false; }

trap - ERR
echo "==> Deployed $DEPLOY_REF"
