"""Sprint automation engine — "when X happens (and conditions match), do Y".

Everything for the engine lives here: the condition matcher, action executors,
event/scheduler dispatch, whitelisted endpoints, and the static recipe list.
`api.py` only gains two lazy-import dispatch calls (in `_notify_card_changes`
and `add_comment`) so there is no circular import; this module imports api
helpers at the top.

Execution model
---------------
- Event rules (card/comment triggers) run **inline, synchronously, in the same
  transaction as the user's write, as the triggering user**. Rule failure is
  contained so it can never fail that write.
- Time-based + recurring rules run from a 5-minute scheduler cron as
  Administrator (see process_time_based_automations).
- Only webhooks are enqueued (network I/O must not add latency to set_field).

Trade-off (same as notifications): only writes that go through Sprint's own
mutation endpoints fire automations. Desk edits, Server Scripts and the Excel
import bypass them. A wildcard doc_events hook is the future upgrade.

Uses TABS to match api.py.
"""

import hashlib
import hmac
import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import frappe
from frappe import _

from sprint.api import (
	_card_title,
	_card_watchers,
	_clean_card_values,
	_is_ticket_reg,
	_listable_fields,
	_loads,
	_notify,
	_notify_card_changes,
	_require_bucket_in_space,
	_require_manager,
	_require_space_access,
	_space_reg,
	can_access_space,
	is_ticket_space,
)

# triggers that fire from a card/comment write (vs the scheduler)
EVENT_TRIGGERS = (
	"card_created", "moved_to_bucket", "field_changed", "assignee_changed",
)
SCHEDULER_TRIGGERS = (
	"due_date_arrived", "due_date_approaching", "card_inactive", "scheduled",
)
ACTION_TYPES = (
	"set_field", "move_to_bucket", "assign", "apply_template",
	"create_card", "notify", "add_comment", "webhook",
)
# actions that need a source/target card — unavailable to a scheduled rule
# unless a create_card action ran earlier in the same rule
CARD_REQUIRED_ACTIONS = ("set_field", "move_to_bucket", "assign", "apply_template")

DEFAULT_DAILY_QUOTA = 500
MAX_DEPTH = 2


# ---------------------------------------------------------------------------
# condition matcher — EXACT mirror of matchFilter in frontend/src/lib/board.js
# ---------------------------------------------------------------------------
def _s(v):
	"""Match the JS String(v ?? '') coercion the frontend uses."""
	return "" if v is None else str(v)


def match_conditions(card, conditions):
	"""AND across rows. A row with no field/operator is skipped; an unknown
	operator passes (same lenient default as the client). `card` is a dict."""
	for f in conditions or []:
		field = f.get("field")
		operator = f.get("operator")
		if not field or not operator:
			continue
		v = card.get(field)
		value = f.get("value")
		if operator == "is":
			ok = _s(v) == _s(value)
		elif operator == "is not":
			ok = _s(v) != _s(value)
		elif operator == "is any of":
			arr = [_s(x) for x in value] if isinstance(value, list) else []
			ok = True if not arr else _s(v) in arr
		elif operator == "is none of":
			arr = [_s(x) for x in value] if isinstance(value, list) else []
			ok = True if not arr else _s(v) not in arr
		elif operator == "contains":
			ok = _s(value).lower() in _s(v).lower()
		elif operator == "is empty":
			ok = v is None or v == ""
		elif operator == "is set":
			ok = v is not None and v != ""
		else:
			ok = True
		if not ok:
			return False
	return True


# ---------------------------------------------------------------------------
# placeholders — {title} {name} {assignee} {bucket} {due_date} {space} {link}
# ---------------------------------------------------------------------------
def render_placeholders(text, doc, reg, actor=None):
	"""Replace only the known keys (never str.format, so arbitrary {tokens} in
	user text can't KeyError or reach attributes). doc may be None (scheduled)."""
	if not text:
		return text or ""
	values = {"space": reg.label if reg else "", "user": ""}
	if actor:
		values["user"] = frappe.utils.get_fullname(actor)
	if doc is not None:
		title_field = (reg.title_field if reg else None) or "title"
		assignee_field = reg.get("assignee_field") if reg else None
		bucket_field = (reg.bucket_field if reg else None) or "bucket"
		due_field = reg.get("due_field") if reg else None
		values["title"] = doc.get(title_field) or ""
		values["name"] = doc.name
		if assignee_field and doc.get(assignee_field):
			values["assignee"] = frappe.utils.get_fullname(doc.get(assignee_field))
		else:
			values["assignee"] = "—"
		bucket = doc.get(bucket_field)
		values["bucket"] = (frappe.db.get_value("SP Bucket", bucket, "bucket_name") if bucket else None) or "—"
		values["due_date"] = frappe.utils.formatdate(doc.get(due_field)) if (due_field and doc.get(due_field)) else "—"
		values["link"] = _card_link(reg, doc)
	out = text
	for key in ("title", "name", "assignee", "bucket", "due_date", "space", "user", "link"):
		if "{" + key + "}" in out:
			out = out.replace("{" + key + "}", _s(values.get(key, "—") if values.get(key) not in (None, "") else "—"))
	return out


def _card_link(reg, doc):
	if not reg or doc is None:
		return frappe.utils.get_url()
	base = frappe.utils.get_url()
	if (reg.get("space_type") or "Task") == "Ticket":
		return f"{base}/sprint/tickets/{reg.name}?ticket={doc.name}"
	return f"{base}/sprint/{reg.name}?card={doc.name}"


