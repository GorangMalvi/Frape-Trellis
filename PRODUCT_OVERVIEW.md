# Sprint — Product Overview

Sprint is a **ClickUp-style task & project management product built on a Frappe
backend with a custom Vue 3 + frappe-ui single-page UI.** Frappe provides the
data layer, permissions, audit, realtime and business-logic engine; Sprint is a
polished, opinionated front-end that makes that backend feel like a modern
work-management app.

It is served as a bundled SPA at **`/sprint`** (e.g. `http://development.localhost:8000/sprint`),
same-origin with Frappe so it reuses the logged-in session. The Frappe Desk
(admin UI) lives at **`/desk`** (this is Frappe v16 — note: `/desk`, not `/app`).

---

## The core architectural idea: "each DocType **is** a Space"

This is the single most important concept. Everything follows from it.

- A **Space** is a Custom DocType (`custom=1`). Its **records are the cards.**
  e.g. the DocType `Analyst Space` holds one record per task/card.
- Spaces are created **rarely**, by admins. Buckets and cards are everyday data.
- The Sprint UI is a **generic, meta-driven renderer.** It reads the DocType's
  *meta* (its field definitions) and renders the board/list/drawer accordingly.
  Add a field in Frappe Desk → it shows up in the UI automatically. No per-space
  UI code is written.
- A thin registry DocType, **`SP Space`**, records *display config* and *field
  pointers* for each space (which field is the title, which is the bucket, etc.).

### The object model

| Concept | What it is in Frappe |
|---|---|
| **Space** | a Custom DocType (the card entity), registered in `SP Space` |
| **Card** | one record of that DocType |
| **Bucket** (column / status) | a row in `SP Bucket`; the card's `bucket` field links to it |
| **Subtask** | a card whose `parent_task` field links to another card in the *same* space |
| **Saved View** | a row in `SP View` (group/sort/filters/me-mode/type) |
| **Activity** | Frappe's `Version` (field-change audit) + `Comment` records |
| **Attachment** | Frappe's `File` records attached to the card |

Spaces are **single-context**: you view one space at a time (no cross-space
boards). Buckets are *data rows*, so renaming/reordering a bucket never rewrites
card records (the card links to the bucket by id).

---

## Design philosophy

1. **Lean on Frappe; don't reinvent it.** Permissions, audit (Version),
   comments, realtime (`list_update`), the File system, and data import/export
   primitives are all Frappe's. Sprint wraps them.
2. **Business logic lives in Frappe Server Scripts** (DocType events) on each
   space's DocType — not in the UI. The UI just reads/writes through the ORM so
   those scripts, validations, and audit always fire.
3. **Structural edits happen in Frappe Desk; the UI auto-reflects them.** Adding
   a field, changing a field type, adding permissions — do it in Desk (or via the
   in-app Fields dialog), and the meta-driven UI picks it up.
4. **The UI is generic.** There is one Board renderer, one List renderer, one
   task drawer — driven by the registry pointers + DocType meta, for every space.

---

## What's built (feature set)

**Views & navigation**
- **Board** (kanban by bucket), **List**, and **Calendar** views over the same
  data. The Calendar (month grid, appears when the space has a `due_field`)
  supports drag-to-reschedule, a "+" per day to create with that due date,
  and an unscheduled tray for cards without a date.
- **Saved Views** — each carries group-by + filters + sort + me-mode + type.
  "Save changes" updates a view in place (toast confirm); "Save as view"/"+ View"
  creates a new one. (On the Board, Group and Save-as-view are hidden — the board
  is always a kanban by bucket; those belong to the List.)
- **Filters** with dropdowns that resolve real values (buckets show names, User
  links show full names).
- **Group by** and **Sort** (List), **Me mode**, **search**.
- **Command palette** (⌘K / `/`).
- **Subtasks** shown as either *Separate* cards (with a parent label + jump) or
  *Nested* under an expander.

**The card (task drawer)**
- Large split modal: title, meta fields (status/assignee/dates/sprint points/
  chips/etc.), **rich-text body** (TipTap), **attachments**, **subtasks**, and an
  **activity feed** (created + field changes + comments) with a comment composer.
- **Autosave** (debounced) with error surfacing + optimistic revert via toasts.
- **Watch** — follow any card (`SP Watcher`); watchers are notified on
  status/assignee changes and new comments. @mentions render as accent chips
  in the activity feed.
- **Card templates** (`SP Template`) — admins save a card's field values as a
  named template ("Save as template" in the drawer); new-card mode offers
  "Start from: <template>" chips.

