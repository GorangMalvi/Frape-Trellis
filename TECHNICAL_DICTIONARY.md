# Sprint — Technical Dictionary & Reference

A reference for an AI/dev picking up this codebase. Read alongside
`PRODUCT_OVERVIEW.md`.

---

## 1. Domain glossary

| Term | Meaning |
|---|---|
| **Space** | A Custom DocType (`custom=1`) whose records are cards. One DocType = one space. |
| **`SP Space`** | Registry DocType: one row per space. Autonamed after the target DocType. Holds display config + field pointers (see §4). |
| **Card** | A single record of a space's DocType. |
| **Bucket** | A board column / status. Rows of **`SP Bucket`** (fields: `bucket_name`, `space`, `color`, `sort_order`, `wip_limit`). A card's bucket field is a **Link → SP Bucket**, so it stores the bucket's hash id, not its name. |
| **`SP View`** | A saved view: `view_type`, `group_by`, `sort_field/dir`, `me_mode`, `is_shared`, `filters_json`. |
| **Subtask** | A card whose **parent field** (`parent_task`, a self-Link) points to another card in the same space. |
| **Title / Bucket / Assignee / Body / Parent / Badge field** | Per-space field *pointers* stored on `SP Space` (the UI is generic, so it must be told which field plays each role). |
| **Badge field** | The field rendered as the colored card badge — points to `sprint_points` (Sprint Points 1–10), replacing the concept of "priority". |
| **Chip field** | A multi-select field. Stored as a **`Small Text`** comma-joined string. Registered in `SP Space.chip_fields` (comma list of fieldnames). |
| **Chip options** | Predefined suggestions for chip fields. Stored as JSON in `SP Space.chip_options` = `{fieldname: [options]}`. NOT on the field (Small Text has no Options box). |
| **Activity feed** | Merge of: record `creation`, Frappe `Comment`s, and `Version` field-change diffs. Built by `get_activity`. |

---

## 2. Repository layout

```
apps/sprint/
  sprint/
    api.py        # main whitelisted surface (cards/views/fields/tickets/Home/inbox/watchers/templates/import)
    automation.py # automation engine: matcher, executors, dispatch, scheduler jobs, endpoints, RECIPES
    setup.py      # data model + idempotent ensure_* migrations, space creation, demo seed
    hooks.py      # website_route_rules, after_migrate, scheduler_events
    tests/        # test_api.py (access/hardening), test_automation.py
    public/frontend/   # built SPA assets (output of yarn build; committed)
    www/sprint.html    # SPA entry page (copied from build)
  frontend/
    package.json, vite.config.js
    src/
      main.js, App.vue, router.js, index.css, store.js
      pages/
        Board.vue       # orchestrator: loads space config+cards, owns view state, all mutations
        Home.vue        # / — my-tasks across spaces + notification inbox
        Dashboard.vue   # /<space>/dashboard — configurable widget grid (add/reorder/save)
        Automations.vue # /<space>/automations — rules list, run history, recipes
        DataPage.vue    # /<space>/data — Excel import/export with header mapping
        TicketIntake.vue# /tickets/new — raise-a-ticket form
      components/
        Sidebar.vue, Toolbar.vue, CommandPalette.vue, ToastHost.vue
        BoardView.vue, ListView.vue, CalendarView.vue, CardItem.vue
        TaskDrawer.vue       # the big card modal (autosave, activity, comments, watch, templates)
        ChipField.vue, DurationField.vue, LinkField.vue, UserAvatar.vue
        CardAttachments.vue  # files + external links (Frappe File)
        FieldsDialog.vue     # add field / edit chip options / convert Select->multi
        FilterPopover.vue    # board Filter — wraps the shared FilterRows.vue
        FilterRows.vue       # the {field,operator,value} row editor (board + automations)
        EmptyState.vue, BarChart.vue, DonutChart.vue, AccentSwitch.vue, ConfirmDialog.vue, NameDialog.vue
        DashboardWidget.vue, WidgetEditor.vue   # configurable dashboard: widget card + config modal
        AutomationBuilder.vue, AutomationActionRow.vue, AutomationRunLog.vue,
        AutomationRecipes.vue, AutomationIcon.vue, PlaceholderInput.vue
        BulkBar.vue, NewSpaceDialog.vue, NewTicketSpaceDialog.vue, SpaceAccessDialog.vue, …
      lib/
        board.js   # colorFor, midpoint, applyFilters, sortCards, buildGroups, matchFilter
        format.js  # formatDate/Duration/Number, when, timeAgo, stripHtml, contrastText
        automation.js  # TRIGGERS/ACTIONS registries, sentence generator, validate, factories
        dashboard.js   # widget model + aggregate() engine (group/measure/scope) + auto-defaults
        users.js   # ensureUsers, userLabel, userImage, userOptions, canManage (User cache)
        depends.js # eval: depends_on evaluation (mandatory/visible/read-only)
      composables/
        useOverlay.js       # Esc stack + focus trap + aria (use on every overlay)
        useSpacePointers.js # title/bucket/assignee/badge/due/parent field pointers
        useViewState.js     # active view, dirty tracking, sessionStorage persistence
```