# ---------------------------------------------------------------------------
# webhook URL safety (SSRF guard) — used at save time and just before delivery
# ---------------------------------------------------------------------------
def _validate_webhook_url(url):
	"""Reject non-http(s), and any host resolving to a private/loopback/
	link-local/reserved/multicast address (blocks 127.*, 10.*, 172.16-31.*,
	192.168.*, 169.254.* cloud metadata, ::1). TOCTOU/DNS-rebind between this
	check and the request is a documented residual gap in v1."""
	if not url:
		frappe.throw(_("Webhook URL is required."))
	parsed = urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.hostname:
		frappe.throw(_("Webhook URL must be http(s) with a host."))
	host = parsed.hostname
	if host.lower() in ("localhost",) or host.lower().endswith((".local", ".internal")):
		frappe.throw(_("Webhook host is not allowed."))
	try:
		infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
	except Exception:
		frappe.throw(_("Webhook host could not be resolved."))
	for info in infos:
		ip = ipaddress.ip_address(info[4][0])
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
			frappe.throw(_("Webhook target resolves to a non-public address."))
	return True


# ---------------------------------------------------------------------------
# save-time validation
# ---------------------------------------------------------------------------
def _validate_definition(reg, trigger_type, trigger_config, conditions, actions):
	"""Validate a rule against the space's meta. Raises on the first problem."""
	if trigger_type not in EVENT_TRIGGERS + SCHEDULER_TRIGGERS:
		frappe.throw(_("Unknown trigger type: {0}").format(trigger_type))
	meta = frappe.get_meta(reg.target_doctype)

	# trigger config
	tc = trigger_config or {}
	if trigger_type == "moved_to_bucket" and tc.get("bucket"):
		_require_bucket_in_space(reg, tc["bucket"])
	if trigger_type == "field_changed" and tc.get("field") and not meta.has_field(tc["field"]):
		frappe.throw(_("Trigger field does not exist: {0}").format(tc["field"]))
	if trigger_type in ("due_date_approaching", "card_inactive"):
		key = "days_before" if trigger_type == "due_date_approaching" else "days"
		if frappe.utils.cint(tc.get(key)) < 0:
			frappe.throw(_("Days must be zero or more."))
	if trigger_type in ("due_date_arrived", "due_date_approaching") and not reg.get("due_field"):
		frappe.throw(_("This space has no due-date field for a due-date trigger."))
	if trigger_type == "scheduled":
		_validate_schedule(tc)

	# conditions: fields must exist
	for c in conditions or []:
		if c.get("field") and not meta.has_field(c["field"]):
			frappe.throw(_("Condition field does not exist: {0}").format(c["field"]))

	# actions
	if not actions:
		frappe.throw(_("Add at least one action."))
	cardless_trigger = trigger_type == "scheduled"
	has_create = False
	for a in actions:
		atype = a.get("type")
		if atype not in ACTION_TYPES:
			frappe.throw(_("Unknown action type: {0}").format(atype))
		if atype == "set_field":
			if not a.get("field") or not meta.has_field(a["field"]):
				frappe.throw(_("Set-field action targets a missing field."))
			_clean_card_values(reg, {a["field"]: a.get("value")})
		elif atype == "move_to_bucket":
			_require_bucket_in_space(reg, a.get("bucket"))
		elif atype == "assign":
			users = a.get("users") or ([a["user"]] if a.get("user") else [])
			for u in users:
				if not frappe.db.exists("User", u):
					frappe.throw(_("Assign action names an unknown user: {0}").format(u))
		elif atype in ("apply_template", "create_card"):
			tmpl = a.get("template")
			if not tmpl or frappe.db.get_value("SP Template", tmpl, "space") != reg.name:
				frappe.throw(_("Action references a template not in this space."))
			if atype == "create_card":
				has_create = True
		elif atype == "notify":
			if not (a.get("recipients") or a.get("users")):
				frappe.throw(_("Notify action needs at least one recipient."))
		elif atype == "webhook":
			_validate_webhook_url(a.get("url"))
	# a scheduled rule can only touch a card if it creates one first
	if cardless_trigger:
		for a in actions:
			if a.get("type") in CARD_REQUIRED_ACTIONS and not has_create:
				frappe.throw(_("A scheduled rule must create a card before it can {0}.").format(a["type"]))
			if a.get("type") == "create_card":
				has_create = True


def _validate_schedule(tc):
	freq = tc.get("frequency")
	if freq not in ("daily", "weekly", "monthly"):
		frappe.throw(_("Schedule frequency must be daily, weekly or monthly."))
	if not tc.get("time"):
		frappe.throw(_("Schedule needs a time of day."))
	if freq == "weekly" and tc.get("weekday") is None:
		frappe.throw(_("Weekly schedule needs a weekday."))
	if freq == "monthly":
		dom = frappe.utils.cint(tc.get("day_of_month"))
		if dom < 1 or dom > 28:
			frappe.throw(_("Day of month must be 1–28."))


# ---------------------------------------------------------------------------
# schedule math (site tz) — presets only, no raw cron
# ---------------------------------------------------------------------------
def compute_next_run(tc, after=None):
	"""Next fire datetime (site tz) at or after `after` for a scheduled rule."""
	from datetime import datetime, timedelta

	after = after or frappe.utils.now_datetime()
	hh, mm = (tc.get("time") or "09:00").split(":")
	hh, mm = int(hh), int(mm)
	freq = tc.get("frequency")

	def at(day):
		return day.replace(hour=hh, minute=mm, second=0, microsecond=0)

	if freq == "daily":
		cand = at(after)
		if cand <= after:
			cand = at(after + timedelta(days=1))
		return cand
	if freq == "weekly":
		target = frappe.utils.cint(tc.get("weekday"))  # 0=Mon … 6=Sun
		cand = at(after)
		delta = (target - cand.weekday()) % 7
		cand = at(after + timedelta(days=delta))
		if cand <= after:
			cand = at(after + timedelta(days=delta + 7))
		return cand
	if freq == "monthly":
		dom = frappe.utils.cint(tc.get("day_of_month")) or 1
		year, month = after.year, after.month
		cand = at(datetime(year, month, dom))
		if cand <= after:
			month += 1
			if month > 12:
				month, year = 1, year + 1
			cand = at(datetime(year, month, dom))
		return cand
	return None