**Fields & data shape (managed from the UI — "Fields" dialog)**
- **Add a field** of type: Multi-select, Single-select, Text, Number,
  Time estimate (Duration), Date, Checkbox, User.
- **Multi-select chips** — free-form tags backed by a `Small Text` comma-string,
  with **predefined, editable option suggestions**.
- **Convert a native Select → multi-select** (reuses its options).
- **Sprint Points** (1–10) instead of "priority" (a registry-pointed badge field).
- **Time estimate** via Frappe's `Duration` type (shown as `Xh Ym`).

**Admin actions in-app**
- Create a space (+ New Space dialog → Custom DocType + buckets).
- Create / rename / recolor / reorder / delete buckets.
- Bulk select + bulk edit / delete.
- Persisted manual **drag-ordering** within a group (fractional `position`).

**Home & notifications**
- **Home page** (`/sprint/`) — **My Tasks** across every readable space,
  grouped Overdue / Today / This week / Later / No date, plus a persistent
  **Inbox** (Frappe `Notification Log`) with unread badge in the sidebar
  (live via the `sprint_notification` realtime event) and mark-all-read.
- **Assignee notifications** — changing a card/ticket's assignee notifies the
  new assignee (in-app toast + inbox; email if the site has outgoing mail).
  Ticket requesters are alerted when their ticket changes bucket.
- Emitted from Sprint's own mutation endpoints — Desk/Server-Script edits
  don't notify (a wildcard doc_events hook is the future upgrade).

**Dashboard** (`/sprint/<space>/dashboard`, per space) — a **configurable
widget builder**, not a fixed report.
- Managers **Customize**: add / remove / drag-reorder widgets. Each widget is a
  **number** (total / open / overdue / done-this-week / sum of any numeric
  field) or a **chart** (bar or donut) that groups cards by **any** field
  (bucket, any Select/Link/Check, or a chip field — chip values split so a card
  tagged `bug,seo` counts in both), measured by count or sum, over all or open
  cards. Layout persists per space (`SP Space.dashboard_json`, manager-edited,
  everyone views).
- **Auto-defaults** when a space has no saved layout: sensible KPIs + a chart
  per groupable field, so a fresh space's dashboard already reflects its shape.
- **Click-to-drill**: clicking a chart segment opens the board's List view
  filtered to that value (chip fields use `contains`).
- All aggregates compute client-side from the same `get_cards` payload the
  board uses. Relies on `SP Space.due_field` + `SP Bucket.is_closed`
  (see TECHNICAL_DICTIONARY §4).

**Automations** (`/sprint/<space>/automations`, per space, manager-managed)
- No-code **"when X → do Y"** rules with a visual builder (WHEN trigger · IF
  conditions · THEN ordered actions) and a live plain-English preview.
- **Triggers**: card created · moves to bucket · field changes (optionally to a
  value) · assignee changes · comment added · due date arrived / N days before ·
  card inactive N days · recurring schedule (daily/weekly/monthly).
- **Actions** (chained): set field · move to bucket · assign (person or
  round-robin) · apply template · create card/subtask · notify
  (assignee/watchers/requester/users) · post comment · webhook (HTTP POST with
  optional HMAC signature). Messages support `{title} {assignee} {bucket}
  {due_date} {space} {link}` placeholders.
- **Trust & safety**: a full **run-history log** (status, actions, errors,
  duration, card link), a **recipe gallery** of one-click prebuilt rules, a
  **dry-run** ("test on a card") that writes nothing, a per-space **daily run
  quota**, and loop protection (bounded cascade depth). Event rules run inline
  in the user's transaction; time-based/recurring run on a 5-min scheduler.
  (Like notifications, only writes through Sprint's own endpoints fire rules —
  Desk/Server-Script/import edits bypass them.)

**Realtime** — board/list/sidebar live-update across users via Frappe's
`list_update` event (self-authored events are ignored to avoid fighting
optimistic UI).

**Data migration — dedicated Import/Export page** (`/sprint/<space>/data`)
- **Export** to Excel (all cards + `Ref`/`Parent Ref` columns so subtasks
  round-trip; buckets export as names, multi-selects as comma strings).
- **Import** from Excel with a **header-mapping** step, inserting through the ORM
  (validations/Server Scripts/audit fire), resolving subtasks via Ref columns,
  and optional update-existing matching.

---

## Status & data note

`Analyst Space` currently holds **real migrated ClickUp data (~131 cards)** — it
is **not** disposable test data. `Dev Task` ("Dev Tasks") is the demo space.

See **`TECHNICAL_DICTIONARY.md`** for the file map, glossary, conventions, and
gotchas before making changes.
