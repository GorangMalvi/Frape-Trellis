# Sprint

A ClickUp-style work-management app: a custom **Vue 3 + frappe-ui SPA** (served at `/sprint`)
over a **Frappe v16** backend. Boards / lists / calendars, saved views, subtasks, ticketing
spaces, cross-space Home + notification inbox, per-space dashboards, card templates,
@mentions, and a when→if→then **automation engine**. Fully responsive — works on phones.

**The core idea:** each Frappe DocType *is* a Space and its records are the cards. The UI is a
generic, meta-driven renderer; a thin `SP Space` registry tells it which field is the
title/bucket/assignee/due/badge. Add a field in Desk (or the in-app Fields dialog) and the UI
shows it automatically.

## 🤖 Working on this repo with an AI agent?

Point it at these files, in this order — they are written for exactly that purpose:

1. **`CLAUDE.md`** — session entry point: what exists, critical rules, build/verify commands.
2. **`PRODUCT_OVERVIEW.md`** — what the product is, the architecture, the full feature set.
3. **`TECHNICAL_DICTIONARY.md`** — glossary, file map, API surface, conventions, gotchas.

The non-negotiables (full list in `TECHNICAL_DICTIONARY.md` §7): build the frontend **inside
the bench environment** (host `node_modules` are platform-specific); card writes must go
through Sprint's endpoints in `sprint/api.py` (Desk/script edits bypass notifications and
automations); schema changes are idempotent `ensure_*` functions in `sprint/setup.py` run via
the `after_migrate` hook; never name a field `order`; Lucide icons only as `<LucideX />`
template tags.

## Setup

Sprint is a Frappe app — it needs a working [bench](https://github.com/frappe/bench). The
easiest path is the [frappe_docker devcontainer](https://github.com/frappe/frappe_docker/blob/main/docs/development.md);
any Frappe v16 bench works.

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/manask20/Sprint
bench --site yoursite.localhost install-app sprint
bench --site yoursite.localhost migrate     # runs the ensure_* migrations
bench start
```

Open `http://yoursite.localhost:8000/sprint`. Sprint has its own in-app login and user
onboarding (users never see Frappe Desk); sign in with your site's Administrator account
first. Structural rights (creating spaces, fields, automations) belong to Administrator or
anyone with the **Sprint Manager** role.

Optional demo data — a full anonymized workspace snapshot (6 spaces, ~145 cards
with buckets, custom fields, subtasks, assignees, and two ticketing spaces):

```bash
bench --site yoursite.localhost execute sprint.demo.seed_demo_data
```

It is idempotent (spaces that already exist are skipped) and creates a handful
of `*@example.com` placeholder users for the assignee fields.

## Development workflow

- **Backend** (`sprint/api.py`, `sprint/automation.py`, `sprint/setup.py`): edits hot-reload
  under `bench start`. After changing `hooks.py`, restart bench.
- **Frontend** (`frontend/src`): pre-built assets are committed, so the app works without a
  node toolchain. To change the UI, rebuild from `frontend/` **in the same environment where
  `yarn install` ran** (inside the devcontainer, not a macOS host):

  ```bash
  cd frontend && yarn install
  yarn build        # outputs hashed assets into sprint/public/frontend
  ```

  Then hard-refresh `/sprint`. (`yarn dev` gives a Vite dev server with frappe-ui's proxy if
  you prefer live reload.)
- **Tests**: `bench --site yoursite.localhost run-tests --module sprint.tests.test_api` and
  `…tests.test_automation` (requires `"allow_tests": true` in the site config).

## Repo layout

```
sprint/                  # Frappe app (Python)
  api.py                 #   the whitelisted API surface — all card writes funnel here
  automation.py          #   automation engine (rules, executors, scheduler jobs)
  setup.py               #   data model + idempotent ensure_* migrations + demo seed
  hooks.py               #   SPA route, after_migrate, scheduler_events
  sprint/doctype/        #   SP Space, SP Bucket, SP View, SP Automation, …
  www/sprint.html        #   production SPA shell
frontend/                # Vue 3 + frappe-ui SPA (Vite, Tailwind)
  src/pages/             #   Board, Home, Dashboard, Automations, DataPage, TicketIntake
  src/components/        #   BoardView / ListView / CalendarView, TaskDrawer, dialogs
  src/lib + composables  #   board logic, formatting, dnd, useOverlay, useBreakpoint
```

## Contributing

Branching, merge rules, CI/CD, releases and rollback are in **`CONTRIBUTING.md`**.
In short: branch from `dev` → PR (CI must pass) → squash-merge to `dev` (deploys to staging)
→ release PR `dev` → `main` (approval, merge commit; deploys to production).

`pre-commit` handles formatting/linting (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/sprint && pre-commit install
```

## License

MIT