# ---------------------------------------------------------------------------
# recipes — prebuilt rules the UI offers as one-click starting points.
# `slots` tells the UI which config keys the user must fill (blanks).
# ---------------------------------------------------------------------------
RECIPES = [
	{
		"id": "round_robin_new",
		"name": "Round-robin new cards",
		"description": "When a card is created, assign it to the next person in a rotation.",
		"icon": "user",
		"trigger_type": "card_created", "trigger_config": {}, "conditions": [],
		"actions": [{"type": "assign", "users": []}],
		"slots": [{"key": "users", "kind": "users", "label": "People to rotate between", "path": "actions.0.users"}],
	},
	{
		"id": "due_today_nudge",
		"name": "Due-today nudge",
		"description": "On the due date, remind the assignee.",
		"icon": "calendar",
		"trigger_type": "due_date_arrived", "trigger_config": {}, "conditions": [],
		"actions": [{"type": "notify", "recipients": ["assignee"], "message": "“{title}” is due today — {link}"}],
		"slots": [],
	},
	{
		"id": "due_soon",
		"name": "Due-soon reminder",
		"description": "A few days before the due date, remind the assignee.",
		"icon": "calendar",
		"trigger_type": "due_date_approaching", "trigger_config": {"days_before": 2}, "conditions": [],
		"actions": [{"type": "notify", "recipients": ["assignee"], "message": "“{title}” is due in a couple of days — {link}"}],
		"slots": [{"key": "days_before", "kind": "days", "label": "Days before due", "path": "trigger_config.days_before"}],
	},
	{
		"id": "notify_requester_done",
		"name": "Tell the requester when it ships",
		"description": "When a card moves to a bucket, notify the requester and watchers.",
		"icon": "columns",
		"trigger_type": "moved_to_bucket", "trigger_config": {"bucket": None}, "conditions": [],
		"actions": [{"type": "notify", "recipients": ["requester", "watchers"], "message": "“{title}” moved to {bucket}"}],
		"slots": [{"key": "bucket", "kind": "bucket", "label": "Which bucket", "path": "trigger_config.bucket"}],
	},
	{
		"id": "escalate_stale",
		"name": "Escalate stale cards",
		"description": "When a card sees no activity for a while, comment and ping the assignee.",
		"icon": "moon",
		"trigger_type": "card_inactive", "trigger_config": {"days": 7}, "conditions": [],
		"actions": [
			{"type": "add_comment", "message": "No activity for a while — is this still moving?"},
			{"type": "notify", "recipients": ["assignee"], "message": "“{title}” has gone quiet — {link}"},
		],
		"slots": [{"key": "days", "kind": "days", "label": "Days of inactivity", "path": "trigger_config.days"}],
	},
	{
		"id": "auto_route",
		"name": "Auto-route on a field value",
		"description": "When a field changes to a value, move the card to a bucket.",
		"icon": "pen",
		"trigger_type": "field_changed", "trigger_config": {"field": None, "to_value": None}, "conditions": [],
		"actions": [{"type": "move_to_bucket", "bucket": None}],
		"slots": [
			{"key": "field", "kind": "field", "label": "Which field", "path": "trigger_config.field"},
			{"key": "to_value", "kind": "value", "label": "Changes to", "path": "trigger_config.to_value"},
			{"key": "bucket", "kind": "bucket", "label": "Move to", "path": "actions.0.bucket"},
		],
	},
	{
		"id": "weekly_task",
		"name": "Weekly recurring task",
		"description": "Every week, create a card from a template and assign it.",
		"icon": "repeat",
		"trigger_type": "scheduled",
		"trigger_config": {"frequency": "weekly", "weekday": 0, "time": "09:00"},
		"conditions": [],
		"actions": [
			{"type": "create_card", "template": None},
			{"type": "assign", "user": None},
		],
		"slots": [
			{"key": "template", "kind": "template", "label": "Card template", "path": "actions.0.template"},
			{"key": "user", "kind": "user", "label": "Assign to", "path": "actions.1.user"},
		],
	},
	{
		"id": "checklist_on_create",
		"name": "Kick off a checklist on create",
		"description": "When a card is created, apply a template's field values.",
		"icon": "plus",
		"trigger_type": "card_created", "trigger_config": {}, "conditions": [],
		"actions": [{"type": "apply_template", "template": None}],
		"slots": [{"key": "template", "kind": "template", "label": "Template to apply", "path": "actions.0.template"}],
	},
]


# ---------------------------------------------------------------------------
# quota — per-space daily run cap, counted from the run log itself
# ---------------------------------------------------------------------------
def _daily_quota():
	return frappe.utils.cint(frappe.conf.get("sprint_automation_daily_quota")) or DEFAULT_DAILY_QUOTA


def _quota_used(space):
	"""Runs logged for this space today (site tz). Memoized + locally
	incremented per request so a 200-card bulk_set doesn't re-count each time."""
	cache = getattr(frappe.local, "_sprint_quota", None)
	if cache is None:
		cache = frappe.local._sprint_quota = {}
	if space not in cache:
		cache[space] = frappe.db.count(
			"SP Automation Run", {"space": space, "creation": [">=", frappe.utils.today()]}
		)
	return cache[space]


def _quota_bump(space):
	cache = getattr(frappe.local, "_sprint_quota", None) or {}
	cache[space] = cache.get(space, 0) + 1
	frappe.local._sprint_quota = cache


