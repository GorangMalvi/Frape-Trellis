# Sprint — command cheat-sheet

Day-to-day commands for the dev environment. For standing up a bench from
nothing (fresh machine, new contributor), see `DEPLOYMENT.md`.

Rules of thumb:

- Backend `.py` changes reload automatically; **frontend changes need a build**.
- Build the frontend **inside the container**, never on the host (host
  `node_modules` are Linux/rollup-specific and fail on macOS).
- After a `docker restart`, `bench start` is gone — relaunch it.

---

## Dev environment — `localhost:8000`

Run from the **repo root** (`docker-compose.yml`, see `docker/dev/`):

```bash
docker compose up -d             # START backend (8000) + Vite live-reload frontend (8080)
docker compose up -d --build     # START + refresh: if app sources changed → yarn build, bench build, migrate
docker compose down              # STOP (volumes kept; down -v = wipe bench + DB)
docker compose logs -f frappe    # all logs (web, worker, socketio, Vite = sprint_ui)

curl http://localhost:8000/api/method/ping     # health check → pong

# sign in: request a code on the login page, then read it (and the login link) here
docker compose logs -f frappe | grep -A5 "SPRINT DEV LOGIN"
```

URLs: app `http://localhost:8000/sprint` · live-reload `http://localhost:8080/sprint` ·
Desk `/desk` (Administrator / admin). `development.localhost` works too.
First `up` bootstraps everything (~10 min). The container is still named
`devcontainer-frappe-1`, so the `docker exec` commands below are unchanged.
(The older two-step frappe_docker flow in `DEPLOYMENT.md` still works.)

## While developing (run from anywhere)

```bash
# rebuild the frontend after editing frontend/src (then hard-refresh /sprint)
docker exec devcontainer-frappe-1 bash -lc \
  'cd /workspace/development/frappe-bench/apps/sprint/frontend && yarn build --base=/assets/sprint/frontend/'

# run one-off backend functions (idempotent ensure_* migrations, seeding, …)
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost execute sprint.setup.setup_demo

# migrate (fires the after_migrate ensure_* hooks)
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost migrate
```

## Tests

```bash
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost run-tests --module sprint.tests.test_api
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost run-tests --module sprint.tests.test_automation
```

(Needs `allow_tests` in the site config.)

## If things wedge

```bash
# graceful restart (NEVER pkill -9) — bench start comes back on its own
docker compose restart frappe
```

## Data note

`Analyst Space` holds **real migrated data** (~131 cards) — not disposable.
Use **Dev Task** for demos and destructive testing.
