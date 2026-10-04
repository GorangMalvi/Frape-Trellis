# Sprint — start here (for AI sessions)

**Sprint** is a ClickUp-style work-management product: a custom Vue 3 +
frappe-ui SPA (served at `/sprint`) over a **Frappe** backend (v16, Desk at
`/desk`). Increasingly positioned as a B2B SaaS.

**Before doing anything, read these two files in this folder:**
- **`PRODUCT_OVERVIEW.md`** — what the product is, the architecture, the full feature set.
- **`TECHNICAL_DICTIONARY.md`** — glossary, file map, API surface, conventions, gotchas, build/dev workflow.

## The one idea to internalize
**Each DocType *is* a Space** — its records are the cards. The UI is a generic,
**meta-driven** renderer; a thin `SP Space` registry tells it which field is the
title/bucket/assignee/due/badge/etc. Add a field in Frappe Desk (or the in-app
Fields dialog) → the UI shows it automatically. Business logic belongs in Frappe
**Server Scripts** or Sprint's own endpoints, not scattered in the UI.

## What exists now (as of the automation engine — commit `2847794`)

**Backend** (`sprint/`):
- `api.py` — the main whitelisted surface: spaces, cards, buckets, views,
  fields, tickets, attachments, comments, Home/inbox, watchers, templates,
  import/export. Card writes funnel through mutation endpoints
  (`create_card`/`update_card`/`set_field`/`move_card`/`bulk_set`/`create_ticket`/`update_ticket`),
  each calling `_notify_card_changes(doc, reg, is_new)` post-save.
- `automation.py` — the automation engine (rules, executors, dispatch,
  scheduler jobs, endpoints, recipes). Dispatch piggybacks on
  `_notify_card_changes` + `add_comment`.
- `setup.py` — data model + idempotent `ensure_*` migrations (run automatically
  via the `after_migrate` hook); space creation; demo seed.
- `hooks.py` — SPA route rule, `after_migrate`, and `scheduler_events`.
- Doctypes: `SP Space` (registry), `SP Bucket`, `SP View`, `SP Space Access`,
  `SP Ticket Member`, `SP Template`, `SP Watcher`, `SP Automation`,
  `SP Automation Run`.
- Tests: `sprint/tests/test_api.py` (access/hardening) + `test_automation.py`.

**Frontend** (`frontend/src/`):
- Pages: `Board.vue` (per-space orchestrator), `Home.vue` (my-tasks + inbox),
  `Dashboard.vue`, `Automations.vue`, `DataPage.vue` (import/export),
  `TicketIntake.vue`. Views: Board / List / **Calendar** (when a space has a due field).
- Shared: `lib/board.js` (filter/sort/group + `matchFilter`), `lib/format.js`,
  `lib/automation.js`, `lib/users.js`, `lib/depends.js`; composables
  `useOverlay` (Esc stack + focus trap — use on every overlay), `useSpacePointers`,
  `useViewState`. Design tokens + dark mode in `index.css`.

**Feature set** (detail in PRODUCT_OVERVIEW): Board/List/Calendar, saved views,
subtasks, filters, bulk actions, command palette, ticketing spaces + per-space
access, Home (cross-space my-tasks + notification inbox), assignee/watcher
notifications, per-space dashboards, card templates, @mentions, and the
**automation engine** (when→if→then rules, run history, recipes, dry-run, quotas).

## Critical rules (full list in TECHNICAL_DICTIONARY §7)
- **Build the frontend inside the devcontainer**, never on the host (host
  `node_modules` are Linux/rollup-specific and fail):
  `docker exec devcontainer-frappe-1 bash -lc 'cd /workspace/development/frappe-bench/apps/sprint/frontend && yarn build --base=/assets/sprint/frontend/'`
- The dev web server is `bench start` inside the container; a `docker restart`
  (needed after `hooks.py` changes) stops it — relaunch with `bench start` and
  confirm `/api/method/ping` → pong.
- Migrations are **idempotent `ensure_*` functions** run automatically on
  `bench migrate` via the `after_migrate` hook. Add new schema there; also
  callable one-off via `bench --site development.localhost execute sprint.setup.<fn>`.
- Multi-select = `Small Text` comma-string + `SP Space.chip_fields` + `chip_options` JSON. A `Select` can't hold multiple values.
- Never name a field `order` (SQL reserved) → use `sort_order`.
- Lucide icons work **only** as template tags (`<LucideX />`), never imported in `<script>`, never dynamic `:is` strings — branch with v-if (see `AutomationIcon.vue`).
- Inline/drag edits go through the **ORM** so Server Scripts/audit/realtime/**automations** fire.
- Structural rights = **Administrator OR the "Sprint Manager" role** (`_is_manager`).
- Generic card writes are allow-listed (`_clean_card_values`); parse user JSON with `_loads`.
- **Automations, notifications, and watchers only fire on writes through
  Sprint's own endpoints** — Desk/Server-Script/Excel-import edits bypass them.
- Big lists window the DOM, not the data (Board 30/column, List 50/group);
  `get_cards` intentionally ships the whole space (client-side filter/sort/group).

## Build & verify
After any `frontend/src` change, build in the container (command above); hard-refresh `/sprint`.
Backend (`api.py`/`automation.py`) auto-reloads; if wedged, graceful
`docker restart devcontainer-frappe-1` (then `bench start` — never `pkill -9`).
Run tests: `bench --site development.localhost run-tests --module sprint.tests.test_api`
(and `…test_automation`; needs `allow_tests` in site config).

## Data note
`Analyst Space` holds **real migrated data** (~131 cards) — not disposable. Use
**`Dev Task`** for demos and any destructive testing.

## Git
Standalone repo (`github.com/GorangMalvi/Frape-Trellis`; originally
`github.com/manask20/Sprint`), separate from the surrounding `frappe_docker`
repo. **`main` and `dev` are protected — PR only** (rulesets in
`.github/rulesets/`; full process in `CONTRIBUTING.md`): branch
`feat/*`/`fix/*` off `dev` → PR → squash-merge (deploys staging); release =
PR `dev` → `main`, merge commit (deploys production after approval). CI
(Lint / Frontend build / Server tests) must pass. Nothing is pushed unless
asked. Everyday commands: `COMMANDS.md`.
Recent arc: ticketing → Home/notifications/dashboards → calendar/watchers/
templates → body editor → perf → hardening+tests → automation engine.