def _quota_exceeded(space):
	return _quota_used(space) >= _daily_quota()


def _log_quota_skip(space):
	"""One Skipped row per space per day marks that the cap was hit."""
	exists = frappe.db.exists("SP Automation Run", {
		"space": space, "status": "Skipped", "trigger_type": "quota",
		"creation": [">=", frappe.utils.today()],
	})
	if exists:
		return
	frappe.get_doc({
		"doctype": "SP Automation Run", "automation": "", "automation_label": "—",
		"space": space, "trigger_type": "quota", "status": "Skipped",
		"error": "Daily automation quota reached.", "triggered_by": frappe.session.user,
	}).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# executor
# ---------------------------------------------------------------------------
def _execute(auto, reg, doc, snapshot, is_test=False):
	"""Run a rule's actions against `doc` (may be None for a scheduled rule
	until a create_card action sets one). Every action is attempted; one
	failing action never blocks the next. Returns the run name (None for a
	dry-run). When is_test, nothing is written — actions only 'resolve'."""
	actions = _loads(auto.get("actions")) or []
	ctx = {"reg": reg, "doc": doc, "auto": auto, "actor": frappe.session.user}
	log = []
	overall_error = None

	frappe.local._sprint_automation_depth = getattr(frappe.local, "_sprint_automation_depth", 0) + 1
	try:
		for a in actions:
			atype = a.get("type")
			t0 = time.monotonic()
			entry = {"type": atype, "status": "ok", "detail": ""}
			try:
				handler = _ACTION_HANDLERS.get(atype)
				if not handler:
					entry.update(status="failed", detail=f"unknown action {atype}")
				elif ctx["doc"] is None and atype in CARD_REQUIRED_ACTIONS:
					entry.update(status="skipped", detail="no target card")
				else:
					entry["detail"] = handler(a, ctx, is_test)
					if is_test:
						entry["status"] = "would"
			except _Queued as q:  # webhook wants to be enqueued after the run row exists
				entry.update(status="would" if is_test else "queued", detail=q.detail)
				if not is_test:
					entry["_url"], entry["_body"], entry["_secret"] = q.url, q.body, q.secret
			except Exception as e:  # one bad action must not abort the rest
				entry.update(status="failed", detail=str(e)[:200])
				overall_error = overall_error or str(e)[:200]
				if not is_test:
					frappe.log_error(frappe.get_traceback(), f"Sprint automation action {atype}")
			entry["ms"] = int((time.monotonic() - t0) * 1000)
			log.append(entry)
	finally:
		frappe.local._sprint_automation_depth -= 1

	statuses = {e["status"] for e in log}
	if is_test:
		return {"actions": log}

	if not log:
		status = "Skipped"
	elif statuses <= {"ok"}:
		status = "Success"
	elif "ok" in statuses:
		status = "Partial"
	else:
		status = "Failed"

	target = ctx["doc"]
	# never persist the private _url/_body/_secret carried on queued entries
	public_log = [{k: v for k, v in e.items() if not k.startswith("_")} for e in log]
	run = frappe.get_doc({
		"doctype": "SP Automation Run",
		"automation": auto.get("name"),
		"automation_label": auto.get("automation_name"),
		"space": reg.name,
		"ref_doctype": target.doctype if target else None,
		"ref_name": target.name if target else None,
		"trigger_type": auto.get("trigger_type"),
		"trigger_snapshot": json.dumps(snapshot or {}),
		"status": status,
		"actions_log": json.dumps(public_log),
		"error": overall_error,
		"duration_ms": sum(e.get("ms", 0) for e in log),
		"triggered_by": frappe.session.user,
	}).insert(ignore_permissions=True)
	_quota_bump(reg.name)
	frappe.db.set_value("SP Automation", auto["name"], {
		"last_run": frappe.utils.now_datetime(),
		"last_status": status,
		"run_count": frappe.utils.cint(auto.get("run_count")) + 1,
	}, update_modified=False)

	# enqueue any webhook deliveries now that the run row exists
	for i, entry in enumerate(log):
		if entry.get("status") == "queued":
			frappe.enqueue(
				"sprint.automation.deliver_webhook",
				queue="short", enqueue_after_commit=True,
				run=run.name, action_idx=i, url=entry["_url"],
				body=entry["_body"], secret=entry.get("_secret"),
			)
	return run.name


# ---- action handlers: each returns a human 'detail' string ----------------
# signature: handler(action_config, ctx, is_test) -> str
def _act_set_field(a, ctx, is_test):
	reg, doc = ctx["reg"], ctx["doc"]
	values = _clean_card_values(reg, {a["field"]: a.get("value")})
	if is_test:
		return f"set {a['field']} to {a.get('value')}"
	doc.set(a["field"], values.get(a["field"]))
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return f"set {a['field']} to {a.get('value')}"


def _act_move_to_bucket(a, ctx, is_test):
	reg, doc = ctx["reg"], ctx["doc"]
	_require_bucket_in_space(reg, a.get("bucket"))
	name = frappe.db.get_value("SP Bucket", a["bucket"], "bucket_name") or a["bucket"]
	if is_test:
		return f"move to {name}"
	doc.set(reg.bucket_field or "bucket", a["bucket"])
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return f"move to {name}"