---

## 3. Backend API surface (`sprint/api.py`, all `@frappe.whitelist()`)

| Endpoint | Purpose |
|---|---|
| `get_spaces` | sidebar list of readable spaces |
| `get_space(space)` | one space's full config: registry pointers (+ `chip_fields`, `chip_options`), buckets, field meta, `current_user` |
| `get_cards(space)` | all cards with every *listable* field (board/list/filter/sort run client-side off this) |
| `move_card`, `set_field` | drag-move / inline edit — **go through ORM (`doc.save`)** so events/audit/realtime fire |
| `create_space_api` | create a space (Custom DocType + registry + buckets) from the UI |
| `add_field` | add a field; kind ∈ multiselect\|select\|text\|number\|date\|check\|user\|duration |
| `set_chip_options`, `convert_to_multiselect` | manage chip option lists / flip a Select → Small Text chip field |
| `add_bucket`, `update_bucket`, `delete_bucket`, `reorder_buckets`, `reorder_spaces` | bucket/space management |
| `bulk_set`, `bulk_delete` | bulk actions |
| `get_views`, `save_view`, `delete_view` | saved views |
| `get_activity`, `add_comment` | activity feed (Version + Comment); `get_activity` caps at the latest 100 entries (`limit` param) |
| `get_my_cards` | Home page: cards assigned to me across all readable spaces (excludes `is_closed` buckets) |
| `get_notifications`, `get_unread_notification_count`, `mark_notification_read`, `mark_all_notifications_read` | persistent inbox over Frappe `Notification Log` |
| `get_watch`, `toggle_watch` | per-card watchers (`SP Watcher`); watchers are notified on bucket/assignee changes + comments |
| `get_templates`, `save_template`, `delete_template` | per-space card templates (`SP Template`, values JSON; save/delete manager-only) |
| `save_dashboard` | persist a space's configurable dashboard layout (`SP Space.dashboard_json`; manager-only; empty list → null = auto-defaults) |
| **`sprint.automation.*`** | the automation engine (separate module): `get_automations`(+quota), `save_automation`, `toggle_automation`, `delete_automation`, `get_automation_runs`, `run_automation_test` (dry-run), `get_automation_recipes` |
| `get_attachments`, `add_file_link`, `remove_attachment` | attachments (Frappe File; uploads use native `/api/method/upload_file`) |
| `export_space`, `import_preview`, `import_commit` | Excel import/export (uses `frappe.utils.xlsxutils`) |

---

## 4. `SP Space` registry fields (the pointers that drive the generic UI)

`target_doctype`, `label`, `icon`, `color`, `sort_order`,
`title_field` (default `title`), `bucket_field` (`bucket`),
`assignee_field`, `body_field`, `parent_field` (`parent_task`),
`badge_field` (`sprint_points`), `due_field` (usually `due_date` — drives
Home grouping + dashboard overdue), `chip_fields` (comma list),
`chip_options` (JSON `{field: [opts]}`).

