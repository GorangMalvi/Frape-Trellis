# Sprint — command cheat-sheet

Day-to-day commands for the dev environment. For standing up a bench from
nothing (fresh machine, new contributor), see `DEPLOYMENT.md`.

Rules of thumb:

- Backend `.py` changes reload automatically; **frontend changes need a build**.
- Build the frontend **inside the container**, never on the host (host
  `node_modules` are Linux/rollup-specific and fail on macOS).
- After a `docker restart`, `bench start` is gone — relaunch it.

---

## Dev environment — `development.localhost:8000`

Run from the **frappe_docker checkout root**:

```bash
# START (two steps)
docker compose -f .devcontainer/docker-compose.yml up -d
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bench start

# STOP
docker compose -f .devcontainer/docker-compose.yml stop

# health check
curl http://development.localhost:8000/api/method/ping     # → pong
```

URLs: app `http://development.localhost:8000/sprint` · Desk `/desk`

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
# graceful container restart (NEVER pkill -9), then bench start again
docker restart devcontainer-frappe-1
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bench start
```

## Data note

`Analyst Space` holds **real migrated data** (~131 cards) — not disposable.
Use **Dev Task** for demos and destructive testing.