def _act_assign(a, ctx, is_test):
	reg, doc, auto = ctx["reg"], ctx["doc"], ctx["auto"]
	field = reg.get("assignee_field")
	if not field:
		raise Exception("space has no assignee field")
	if a.get("users"):  # round-robin
		pool = [u for u in a["users"] if frappe.db.exists("User", u)]
		if not pool:
			raise Exception("no valid users to assign")
		idx = frappe.utils.cint(auto.get("rr_index")) % len(pool)
		user = pool[idx]
		if not is_test:
			frappe.db.set_value("SP Automation", auto["name"], "rr_index", idx + 1, update_modified=False)
			auto["rr_index"] = idx + 1
	else:
		user = a.get("user")
		if not user or not frappe.db.exists("User", user):
			raise Exception("assign action names an unknown user")
	if is_test:
		return f"assign {frappe.utils.get_fullname(user)}"
	doc.set(field, user)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return f"assign {frappe.utils.get_fullname(user)}"


def _act_apply_template(a, ctx, is_test):
	reg, doc = ctx["reg"], ctx["doc"]
	tmpl = frappe.db.get_value("SP Template", a.get("template"),
	                           ["template_name", "values_json", "space"], as_dict=True)
	if not tmpl or tmpl.space != reg.name:
		raise Exception("template not in this space")
	values = _clean_card_values(reg, _loads(tmpl.values_json) or {})
	if is_test:
		return f"apply template {tmpl.template_name}"
	doc.update(values)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return f"apply template {tmpl.template_name}"


def _act_create_card(a, ctx, is_test):
	reg = ctx["reg"]
	tmpl = frappe.db.get_value("SP Template", a.get("template"),
	                           ["template_name", "values_json", "space"], as_dict=True)
	if not tmpl or tmpl.space != reg.name:
		raise Exception("template not in this space")
	values = _clean_card_values(reg, _loads(tmpl.values_json) or {})
	title_field = reg.title_field or "title"
	values.setdefault(title_field, values.get(title_field) or ctx["auto"].get("automation_name") or "New card")
	as_subtask = a.get("as_subtask") and ctx.get("doc") is not None
	if as_subtask:
		values[reg.parent_field or "parent_task"] = ctx["doc"].name
	if is_test:
		return f"create a card from {tmpl.template_name}" + (" (subtask)" if as_subtask else "")
	new_doc = frappe.get_doc({"doctype": reg.target_doctype, **values})
	new_doc.insert(ignore_permissions=True)
	_notify_card_changes(new_doc, reg=reg, is_new=True)
	ctx["doc"] = new_doc  # subsequent actions in this rule target the new card
	return f"created a card from {tmpl.template_name}"


def _resolve_recipients(a, ctx):
	reg, doc = ctx["reg"], ctx["doc"]
	users = set(a.get("users") or [])
	tokens = a.get("recipients") or []
	if doc is not None:
		if "assignee" in tokens and reg.get("assignee_field") and doc.get(reg.assignee_field):
			users.add(doc.get(reg.assignee_field))
		if "watchers" in tokens:
			users.update(_card_watchers(doc.doctype, doc.name))
		if "requester" in tokens and doc.get("requester"):
			users.add(doc.get("requester"))
	return [u for u in users if u and frappe.db.exists("User", u)]


def _act_notify(a, ctx, is_test):
	reg, doc = ctx["reg"], ctx["doc"]
	users = _resolve_recipients(a, ctx)
	msg = render_placeholders(a.get("message") or "", doc, reg, actor=ctx["actor"])
	names = ", ".join(frappe.utils.get_fullname(u) for u in users) or "nobody"
	if is_test:
		return f"notify {names}: {msg}"
	if users and doc is not None:
		_notify(users, msg or f"Automation on “{_card_title(doc.doctype, doc.name)}”",
		        doc.doctype, doc.name, ntype="Alert")
	return f"notify {names}"


def _act_add_comment(a, ctx, is_test):
	reg, doc = ctx["reg"], ctx["doc"]
	msg = render_placeholders(a.get("message") or "", doc, reg, actor=ctx["actor"])
	if is_test:
		return f"comment: {msg}"
	doc.add_comment("Comment", msg)  # direct call — never re-enters comment trigger
	return "posted a comment"


def _act_webhook(a, ctx, is_test):
	reg, doc, auto = ctx["reg"], ctx["doc"], ctx["auto"]
	url = a.get("url")
	_validate_webhook_url(url)
	host = urlparse(url).hostname
	if is_test:
		return f"POST to {host}"
	card_fields = {}
	if doc is not None:
		card_fields = {f: doc.get(f) for f in _listable_fields(doc.doctype) if f in doc.as_dict()}
	body = json.dumps({
		"event": auto.get("trigger_type"),
		"rule": auto.get("automation_name"),
		"space": reg.name,
		"card": card_fields,
		"timestamp": frappe.utils.now(),
	})
	# secret lives on the rule; pass it to the queued job for HMAC signing
	secret = None
	try:
		secret = frappe.get_doc("SP Automation", auto["name"]).get_password("webhook_secret") if auto.get("name") else None
	except Exception:
		secret = None
	# marker fields consumed by _execute to enqueue the delivery
	raise _Queued(url=url, body=body, secret=secret, detail=f"queued POST to {host}")


class _Queued(Exception):
	"""Sentinel: an action wants to enqueue a webhook rather than run inline."""
	def __init__(self, url, body, secret, detail):
		self.url, self.body, self.secret, self.detail = url, body, secret, detail


_ACTION_HANDLERS = {
	"set_field": _act_set_field,
	"move_to_bucket": _act_move_to_bucket,
	"assign": _act_assign,
	"apply_template": _act_apply_template,
	"create_card": _act_create_card,
	"notify": _act_notify,
	"add_comment": _act_add_comment,
	"webhook": _act_webhook,
}


# ---------------------------------------------------------------------------
# dispatch — called from api.py's mutation funnel (2 lazy-import call sites)
# ---------------------------------------------------------------------------
def _automations_ready():
	"""True once per request if the SP Automation table exists."""
	if not hasattr(frappe.local, "_sprint_automation_ready"):
		frappe.local._sprint_automation_ready = frappe.db.exists("DocType", "SP Automation")
	return frappe.local._sprint_automation_ready