`SP Bucket` also carries `is_closed` (Check) — marks a terminal ("Done")
bucket so Home/my-tasks and dashboards can exclude finished work.
Migration entry point: `sprint.setup.ensure_due_and_closed_fields`.

Every space DocType auto-gets: `bucket` (Link→SP Bucket), `parent_task`
(self-Link), `position` (Float, hidden — drag rank). Example real fields on
`Analyst Space`: `title`, `assignee` (Link→User), `due_date` (Date), `body`
(Text Editor), `sprint_points` (Select 1-10), `tags` (Small Text chip),
`business_owner` (Link→User), `time_estimate` (Duration), `ai_score` (Int).

---

## 5. Key Frappe concepts used

- **DocType / meta** — schema. The UI reads `frappe.get_meta(doctype).fields`.
- **Custom DocType (`custom=1`)** — editable at runtime without developer mode;
  spaces are these. Adding/changing fields = edit the DocType doc + `.save()`.
- **Server Scripts** (DocType Event) — where business logic belongs. Requires
  `server_script_enabled`. They fire only on ORM saves.
- **`owner` / `creation`** — Frappe sets these on insert (owner = session user).
  To preserve original values on import, override **after** insert via
  `frappe.db.set_value(dt, name, {...}, update_modified=False)`.
- **Realtime** — `frappe.publish_realtime("list_update", {doctype,name,user}, doctype=..., after_commit=True)`. Client subscribes via socket; ignores `user == self`.
- **File** — `attached_to_doctype`/`attached_to_name`. Supports uploads *and*
  external-URL "links" (Google Docs/Sheets).
- **Fieldtypes that matter here:** `Select` (single value, **validated** — cannot
  hold CSV), `Small Text` (free string → our multi-select storage), `Link`,
  `Duration` (stored as **seconds**), `Text Editor` (HTML body).

---

## 6. frappe-ui (frontend lib) cheatsheet

- `createResource({url, makeParams, onSuccess, auto})` → `.data`, `.fetch()`,
  `.reload()`, `.loading`.
- `call('dotted.path.method', {args})` → returns `message`. Reads
  `window.csrf_token` automatically.
- `TextEditor` (TipTap): `:content` + `@change`, `:fixedMenu`/`:bubbleMenu`.
- `LinkField` (local wrapper) for Link fields; under the hood reka-ui Popover
  teleports to body.
- `initSocket()` for realtime; `Autocomplete`, `Avatar`, `Badge`, `FormControl`.

---

## 7. Conventions & gotchas (READ BEFORE EDITING)

- **Multi-select = `Small Text` + `chip_fields` + `chip_options`.** A `Select`
  can't hold multiple values (it validates a single option). "Convert to
  multi-select" flips the type to `Small Text` and copies its options into
  `chip_options`.
