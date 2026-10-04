#!/usr/bin/env bash
# Entrypoint of the Sprint dev containers (see docker-compose.yml).
#
#   sprint-dev-entrypoint [backend]  first run: create bench + site + install Sprint;
#                                    after `up --build` with changed sources: refresh
#                                    deps, rebuild frontend, migrate; then `bench start`
#                                    (web :8000, socketio, worker, scheduler) plus the
#                                    Vite live-reload dev server (:8080).
set -euo pipefail

DEV=/workspace/development
BENCH="$DEV/frappe-bench"
APP="$BENCH/apps/sprint"
SITE="${SITE_NAME:-development.localhost}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-123}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
STAMP="$DEV/.sprint-build-id"

log() { printf '\033[1;34m[sprint-dev]\033[0m %s\n' "$*"; }

wait_for_db() {
	log "waiting for MariaDB…"
	until mariadb-admin ping -h mariadb -uroot -p"$DB_ROOT_PASSWORD" --silent 2>/dev/null; do sleep 2; done
}

bootstrap() {
	log "first run: creating a Frappe v16 bench (takes ~5-10 min)…"
	cd "$DEV"
	# apps/sprint already exists (it is the bind-mounted repo), hence --ignore-exist;
	# init would also pick it up and fail building its assets before it is
	# pip-installed, hence --skip-assets (built below, once sprint is installed).
	bench init --ignore-exist --skip-assets --skip-redis-config-generation \
		--frappe-branch "${FRAPPE_BRANCH:-version-16}" frappe-bench
	cd "$BENCH"
	bench set-config -g db_host mariadb
	bench set-config -g redis_cache redis://redis-cache:6379
	bench set-config -g redis_queue redis://redis-queue:6379
	bench set-config -g redis_socketio redis://redis-queue:6379
	bench set-config -gp developer_mode 1

	log "installing the sprint app…"
	./env/bin/pip install -q -e apps/sprint
	printf 'frappe\nsprint\n' > sites/apps.txt

	log "building Frappe assets…"
	bench build

	log "creating site $SITE…"
	# --force: a previous first run may have died after creating the database
	bench new-site "$SITE" --force --db-host mariadb --db-root-username root \
		--db-root-password "$DB_ROOT_PASSWORD" --mariadb-user-host-login-scope=% \
		--admin-password "$ADMIN_PASSWORD"
	bench --site "$SITE" install-app sprint
	bench --site "$SITE" set-config allow_tests true
	bench use "$SITE"

	if [ "${SEED_DEMO:-1}" = "1" ]; then
		log "seeding demo data…"
		bench --site "$SITE" execute sprint.demo.seed_demo_data
	fi
}

refresh() {
	log "sources changed since last build: refreshing…"
	cd "$BENCH"
	./env/bin/pip install -q -e apps/sprint
	(
		cd "$APP/frontend"
		export NODE_OPTIONS="--max-old-space-size=4096"
		yarn install --frozen-lockfile --non-interactive
		yarn build --base=/assets/sprint/frontend/
	)
	bench build --app sprint
	bench --site "$SITE" migrate
}

backend() {
	wait_for_db
	[ -f "$BENCH/sites/$SITE/site_config.json" ] || bootstrap

	# passwordless login (code + link printed to these logs) — dev only, see sprint/dev_login.py
	# (works on Sprint's /sprint/login and on Frappe's own /login "Login with Email Link")
	(
		cd "$BENCH"
		bench --site "$SITE" set-config --parse sprint_dev_login "${DEV_LOGIN:-1}" >/dev/null
		bench --site "$SITE" execute sprint.dev_login.sync_login_page >/dev/null
	)

	want="$(cat /opt/sprint-build-id)"
	have="$(cat "$STAMP" 2>/dev/null || true)"
	if [ "$want" != "$have" ]; then
		refresh
		echo "$want" > "$STAMP"
	else
		log "no source changes since last build (use 'docker compose up --build' after pulling/editing)"
	fi

	cd "$BENCH"
	# Run the Vite dev server as one more `bench start` (honcho) process so frontend and
	# backend start/stop/restart together. The loop keeps a Vite crash from making honcho
	# stop the whole bench. Windows/macOS bind mounts don't deliver file events: poll.
	sed -i '/^sprint_ui:/d' Procfile
	if [ "${VITE_DEV:-1}" = "1" ]; then
		echo "sprint_ui: bash -c 'cd apps/sprint/frontend && ([ -d node_modules/.bin ] || yarn install --frozen-lockfile --non-interactive); while true; do CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=500 yarn dev --host 0.0.0.0 --port 8080; sleep 3; done'" >> Procfile
		log "frontend (Vite, live reload) → http://localhost:8080/sprint"
	fi
	log "backend → http://localhost:8000/sprint  (Desk: /desk, Administrator / $ADMIN_PASSWORD)"
	exec bench start
}

case "${1:-backend}" in
	backend) backend ;;
	*) exec "$@" ;;
esac