def _invalidate_rule_cache(space):
	cache = getattr(frappe.local, "_sprint_rules", None)
	if cache:
		cache.pop(space, None)


def _rules_for(space, trigger_types):
	"""Enabled rules for a space + trigger set, cached per request per space."""
	cache = getattr(frappe.local, "_sprint_rules", None)
	if cache is None:
		cache = frappe.local._sprint_rules = {}
	if space not in cache:
		cache[space] = frappe.get_all(
			"SP Automation",
			filters={"space": space, "enabled": 1},
			fields=["name", "automation_name", "trigger_type", "trigger_config",
			        "conditions", "actions", "run_count", "rr_index"],
		)
	return [r for r in cache[space] if r.trigger_type in trigger_types]


def _already_ran(rule_name, docname):
	seen = getattr(frappe.local, "_sprint_automation_seen", None)
	if seen is None:
		seen = frappe.local._sprint_automation_seen = set()
	key = (rule_name, docname)
	if key in seen:
		return True
	seen.add(key)
	return False


def dispatch_card_event(doc, reg=None, is_new=False):
	"""Fire matching card-event automations. Called at the end of
	api._notify_card_changes, so every mutation endpoint is covered and
	automation-made saves re-enter here (guarded by depth). Never raises."""
	try:
		if reg is None or not _automations_ready():
			return
		if getattr(frappe.local, "_sprint_automation_depth", 0) >= MAX_DEPTH:
			return
		rules = _rules_for(reg.name, EVENT_TRIGGERS)
		if not rules:
			return

		before = None if is_new else doc.get_doc_before_save()
		bucket_field = reg.bucket_field or "bucket"
		assignee_field = reg.get("assignee_field")
		changed = set()
		if before is not None:
			for df in frappe.get_meta(doc.doctype).fields:
				fn = df.fieldname
				if doc.get(fn) != before.get(fn):
					changed.add(fn)

		events = set()
		if is_new:
			events.add("card_created")
		if before is not None:
			if bucket_field in changed:
				events.add("moved_to_bucket")
			if assignee_field and assignee_field in changed:
				events.add("assignee_changed")
			if changed - {"modified", "modified_by"}:
				events.add("field_changed")
		if not events:
			return

		card = doc.as_dict()
		for rule in rules:
			if rule.trigger_type not in events:
				continue
			tc = _loads(rule.trigger_config) or {}
			if rule.trigger_type == "moved_to_bucket" and tc.get("bucket"):
				if doc.get(bucket_field) != tc["bucket"]:
					continue
			if rule.trigger_type == "field_changed":
				if tc.get("field") and tc["field"] not in changed:
					continue
				if tc.get("to_value") not in (None, "") and _s(doc.get(tc.get("field"))) != _s(tc["to_value"]):
					continue
			if _already_ran(rule.name, doc.name):
				continue
			if _quota_exceeded(reg.name):
				_log_quota_skip(reg.name)
				return
			if not match_conditions(card, _loads(rule.conditions) or []):
				continue
			snapshot = {"event": rule.trigger_type, "changed": sorted(changed), "is_new": is_new}
			_execute(rule, reg, doc, snapshot)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Sprint automation dispatch")


def dispatch_comment_event(doctype, name, content):
	"""Fire comment_added automations. Called from api.add_comment. Comments
	created by the add_comment *action* call doc.add_comment directly (not the
	endpoint), so they can never re-enter here. Never raises."""
	try:
		if not _automations_ready():
			return
		if getattr(frappe.local, "_sprint_automation_depth", 0) >= MAX_DEPTH:
			return
		reg = _space_reg(doctype=doctype)
		if not reg:
			return
		rules = _rules_for(reg.name, ("comment_added",))
		if not rules:
			return
		doc = frappe.get_doc(doctype, name)
		card = doc.as_dict()
		for rule in rules:
			if _already_ran(rule.name, name):
				continue
			if _quota_exceeded(reg.name):
				_log_quota_skip(reg.name)
				return
			if not match_conditions(card, _loads(rule.conditions) or []):
				continue
			snapshot = {"event": "comment_added", "comment_excerpt": (content or "")[:140]}
			_execute(rule, reg, doc, snapshot)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Sprint automation comment dispatch")


# ---------------------------------------------------------------------------
# webhook delivery (background job) — single attempt, no redirects
# ---------------------------------------------------------------------------
def deliver_webhook(run, action_idx, url, body, secret=None):
	import requests

	status_detail = ""
	ok = False
	try:
		_validate_webhook_url(url)  # re-check: DNS may have changed since save
		headers = {"Content-Type": "application/json", "User-Agent": "Sprint-Automation/1"}
		if secret:
			sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
			headers["X-Sprint-Signature"] = f"sha256={sig}"
		resp = requests.post(url, data=body, headers=headers, timeout=10, allow_redirects=False)
		ok = 200 <= resp.status_code < 300
		status_detail = f"HTTP {resp.status_code}"
	except Exception as e:
		status_detail = str(e)[:200]

	# patch the run's action log entry + downgrade Success→Partial on failure
	if not frappe.db.exists("SP Automation Run", run):
		return
	doc = frappe.get_doc("SP Automation Run", run)
	try:
		log = json.loads(doc.actions_log or "[]")
	except Exception:
		log = []
	if 0 <= action_idx < len(log):
		log[action_idx]["status"] = "ok" if ok else "failed"
		log[action_idx]["detail"] = f"{log[action_idx].get('detail','')} · {status_detail}".strip(" ·")
	new_status = doc.status
	if not ok and doc.status == "Success":
		new_status = "Partial"
	frappe.db.set_value("SP Automation Run", run, {
		"actions_log": json.dumps(log), "status": new_status,
	}, update_modified=False)
	frappe.db.commit()


