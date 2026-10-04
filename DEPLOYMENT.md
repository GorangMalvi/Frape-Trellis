# Sprint — Setup Guide (from scratch)

Get Sprint running from nothing: its own Frappe bench, database, and site.
**Lean by design — only Frappe + Sprint** (Sprint has zero dependency on
ERPNext/HRMS/CRM, so we never install them).

For contributors: this is how you stand up a local dev environment, load demo data,
and start hacking.

---

## Prerequisites
- **Docker** (Desktop on Mac / Engine on Linux), ~8 GB RAM for the first build.
- **Git** + access to `github.com/manask20/Sprint` — it's **private**, so you must be
  invited as a collaborator (then clone with your *own* GitHub credentials).
- Frappe **v16**, MariaDB 10.6+, Node 18/20 (all provided by the frappe_docker image).

## How the pieces fit (the ordering)
The Frappe framework is never modified — Sprint is an **app layered on top** of a
bench. Setup is **base-first, app-last**:
```
1. Docker
2. frappe_docker  (the dev harness)
3. Frappe bench + site
4. get the Sprint app        ← the app arrives here, not before
5. build + seed + run
```

---

## 1. Clone the frappe_docker harness
```bash
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker
cp -R devcontainer-example .devcontainer
cp -R development/vscode-example development/.vscode
```

## 2. Start the containers
```bash
docker compose -f .devcontainer/docker-compose.yml up -d
# -> devcontainer-frappe-1, devcontainer-mariadb-1, devcontainer-redis-*
```

## 3. Bootstrap a lean bench + site (Frappe only)
The stock `apps-example.json` installs ERPNext — we don't want it. Feed the installer
an empty apps list so only Frappe is pulled:
```bash
docker exec -w /workspace/development devcontainer-frappe-1 bash -lc 'echo "[]" > apps.json'
docker exec -w /workspace/development devcontainer-frappe-1 python installer.py -j apps.json
```
Creates `frappe-bench` (Frappe v16, **no ERPNext**) + site `development.localhost`
(admin password `admin`, MariaDB root `123`), developer mode on. ~5–10 min.

## 4. Add the Sprint app
Clone into the bench's `apps/` on the **host** (uses your own Git credentials). The
folder **must be named `sprint`** (the app's module name), not `Sprint`:
```bash
git clone git@github.com:manask20/Sprint.git \
  development/frappe-bench/apps/sprint        # or the https URL

docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 bash -lc '
  ./env/bin/pip install -e apps/sprint
  printf "frappe\nsprint\n" > sites/apps.txt          # full rewrite; a bare >> can glue "frappesprint"
  bench --site development.localhost install-app sprint
  bench --site development.localhost migrate           # fires after_migrate ensure_* + Sprint Manager role
'
```

## 5. Build assets & run
```bash
docker exec -w /workspace/development/frappe-bench/apps/sprint/frontend devcontainer-frappe-1 bash -lc '
  export NODE_OPTIONS="--max-old-space-size=4096"
  yarn install
  yarn build --base=/assets/sprint/frontend/
'
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 bench build --app sprint
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bench start
```
Open **http://development.localhost:8000/sprint** (Desk at `/desk`, login
`Administrator` / `admin`). Verify: `curl http://development.localhost:8000/api/method/ping` → `pong`.

---

## 6. Load demo / seed data

A fresh site is **empty** — install + migrate create the *schema*, not content. Sprint
ships an **anonymized demo dataset** (`sprint/demo_data.json`); seed it to get realistic
spaces, cards, and demo users to explore:
```bash
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost execute sprint.demo.seed_demo_data
```
Creates the demo users + spaces + cards from the shipped snapshot. **Idempotent** —
skips anything that already exists, safe to re-run.

Prefer a tiny starter instead? This makes one demo space (a "Dev Task" board with a few
cards, no data file needed):
```bash
docker exec -w /workspace/development/frappe-bench devcontainer-frappe-1 \
  bench --site development.localhost execute sprint.setup.setup_demo
```

> **Maintainers:** regenerate the shipped snapshot from a populated site with
> `bench --site <site> execute sprint.demo.export_demo_data` — it scrubs real names/company
> before writing `demo_data.json`. Commit the refreshed file.

---

## Daily usage
```bash
# start (after a reboot / Docker restart)
docker compose -f .devcontainer/docker-compose.yml up -d
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bench start

# stop
docker compose -f .devcontainer/docker-compose.yml stop
```
`bench start` is the dev server (auto-reloads backend on `.py` changes). You only need
to **rebuild the frontend** after editing `frontend/src`:
```bash
docker exec -w /workspace/development/frappe-bench/apps/sprint/frontend devcontainer-frappe-1 \
  bash -lc 'yarn build --base=/assets/sprint/frontend/'
```
…then hard-refresh the browser.

---

## Production (optional — self-hosting your own instance)
Same as steps 1–5 on a server, with these changes:
- **Private repo:** use a read-only **SSH deploy key** for the clone/get-app — never a PAT.
- **Skip the build spike:** the repo commits prebuilt frontend assets, so on a small box
  you can ship those instead of running the ~4 GB `yarn build`.
- **Real process manager:** replace `bench start` with `bench setup production frappe`
  (supervisor + nginx) and `bench --site <site> scheduler enable`.
- Point your domain / reverse proxy at the web port; terminate HTTPS at the proxy.
- A **4 GB / 2 vCPU** VM comfortably runs lean Frappe + Sprint (~2–2.5 GB at runtime).

---

## Gotchas
- **Lean = empty `apps.json` (`[]`).** The stock `apps-example.json` installs ERPNext,
  which Sprint doesn't need.
- **`apps.txt` needs trailing newlines** — rewrite with `printf`, never `echo >>` onto a
  file with no final newline (yields `frappesprint` → `ModuleNotFoundError`).
- **Fresh site is empty** — run the seeder (§6) or you'll see no spaces.
- **Build the frontend *inside* the container** — host `node_modules` are Linux/rollup-
  specific and fail on macOS.
- **Frappe must be `version-16`.**