- **Never name a field `order`** — SQL reserved word; use **`sort_order`**.
- **Use `frappe.client.get`**, not `get_doc` (the latter isn't a client method).
- **Lucide icons only work as *template* auto-imports** (frappe-ui vite plugin),
  e.g. `<LucideX />`. You **cannot** import them in `<script>` and dynamic
  `:is="'LucideX'"` strings don't resolve — render by branch in the template.
- **`set_field` / `move_card` use the ORM** (`doc.set().save()`), not
  `frappe.db.set_value`, so Server Scripts/validations/Version/realtime fire.
  Raw `frappe.db.set_value` (used in reorder endpoints, import owner/creation)
  bypasses all of that — `publish_realtime` is called manually there.
- **`.PopoverContent { z-index: 100 }`** in `index.css` — without it, Link
  dropdowns render *behind* the task modal (reka-ui teleports with no z-index).
- **Realtime on `*.localhost`** — the socketio node server can't resolve
  `development.localhost`; needs `127.0.0.1 development.localhost` in the
  container hosts (`extra_hosts` in `.devcontainer/docker-compose.yml`).
- **Frappe Desk is `/desk`** (v16), not `/app`.
- **Structural rights = Administrator OR the "Sprint Manager" role**
  (`_is_manager` in api.py). Grant the role in Desk to delegate space/field/
  bucket management without the Administrator account.
- **Generic card writes are allow-listed** (`_clean_card_values`): system
  columns are stripped, unknown fields rejected, and a bucket value must
  belong to the card's space. `verify_password` is rate-limited (5/min).
- **Registry migrations auto-run on `bench migrate`** via the `after_migrate`
  hook (idempotent `ensure_*` functions in setup.py) — no manual step on a
  fresh bench.
- **Tests**: `bench --site SITE run-tests --module sprint.tests.test_api`
  (and `…test_automation`; requires `allow_tests`; ephemeral spaces).
- **Automation engine** lives in `sprint/automation.py` (matcher, executors,
  dispatch, scheduler jobs, endpoints, recipes). Doctypes `SP Automation` +
  `SP Automation Run` (created by `ensure_automation_meta`, auto-run via
  `after_migrate`). Dispatch piggybacks on `_notify_card_changes` (card events)
  and `add_comment` (comment events) — 2 lazy-import call sites in api.py.
  `match_conditions` mirrors `matchFilter` (board.js) exactly; the frontend
  reuses the shared **FilterRows.vue** row editor. Scheduler cron `*/5`
  `process_time_based_automations` + daily `prune_automation_runs`
  (`hooks.py scheduler_events`; needs a `bench restart` after hook changes).
  Guards: `frappe.local._sprint_automation_depth` (max 2), per-space daily
  quota from the run log (`sprint_automation_daily_quota`, default 500),
  SSRF-checked + queued webhooks. Event rules run **inline as the triggering
  user**; a rule failure never fails the user's save.
- **Big lists window the DOM, not the data.** `get_cards` intentionally ships
  the whole space (filter/sort/group run client-side — the core architecture);
  BoardView renders 30 cards/column and ListView 50 rows/group with "Show
  more". Dropping a card at the very end of a windowed column positions it
  relative to the last *visible* card.

---

## 8. Build & dev workflow

Dev runs in a devcontainer: container **`devcontainer-frappe-1`**, bench at
**`/workspace/development/frappe-bench`**, site **`development.localhost`**.
On the host the repo is at `…/frappe_docker`, mounted so host `…/development` =
container `/workspace`.

**Build the frontend** (required after any `frontend/src` change):
```
cd /workspace/development/frappe-bench/apps/sprint/frontend
yarn build --base=/assets/sprint/frontend/
```
This outputs to `sprint/public/frontend/` and copies the entry HTML to
`sprint/www/sprint.html`. Assets are served via a symlink
`sites/assets/sprint → apps/sprint/sprint/public`; routing via
`website_route_rules` (`/sprint/<path:app_path>`).

**Backend changes** (`api.py`): the dev server auto-reloads. If wedged, prefer a
**graceful** `docker restart devcontainer-frappe-1` — **do NOT `pkill -9`** the
werkzeug server (it can wedge subsequent requests).

**Run Python in the bench** (e.g. migrations, one-off scripts):
```
docker exec -i devcontainer-frappe-1 bash -lc 'cd /workspace/development/frappe-bench/sites && ../env/bin/python /tmp/script.py'
```
or `bench --site development.localhost execute sprint.setup.<fn>`.

**Useful `setup.py` entry points:** `install_all`, `rebuild`, `setup_demo`,
`create_space`, `migrate_chip_options`, `clear_audit`, `delete_space`.

---

## 9. Repo / git

This app is its own git repo (remote: `github.com/manask20/Sprint`), **separate
from the surrounding `frappe_docker` repo** (which gitignores `development/*`).
It is a standalone, installable Frappe app (`bench get-app` → `install-app
sprint`; then `yarn install` + `yarn build`).