# ---------------------------------------------------------------------------
# scheduler jobs (registered in hooks.py scheduler_events)
# ---------------------------------------------------------------------------
def process_time_based_automations():
	"""Runs every 5 minutes. Fires scheduled + due-date + inactivity rules.
	Idempotent and bounded; site-tz throughout; skips missing spaces."""
	if not frappe.db.exists("DocType", "SP Automation"):
		return
	frappe.set_user("Administrator")
	now = frappe.utils.now_datetime()

	rules = frappe.get_all(
		"SP Automation",
		filters={"enabled": 1, "trigger_type": ["in", SCHEDULER_TRIGGERS]},
		fields=["name", "automation_name", "space", "trigger_type", "trigger_config",
		        "conditions", "actions", "run_count", "rr_index", "next_run"],
	)
	for rule in rules:
		try:
			reg = _space_reg(space=rule.space)
			if not reg or not frappe.db.exists("DocType", reg.target_doctype):
				continue
			if _quota_exceeded(reg.name):
				_log_quota_skip(reg.name)
				continue
			if rule.trigger_type == "scheduled":
				_run_scheduled(rule, reg, now)
			else:
				_run_card_scan(rule, reg, now)
			frappe.db.commit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Sprint scheduled automation {rule.name}")
			frappe.db.rollback()


def _run_scheduled(rule, reg, now):
	tc = _loads(rule.trigger_config) or {}
	if not rule.next_run or frappe.utils.get_datetime(rule.next_run) > now:
		return
	# fire once, then jump to the next future slot (no backfill storm)
	_execute(rule, reg, None, {"event": "scheduled"})
	nxt = compute_next_run(tc, after=now)
	frappe.db.set_value("SP Automation", rule.name, "next_run", nxt, update_modified=False)


def _run_card_scan(rule, reg, now):
	tc = _loads(rule.trigger_config) or {}
	doctype = reg.target_doctype
	meta = frappe.get_meta(doctype)
	bucket_field = reg.bucket_field or "bucket"
	closed = frappe.get_all("SP Bucket", filters={"space": reg.name, "is_closed": 1}, pluck="name") \
		if frappe.db.has_column("SP Bucket", "is_closed") else []
	filters = {}
	if closed and meta.has_field(bucket_field):
		filters[bucket_field] = ["not in", closed]

	if rule.trigger_type in ("due_date_arrived", "due_date_approaching"):
		due_field = reg.get("due_field")
		if not due_field or not meta.has_field(due_field):
			return
		days = frappe.utils.cint(tc.get("days_before")) if rule.trigger_type == "due_date_approaching" else 0
		target = frappe.utils.add_days(frappe.utils.today(), days)
		filters[due_field] = target
	elif rule.trigger_type == "card_inactive":
		days = frappe.utils.cint(tc.get("days")) or 1
		cutoff = frappe.utils.add_to_date(now, days=-days)
		filters["modified"] = ["<=", cutoff]
	else:
		return

	cards = frappe.get_all(doctype, filters=filters, pluck="name",
	                       order_by="modified desc", limit_page_length=200)
	if not cards:
		return
	conditions = _loads(rule.conditions) or []
	# dedupe via the run log: due-date = once/day; inactive = once ever (within retention)
	same_day = rule.trigger_type != "card_inactive"
	for name in cards:
		if _quota_exceeded(reg.name):
			_log_quota_skip(reg.name)
			return
		run_filter = {"automation": rule.name, "ref_name": name}
		if same_day:
			run_filter["creation"] = [">=", frappe.utils.today()]
		if frappe.db.exists("SP Automation Run", run_filter):
			continue
		doc = frappe.get_doc(doctype, name)
		if not match_conditions(doc.as_dict(), conditions):
			continue
		_execute(rule, reg, doc, {"event": rule.trigger_type})


def prune_automation_runs():
	"""Daily: drop run rows older than the retention window, in batches."""
	if not frappe.db.exists("DocType", "SP Automation Run"):
		return
	retention = frappe.utils.cint(frappe.conf.get("sprint_automation_run_retention_days")) or 30
	cutoff = frappe.utils.add_days(frappe.utils.today(), -retention)
	while True:
		rows = frappe.db.sql(
			"select name from `tabSP Automation Run` where creation < %s limit 5000", cutoff
		)
		if not rows:
			break
		frappe.db.sql(
			"delete from `tabSP Automation Run` where creation < %s limit 5000", cutoff
		)
		frappe.db.commit()


# ---------------------------------------------------------------------------
# whitelisted endpoints
# ---------------------------------------------------------------------------
def _rule_dict(d, include_secret_flag=True):
	out = {
		"name": d.name,
		"automation_name": d.automation_name,
		"enabled": d.enabled,
		"description": d.description,
		"trigger_type": d.trigger_type,
		"trigger_config": _loads(d.trigger_config) or {},
		"conditions": _loads(d.conditions) or [],
		"actions": _loads(d.actions) or [],
		"run_count": d.run_count or 0,
		"last_run": str(d.last_run) if d.last_run else None,
		"last_status": d.last_status,
		"next_run": str(d.next_run) if d.next_run else None,
	}
	if include_secret_flag:
		out["has_secret"] = bool(frappe.db.get_value("SP Automation", d.name, "webhook_secret"))
	return out


@frappe.whitelist()
def get_automations(space):
	"""Rules for a space + the daily-quota block. Space read access required."""
	_require_space_access(space=space, mode="read")
	rows = frappe.get_all(
		"SP Automation",
		filters={"space": space},
		fields=["name", "automation_name", "enabled", "description", "trigger_type",
		        "trigger_config", "conditions", "actions", "run_count", "last_run",
		        "last_status", "next_run"],
		order_by="creation asc",
	)
	limit = _daily_quota()
	used = frappe.db.count("SP Automation Run", {"space": space, "creation": [">=", frappe.utils.today()]})
	return {
		"rules": [_rule_dict(frappe._dict(r)) for r in rows],
		"quota": {"limit": limit, "used": used, "remaining": max(0, limit - used)},
	}


@frappe.whitelist(methods=["POST"])
def save_automation(space, automation_name, trigger_type, trigger_config=None,
                    conditions=None, actions=None, enabled=1, description=None,
                    webhook_secret=None, name=None):
	"""Create or update a rule. Manager + space-write gated; fully validated."""
	_require_manager()
	reg = _require_space_access(space=space, mode="write")
	automation_name = (automation_name or "").strip()
	if not automation_name:
		frappe.throw(_("Name your automation."))
	tc = _loads(trigger_config, "trigger_config") or {}
	conds = _loads(conditions, "conditions") or []
	acts = _loads(actions, "actions") or []
	_validate_definition(reg, trigger_type, tc, conds, acts)

	values = {
		"space": space,
		"automation_name": automation_name,
		"enabled": frappe.utils.cint(enabled),
		"description": description,
		"trigger_type": trigger_type,
		"trigger_config": json.dumps(tc),
		"conditions": json.dumps(conds),
		"actions": json.dumps(acts),
	}
	if trigger_type == "scheduled" and values["enabled"]:
		values["next_run"] = compute_next_run(tc)
	else:
		values["next_run"] = None

	if name and frappe.db.exists("SP Automation", name):
		doc = frappe.get_doc("SP Automation", name)
		doc.update(values)
		if webhook_secret is not None:
			doc.webhook_secret = webhook_secret
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "SP Automation", **values})
		if webhook_secret:
			doc.webhook_secret = webhook_secret
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
	_invalidate_rule_cache(space)
	return _rule_dict(doc)


@frappe.whitelist(methods=["POST"])
def toggle_automation(name, enabled):
	_require_manager()
	space = frappe.db.get_value("SP Automation", name, "space")
	_require_space_access(space=space, mode="write")
	enabled = frappe.utils.cint(enabled)
	doc = frappe.get_doc("SP Automation", name)
	doc.enabled = enabled
	# recompute next_run so a long-disabled scheduled rule doesn't insta-fire
	if doc.trigger_type == "scheduled" and enabled:
		doc.next_run = compute_next_run(_loads(doc.trigger_config) or {})
	elif not enabled:
		doc.next_run = None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_invalidate_rule_cache(space)
	return {"name": name, "enabled": enabled}


@frappe.whitelist(methods=["POST"])
def delete_automation(name):
	"""Delete the rule. Its run rows are intentionally kept (quota integrity;
	they prune out on the retention schedule)."""
	_require_manager()
	space = frappe.db.get_value("SP Automation", name, "space")
	if space:
		_require_space_access(space=space, mode="write")
	frappe.delete_doc("SP Automation", name, ignore_permissions=True)
	frappe.db.commit()
	if space:
		_invalidate_rule_cache(space)
	return {"deleted": name}


@frappe.whitelist()
def get_automation_runs(space, automation=None, limit=50):
	"""Run log for a space (optionally one rule), newest first. Space read."""
	_require_space_access(space=space, mode="read")
	filters = {"space": space}
	if automation:
		filters["automation"] = automation
	rows = frappe.get_all(
		"SP Automation Run",
		filters=filters,
		fields=["name", "automation", "automation_label", "ref_doctype", "ref_name",
		        "trigger_type", "status", "actions_log", "error", "duration_ms",
		        "triggered_by", "creation"],
		order_by="creation desc",
		limit_page_length=min(frappe.utils.cint(limit) or 50, 200),
	)
	# resolve a display title for the card link (graceful if it's gone)
	title_cache = {}
	for r in rows:
		r["actions_log"] = _loads(r.actions_log) or []
		r["doc_title"] = None
		if r.ref_doctype and r.ref_name:
			key = (r.ref_doctype, r.ref_name)
			if key not in title_cache:
				treg = _space_reg(doctype=r.ref_doctype)
				tf = (treg.title_field if treg else None) or "title"
				try:
					title_cache[key] = frappe.db.get_value(r.ref_doctype, r.ref_name, tf)
				except Exception:
					title_cache[key] = None
			r["doc_title"] = title_cache[key]
	return rows


@frappe.whitelist(methods=["POST"])
def run_automation_test(automation, card):
	"""Dry-run: report what the rule WOULD do against `card`, writing nothing.
	Manager-gated. Reuses the real matcher + action resolve halves (is_test)."""
	_require_manager()
	auto = frappe.get_doc("SP Automation", automation)
	reg = _require_space_access(space=auto.space, mode="read")
	doc = frappe.get_doc(reg.target_doctype, card)
	conds = _loads(auto.conditions) or []
	cond_report = []
	for c in conds:
		cond_report.append({
			"field": c.get("field"), "operator": c.get("operator"), "value": c.get("value"),
			"passed": match_conditions(doc.as_dict(), [c]),
		})
	would_match = match_conditions(doc.as_dict(), conds)
	report = {"trigger_would_match": would_match, "conditions": cond_report, "actions": []}
	if would_match:
		result = _execute(frappe._dict(auto.as_dict()), reg, doc,
		                  {"event": auto.trigger_type, "is_test": True}, is_test=True)
		report["actions"] = result.get("actions", [])
	return report


@frappe.whitelist()
def get_automation_recipes():
	"""Static prebuilt rules the builder pre-fills. Any logged-in user."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	return RECIPES
