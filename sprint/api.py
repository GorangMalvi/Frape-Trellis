"""Whitelisted endpoints powering the Sprint board UI.

These are framework plumbing (read the registry / DocType meta and shape it for
the generic renderer). Per-space *business* logic belongs in Server Scripts on
the space's own DocType.
"""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

# fieldtypes the board UI never needs to render
_LAYOUT_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Heading"}
_SYSTEM_FIELDS = {"naming_series", "amended_from"}
# heavy / relational fieldtypes we don't fetch into the board+list grid
_NON_LISTABLE = _LAYOUT_TYPES | {
    "Text Editor", "Long Text", "Code", "Markdown Editor", "HTML Editor",
    "Table", "Table MultiSelect", "Signature", "Geolocation", "Text",
}
_SERVER_OWNED_TICKET_FIELDS = {"doctype", "name", "requester", "owner", "creation", "modified", "modified_by"}


def _is_manager():
	"""Administrator, or anyone holding the Sprint Manager role, may make
	structural changes (spaces, fields, buckets, import/export)."""
	return (
		frappe.session.user == "Administrator"
		or "Sprint Manager" in frappe.get_roles()
	)


def _require_manager():
	"""Structural changes (spaces, fields, buckets, bulk data import/export)
	require Administrator or the Sprint Manager role. Cards, views, comments
	and attachments stay open to all permitted users — enforced here so UI
	gating can't be bypassed."""
	if not _is_manager():
		frappe.throw(_("Only a Sprint manager can do this."), frappe.PermissionError)


def _loads(value, what="payload"):
	"""json.loads that raises a clean validation error instead of a 500."""
	if not isinstance(value, str):
		return value
	try:
		return json.loads(value or "null")
	except Exception:
		frappe.throw(_("Invalid JSON for {0}.").format(what))


# identity/system columns no generic card write may ever touch
_WRITE_BLOCKED_FIELDS = {
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"doctype", "parent", "parentfield", "parenttype",
	"_assign", "_comments", "_liked_by", "_user_tags",
}


def _clean_card_values(reg, values):
	"""Guard a generic {field: value} write: strip system columns, reject
	fields that don't exist on the space's DocType, and make sure a bucket
	value actually belongs to this space."""
	values = {k: v for k, v in (values or {}).items() if k not in _WRITE_BLOCKED_FIELDS}
	meta = frappe.get_meta(reg.target_doctype)
	unknown = [k for k in values if not meta.has_field(k)]
	if unknown:
		frappe.throw(_("Unknown field(s): {0}").format(", ".join(sorted(unknown))))
	bucket_field = reg.bucket_field or "bucket"
	if values.get(bucket_field):
		_require_bucket_in_space(reg, values[bucket_field])
	return values


def _require_bucket_in_space(reg, bucket):
	if frappe.db.get_value("SP Bucket", bucket, "space") != reg.name:
		frappe.throw(_("Bucket does not belong to this space."))


def _space_reg(space=None, doctype=None):
	"""Return the SP Space registry row by registry name or target DocType."""
	if space:
		return frappe.get_doc("SP Space", space)
	name = frappe.db.get_value("SP Space", {"target_doctype": doctype}, "name")
	return frappe.get_doc("SP Space", name) if name else None


def _is_ticket_reg(reg):
	return (reg.get("space_type") or "Task") == "Ticket"


def _space_access_mode(reg, fieldname):
	return reg.get(fieldname) or "All"


def _space_access_rows(reg):
	return list(reg.get("access_users") or [])


def can_access_space(reg, mode="read", user=None):
	"""App-level space visibility/editability.

	All = every logged-in user. Selected Users = rows in SP Space Access.
	Administrator can always access so configuration mistakes can be fixed.
	"""
	user = user or frappe.session.user
	if user == "Guest":
		return False
	if user == "Administrator":
		return True

	fieldname = "write_access" if mode == "write" else "read_access"
	if _space_access_mode(reg, fieldname) == "All":
		return True
	if mode == "read" and _space_access_mode(reg, "write_access") == "All":
		return True

	for row in _space_access_rows(reg):
		if row.user != user:
			continue
		if mode == "write" and row.can_write:
			return True
		if mode == "read" and (row.can_read or row.can_write):
			return True
	return False


def _require_space_access(reg=None, space=None, doctype=None, mode="read"):
	reg = reg or _space_reg(space=space, doctype=doctype)
	if reg and can_access_space(reg, mode=mode):
		return reg
	frappe.throw(_("You do not have {0} access to this space.").format(mode), frappe.PermissionError)


def is_ticket_space(space=None, doctype=None):
	reg = _space_reg(space=space, doctype=doctype)
	return bool(reg and _is_ticket_reg(reg))


def get_user_descendants(user=None):
	"""All recursive lower nodes from the User.manager tree.
	Memoized per request — ticket loops call this once per doc otherwise."""
	user = user or frappe.session.user
	cache = getattr(frappe.local, "_sprint_descendants", None)
	if cache is None:
		cache = frappe.local._sprint_descendants = {}
	if user in cache:
		return cache[user]
	# `manager` is a site-level custom field on User, not core Frappe — without it
	# there is no reporting tree, so a user sees only their own tickets.
	if not frappe.get_meta("User").has_field("manager"):
		cache[user] = []
		return cache[user]
	seen = set()
	frontier = [user]
	while frontier:
		children = frappe.get_all(
			"User",
			filters={"manager": ["in", frontier]},
			pluck="name",
		)
		frontier = [u for u in children if u not in seen and u != user]
		seen.update(frontier)
	cache[user] = sorted(seen)
	return cache[user]


def _ticket_visible_requesters(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return None
	return [user, *get_user_descendants(user)]


def can_access_ticket(doctype, name, mode="read", user=None, reg=None):
	"""Ticket access is based on ticket.requester in the user's manager tree."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	reg = reg or _space_reg(doctype=doctype)
	if not reg or not _is_ticket_reg(reg):
		return bool(reg and can_access_space(reg, mode=mode, user=user))
	if not can_access_space(reg, mode=mode, user=user):
		return False
	requester = frappe.db.get_value(doctype, name, "requester")
	return requester in _ticket_visible_requesters(user)


def _require_ticket_access(doctype, name, mode="read", reg=None):
	if can_access_ticket(doctype, name, mode=mode, reg=reg):
		return
	frappe.throw(_("You do not have access to this ticket."), frappe.PermissionError)


def ticket_query_filter(user=None):
	"""Filters that return tickets visible to user, or all tickets for Administrator."""
	requesters = _ticket_visible_requesters(user)
	if requesters is None:
		return {}
	return {"requester": ["in", requesters]}


def _listable_fields(doctype):
	meta = frappe.get_meta(doctype)
	wanted = ["name", "modified", "owner", "_assign"]
	for df in meta.fields:
		if df.fieldtype not in _NON_LISTABLE and df.fieldname not in _SYSTEM_FIELDS:
			wanted.append(df.fieldname)
	return list(dict.fromkeys(wanted))


@frappe.whitelist()
def get_spaces():
	"""Sidebar: every registered space, ordered."""
	fields = ["name", "target_doctype", "label", "icon", "color", "sort_order"]
	if frappe.db.has_column("SP Space", "space_type"):
		fields.append("space_type")
	if frappe.db.has_column("SP Space", "read_access"):
		fields.append("read_access")
	if frappe.db.has_column("SP Space", "write_access"):
		fields.append("write_access")
	spaces = frappe.get_all(
		"SP Space",
		fields=fields,
		order_by="sort_order asc, label asc",
	)
	# batch-load the per-space ACL child rows instead of get_doc per space
	access = {}
	if frappe.db.exists("DocType", "SP Space Access"):
		for row in frappe.get_all(
			"SP Space Access",
			filters={"parenttype": "SP Space"},
			fields=["parent", "user", "can_read", "can_write"],
		):
			access.setdefault(row.parent, []).append(row)
	for s in spaces:
		reg = frappe._dict(s, access_users=access.get(s.name, []))
		s["can_read"] = can_access_space(reg, "read")
		s["can_write"] = can_access_space(reg, "write")
	return [s for s in spaces if s["can_read"]]


@frappe.whitelist()
def get_space(space):
	"""Full config for one space: registry pointers, buckets, and field meta."""
	reg = frappe.get_doc("SP Space", space)
	_require_space_access(reg=reg, mode="read")
	doctype = reg.target_doctype

	meta = frappe.get_meta(doctype)
	protected_fields = _protected_fields(reg)
	fields = []
	for df in meta.fields:
		if df.fieldtype in _LAYOUT_TYPES or df.fieldname in _SYSTEM_FIELDS or df.hidden:
			continue
		fields.append({
			"fieldname": df.fieldname,
			"label": df.label,
			"fieldtype": df.fieldtype,
			"options": df.options,
			"reqd": df.reqd,
			"read_only": df.read_only,
			"in_list_view": df.in_list_view,
			"can_delete": df.fieldname not in protected_fields,
			"depends_on": df.depends_on,
			"mandatory_depends_on": df.mandatory_depends_on,
			"read_only_depends_on": df.read_only_depends_on,
		})

	bucket_fields = ["name", "bucket_name", "color", "sort_order", "wip_limit"]
	if frappe.db.has_column("SP Bucket", "is_closed"):
		bucket_fields.append("is_closed")
	buckets = frappe.get_all(
		"SP Bucket",
		filters={"space": space},
		fields=bucket_fields,
		order_by="sort_order asc",
	)

	try:
		chip_options = json.loads(reg.get("chip_options")) if reg.get("chip_options") else {}
	except Exception:
		chip_options = {}

	dashboard = None
	if reg.get("dashboard_json"):
		dashboard = _loads(reg.get("dashboard_json")) if isinstance(reg.get("dashboard_json"), str) else reg.get("dashboard_json")

	return {
		"space": {
			"name": reg.name,
			"doctype": doctype,
			"label": reg.label,
			"icon": reg.icon,
			"color": reg.color,
			"space_type": reg.get("space_type") or "Task",
			"title_field": reg.title_field or "title",
			"bucket_field": reg.bucket_field or "bucket",
			"assignee_field": reg.assignee_field,
			"body_field": reg.body_field,
			"parent_field": reg.parent_field or "parent_task",
			"badge_field": reg.get("badge_field") or "sprint_points",
			"due_field": reg.get("due_field"),
			"chip_fields": [c.strip() for c in (reg.get("chip_fields") or "").split(",") if c.strip()],
			"chip_options": chip_options,
			"ticket_members": [row.user for row in (reg.get("ticket_members") or []) if row.user],
			"read_access": reg.get("read_access") or "All",
			"write_access": reg.get("write_access") or "All",
			"access_users": [
				{"user": row.user, "can_read": bool(row.can_read), "can_write": bool(row.can_write)}
				for row in _space_access_rows(reg)
				if row.user
			],
			"dashboard": dashboard,
		},
		"buckets": buckets,
		"fields": fields,
		"current_user": frappe.session.user,
		"can_manage": _is_manager(),
		"can_write_space": can_access_space(reg, "write"),
	}


@frappe.whitelist()
def get_cards(space):
	"""All cards for a space with every listable field — the board, list view,
	filtering and sorting all run client-side off this single payload."""
	reg = frappe.get_doc("SP Space", space)
	_require_space_access(reg=reg, mode="read")
	doctype = reg.target_doctype
	wanted = _listable_fields(doctype)
	if _is_ticket_reg(reg):
		return frappe.get_all(
			doctype,
			filters=ticket_query_filter(),
			fields=wanted,
			order_by="modified desc",
			limit_page_length=0,
			ignore_permissions=True,
		)
	return frappe.get_all(doctype, fields=wanted, order_by="modified desc", limit_page_length=0, ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def move_card(doctype, name, bucket):
	"""Drag-and-drop: move a card to a different bucket."""
	reg = _space_reg(doctype=doctype)
	if reg and _is_ticket_reg(reg):
		_require_ticket_access(doctype, name, "write", reg=reg)
	else:
		_require_space_access(reg=reg, doctype=doctype, mode="write")
	bucket_field = (reg.bucket_field if reg else None) or "bucket"
	if reg and bucket:
		_require_bucket_in_space(reg, bucket)
	doc = frappe.get_doc(doctype, name)
	setattr(doc, bucket_field, bucket)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return {"name": name, "bucket": bucket}


@frappe.whitelist(methods=["POST"])
def set_field(doctype, name, fieldname, value):
	"""Single-field update for inline edits. Goes through the ORM (doc.save)
	so validations, Server Script DocType events, Version/audit, and the
	realtime list_update all fire — consistent with drawer/drag edits."""
	reg = _space_reg(doctype=doctype)
	ticket = bool(reg and _is_ticket_reg(reg))
	if ticket:
		_require_ticket_access(doctype, name, "write", reg=reg)
		if fieldname in _SERVER_OWNED_TICKET_FIELDS:
			frappe.throw(_("{0} is managed by the server.").format(fieldname))
	else:
		_require_space_access(reg=reg, doctype=doctype, mode="write")
	if reg:
		_clean_card_values(reg, {fieldname: value})
	doc = frappe.get_doc(doctype, name)
	doc.set(fieldname, value)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	return {"name": name, "fieldname": fieldname, "value": value}


@frappe.whitelist(methods=["POST"])
def create_card(space, values):
	reg = _require_space_access(space=space, mode="write")
	if _is_ticket_reg(reg):
		frappe.throw(_("Use create_ticket for ticket spaces."))
	values = _clean_card_values(reg, _loads(values, "values") or {})
	doc = frappe.get_doc({"doctype": reg.target_doctype, **values})
	doc.insert(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg, is_new=True)
	frappe.db.commit()
	return {field: doc.get(field) for field in _listable_fields(doc.doctype) if field in doc.as_dict()}


@frappe.whitelist(methods=["POST"])
def update_card(doctype, name, values):
	reg = _require_space_access(doctype=doctype, mode="write")
	if _is_ticket_reg(reg):
		frappe.throw(_("Use update_ticket for ticket spaces."))
	values = _clean_card_values(reg, _loads(values, "values") or {})
	doc = frappe.get_doc(doctype, name)
	doc.update(values)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg)
	frappe.db.commit()
	return {field: doc.get(field) for field in _listable_fields(doc.doctype) if field in doc.as_dict()}


@frappe.whitelist(methods=["POST"])
def create_space_api(label, icon=None, color=None, fields=None, buckets=None):
	_require_manager()
	"""Admin: create a new space (Custom DocType + registry + buckets) from the UI.

	`fields` is a dict of optional toggles: {priority, assignee, due_date, body}.
	`buckets` is a list of {bucket_name, color}.
	"""

	from sprint.setup import ensure_space_doctype, create_space

	label = (label or "").strip()
	if not label:
		frappe.throw(_("Space name is required"))
	doctype = label
	if frappe.db.exists("DocType", doctype):
		frappe.throw(_("A DocType named '{0}' already exists — pick another name").format(doctype))

	opts = _loads(fields, "fields") or {}
	df = [{"fieldname": "title", "label": "Title", "fieldtype": "Data", "reqd": 1, "in_list_view": 1}]
	assignee_field = body_field = due_field = None
	if opts.get("sprint_points"):
		df.append({"fieldname": "sprint_points", "label": "Sprint Points", "fieldtype": "Select",
		           "options": "\n".join(str(i) for i in range(1, 11)), "in_list_view": 1})
	if opts.get("assignee"):
		df.append({"fieldname": "assignee", "label": "Assignee", "fieldtype": "Link", "options": "User"})
		assignee_field = "assignee"
	if opts.get("due_date"):
		df.append({"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date"})
		due_field = "due_date"
	if opts.get("body"):
		df.append({"fieldname": "body", "label": "Body", "fieldtype": "Text Editor"})
		body_field = "body"
	chip_fields = ""
	if opts.get("tags"):
		df.append({"fieldname": "tags", "label": "Tags", "fieldtype": "Small Text"})
		chip_fields = "tags"

	ensure_space_doctype(doctype, df)

	bk = _loads(buckets, "buckets") or []
	if not bk:
		bk = [{"bucket_name": "To Do"}, {"bucket_name": "In Progress"}, {"bucket_name": "Done"}]

	create_space(doctype, label=label, icon=icon, color=color,
	             assignee_field=assignee_field, body_field=body_field,
	             badge_field="sprint_points", due_field=due_field,
	             chip_fields=chip_fields, buckets=bk)

	if chip_fields == "tags":
		from sprint.setup import DEFAULT_TAG_OPTIONS
		frappe.db.set_value("SP Space", doctype, "chip_options",
		                    json.dumps({"tags": list(DEFAULT_TAG_OPTIONS)}), update_modified=False)
		frappe.db.commit()
	return {"name": doctype, "label": label}


@frappe.whitelist(methods=["POST"])
def update_space_settings(space, label=None, icon=None, color=None):
	_require_manager()
	reg = frappe.get_doc("SP Space", space)
	if label is not None:
		label = (label or "").strip()
		if not label:
			frappe.throw(_("Space name is required"))
		reg.label = label
	if icon is not None:
		reg.icon = (icon or "").strip()[:4]
	if color is not None:
		color = (color or "").strip()
		if color:
			reg.color = color
	reg.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": reg.name, "label": reg.label, "icon": reg.icon, "color": reg.color}


# fieldtypes a dashboard widget can group cards by / sum
_GROUPABLE_TYPES = {"Select", "Link", "Check", "Small Text"}
_NUMERIC_TYPES = {"Int", "Float", "Currency", "Percent", "Duration"}


@frappe.whitelist(methods=["POST"])
def save_dashboard(space, widgets):
	"""Persist a space's dashboard layout (manager-gated). `widgets` is a JSON
	list of widget configs; validated against the space's fields. Saving an
	empty list resets to the auto-generated default (stored as null)."""
	_require_manager()
	reg = _require_space_access(space=space, mode="write")
	meta = frappe.get_meta(reg.target_doctype)
	widgets = _loads(widgets, "widgets") or []
	bucket_field = reg.bucket_field or "bucket"

	def field_ok(fn):
		return fn == bucket_field or meta.has_field(fn)

	clean = []
	for w in widgets:
		if not isinstance(w, dict):
			continue
		wtype = w.get("type")
		if wtype not in ("stat", "chart"):
			frappe.throw(_("Unknown widget type: {0}").format(wtype))
		# validate referenced fields exist on the space
		for key in ("group_by", "measure_field", "field"):
			if w.get(key) and not field_ok(w[key]):
				frappe.throw(_("Widget references a missing field: {0}").format(w[key]))
		clean.append(w)

	frappe.db.set_value("SP Space", space, "dashboard_json",
	                    json.dumps({"widgets": clean}) if clean else None,
	                    update_modified=False)
	frappe.db.commit()
	return {"space": space, "widgets": clean}


@frappe.whitelist(methods=["POST"])
def create_ticket_space_api(label, icon=None, color=None, buckets=None, members=None):
	_require_manager()
	"""Admin: create a ticket space backed by a Custom DocType.

	Ticket spaces reuse the board/list renderer but are marked with
	SP Space.space_type = Ticket so ticket-specific access rules apply.
	"""

	from sprint.setup import create_ticket_space

	label = (label or "").strip()
	if not label:
		frappe.throw(_("Ticket space name is required"))
	doctype = label
	if frappe.db.exists("DocType", doctype):
		frappe.throw(_("A DocType named '{0}' already exists — pick another name").format(doctype))

	bk = _loads(buckets, "buckets") or []
	if not bk:
		bk = [{"bucket_name": "Open"}, {"bucket_name": "In Progress"}, {"bucket_name": "Closed"}]
	member_list = _parse_members(members)
	if not member_list:
		frappe.throw(_("At least one ticket member is required."))

	create_ticket_space(doctype, label=label, icon=icon or "T", color=color, buckets=bk, members=member_list)
	return {"name": doctype, "label": label}


def _ticket_payload(doc):
	return {field: doc.get(field) for field in _listable_fields(doc.doctype) if field in doc.as_dict()}


def _require_ticket_space(space):
	reg = _space_reg(space=space)
	if not reg or not _is_ticket_reg(reg):
		frappe.throw(_("'{0}' is not a ticket space.").format(space))
	return reg


def _parse_members(members):
	if not members:
		return []
	if isinstance(members, str):
		members = _loads(members, "members")
	out = []
	for user in members or []:
		user = str(user).strip()
		if user and user not in out:
			if not frappe.db.exists("User", user):
				frappe.throw(_("User '{0}' does not exist.").format(user))
			out.append(user)
	return out


def _ticket_member_users(space):
	reg = _require_ticket_space(space)
	return [row.user for row in (reg.get("ticket_members") or []) if row.user]


def _validate_ticket_assignee(space, assignee):
	members = _ticket_member_users(space)
	if not members:
		frappe.throw(_("Add ticket members before creating tickets in this space."))
	if not assignee:
		frappe.throw(_("Responsible person is required."))
	if assignee not in members:
		frappe.throw(_("Responsible person must be a ticket member."))


@frappe.whitelist()
def get_ticket_members(space):
	"""Selectable responsible people for a ticket space."""
	return _ticket_member_users(space)


@frappe.whitelist(methods=["POST"])
def set_ticket_members(space, members):
	_require_manager()
	reg = _require_ticket_space(space)
	member_list = _parse_members(members)
	if not member_list:
		frappe.throw(_("At least one ticket member is required."))
	reg.ticket_members = []
	for user in member_list:
		reg.append("ticket_members", {"user": user})
	reg.save(ignore_permissions=True)
	frappe.db.commit()
	return {"space": space, "members": member_list}


def _parse_space_access_users(users):
	users = _loads(users, "users") or []
	out = []
	seen = set()
	for row in users:
		if isinstance(row, str):
			row = {"user": row, "can_read": 1, "can_write": 0}
		user = str(row.get("user") or "").strip()
		if not user or user in seen:
			continue
		if not frappe.db.exists("User", user):
			frappe.throw(_("User '{0}' does not exist.").format(user))
		can_write = bool(row.get("can_write"))
		can_read = bool(row.get("can_read")) or can_write
		out.append({"user": user, "can_read": can_read, "can_write": can_write})
		seen.add(user)
	return out


@frappe.whitelist()
def get_space_access(space):
	_require_manager()
	reg = frappe.get_doc("SP Space", space)
	return {
		"read_access": reg.get("read_access") or "All",
		"write_access": reg.get("write_access") or "All",
		"users": [
			{"user": row.user, "can_read": bool(row.can_read), "can_write": bool(row.can_write)}
			for row in _space_access_rows(reg)
			if row.user
		],
	}


@frappe.whitelist(methods=["POST"])
def set_space_access(space, read_access="All", write_access="All", users=None):
	_require_manager()
	if read_access not in ("All", "Selected Users"):
		frappe.throw(_("Unknown view access mode."))
	if write_access not in ("All", "Selected Users"):
		frappe.throw(_("Unknown edit access mode."))
	reg = frappe.get_doc("SP Space", space)
	reg.read_access = read_access
	reg.write_access = write_access
	reg.access_users = []
	for row in _parse_space_access_users(users):
		reg.append("access_users", row)
	reg.save(ignore_permissions=True)
	frappe.db.commit()
	return get_space_access(space)


@frappe.whitelist(methods=["POST"])
def create_ticket(space, title, description=None, assignee=None, priority=None, bucket=None, values=None):
	"""Create a ticket as the current user. requester is always server-owned."""
	reg = _require_space_access(reg=_require_ticket_space(space), mode="read")
	doctype = reg.target_doctype
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)

	title = (title or "").strip()
	if not title:
		frappe.throw(_("Title is required"))
	_validate_ticket_assignee(space, assignee)
	if bucket:
		_require_bucket_in_space(reg, bucket)

	extra = _loads(values, "values") or {}
	for protected in _SERVER_OWNED_TICKET_FIELDS:
		extra.pop(protected, None)
	extra = _clean_card_values(reg, extra)

	doc = frappe.get_doc({
		"doctype": doctype,
		**extra,
		"title": title,
		"requester": frappe.session.user,
	})
	if description is not None:
		doc.set(reg.body_field or "description", description)
	if assignee is not None:
		doc.set(reg.assignee_field or "assignee", assignee)
	if priority is not None:
		doc.set(reg.badge_field or "priority", priority)
	if bucket is not None:
		doc.set(reg.bucket_field or "bucket", bucket)
	doc.insert(ignore_permissions=True)
	_notify_card_changes(doc, reg=reg, is_new=True)
	frappe.db.commit()
	return _ticket_payload(doc)


@frappe.whitelist()
def get_ticket(doctype, name):
	_require_ticket_access(doctype, name, "read")
	doc = frappe.get_doc(doctype, name)
	return doc.as_dict()


@frappe.whitelist()
def list_tickets(space):
	reg = _require_ticket_space(space)
	return frappe.get_all(
		reg.target_doctype,
		filters=ticket_query_filter(),
		fields=_listable_fields(reg.target_doctype),
		order_by="modified desc",
		limit_page_length=0,
		ignore_permissions=True,
	)


@frappe.whitelist(methods=["POST"])
def update_ticket(doctype, name, values):
	reg = _space_reg(doctype=doctype)
	if not reg or not _is_ticket_reg(reg):
		frappe.throw(_("{0} is not a ticket DocType.").format(doctype))
	_require_ticket_access(doctype, name, "write", reg=reg)
	values = _loads(values, "values") or {}
	for protected in _SERVER_OWNED_TICKET_FIELDS:
		values.pop(protected, None)
	values = _clean_card_values(reg, values)
	doc = frappe.get_doc(doctype, name)
	doc.update(values)
	doc.save(ignore_permissions=True)
	_notify_card_changes(doc)
	frappe.db.commit()
	return _ticket_payload(doc)


# ---------------------------------------------------------------------------
# field + multi-select option management (from the UI, no Frappe Desk needed)
# ---------------------------------------------------------------------------
def _parse_options(options):
	"""Accept a JSON list, or comma-separated string -> clean, de-duped list."""
	if not options:
		return []
	if isinstance(options, str):
		try:
			options = json.loads(options)
		except Exception:
			options = options.split(",")
	out = [str(o).strip() for o in options if str(o).strip()]
	return list(dict.fromkeys(out))  # de-dupe, keep order


# label -> fieldtype (+ fixed options) for fields creatable from the UI
_FIELD_KINDS = {
	"multiselect": {"fieldtype": "Small Text"},
	"select": {"fieldtype": "Select"},
	"text": {"fieldtype": "Data"},
	"number": {"fieldtype": "Int"},
	"date": {"fieldtype": "Date"},
	"check": {"fieldtype": "Check"},
	"user": {"fieldtype": "Link", "options": "User"},
	"duration": {"fieldtype": "Duration"},
}

_RESERVED_FIELDS = {
	"name", "owner", "creation", "modified", "modified_by", "idx", "docstatus",
	"parent", "parentfield", "parenttype", "title", "bucket", "parent_task", "position",
}


def _protected_fields(reg):
	"""Fields that structural UI edits must not remove."""
	names = set(_RESERVED_FIELDS) | set(_SYSTEM_FIELDS)
	if _is_ticket_reg(reg):
		names |= _SERVER_OWNED_TICKET_FIELDS | {"requester"}
	for fieldname in (
		reg.title_field,
		reg.bucket_field,
		reg.assignee_field,
		reg.body_field,
		reg.parent_field,
		reg.get("badge_field"),
	):
		if fieldname:
			names.add(fieldname)
	return names


def _get_doctype_and_field(reg, fieldname):
	dt = frappe.get_doc("DocType", reg.target_doctype)
	df = next((f for f in dt.fields if f.fieldname == fieldname), None)
	if not df:
		frappe.throw(_("No field '{0}' on this space").format(fieldname))
	return dt, df


def _select_options_from_field(df):
	return [o.strip() for o in (df.options or "").split("\n") if o.strip()]


def _read_chip_state(reg):
	chip_fields = [c.strip() for c in (reg.chip_fields or "").split(",") if c.strip()]
	try:
		chip_options = json.loads(reg.chip_options) if reg.get("chip_options") else {}
	except Exception:
		chip_options = {}
	return chip_fields, chip_options


def _write_chip_state(reg, chip_fields, chip_options):
	reg.chip_fields = ",".join(dict.fromkeys([c for c in chip_fields if c]))
	reg.chip_options = json.dumps(chip_options or {})
	reg.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def set_chip_options(space, fieldname, options):
	_require_manager()
	"""Set the predefined option list for a multi-select (chip) field on a space.
	Stored as a JSON map on SP Space; surfaced via get_space -> chip_options."""
	reg = frappe.get_doc("SP Space", space)
	opts = _parse_options(options)
	try:
		current = json.loads(reg.chip_options) if reg.get("chip_options") else {}
	except Exception:
		current = {}
	current[fieldname] = opts
	reg.chip_options = json.dumps(current)
	reg.save(ignore_permissions=True)
	frappe.db.commit()
	return {"fieldname": fieldname, "options": opts}


@frappe.whitelist(methods=["POST"])
def update_field(
	space,
	fieldname,
	label=None,
	options=None,
	reqd=None,
	read_only=None,
	depends_on=None,
	mandatory_depends_on=None,
	read_only_depends_on=None,
):
	_require_manager()

	reg = frappe.get_doc("SP Space", space)
	dt, df = _get_doctype_and_field(reg, fieldname)

	if label is not None:
		label = (label or "").strip()
		if not label:
			frappe.throw(_("Field label is required"))
		df.label = label
	if reqd is not None:
		df.reqd = 1 if str(reqd).lower() in ("1", "true", "yes", "on") else 0
	if read_only is not None:
		df.read_only = 1 if str(read_only).lower() in ("1", "true", "yes", "on") else 0
	for prop, value in {
		"depends_on": depends_on,
		"mandatory_depends_on": mandatory_depends_on,
		"read_only_depends_on": read_only_depends_on,
	}.items():
		if value is not None:
			df.set(prop, (value or "").strip())

	opt_list = None
	chip_fields, chip_options = _read_chip_state(reg)
	if options is not None:
		opt_list = _parse_options(options)
		if fieldname in chip_fields:
			chip_options[fieldname] = opt_list
		elif df.fieldtype == "Select":
			df.options = "\n".join(opt_list)
		else:
			frappe.throw(_("Only Select and multi-select fields have editable options"))

	dt.save(ignore_permissions=True)
	if options is not None and fieldname in chip_fields:
		_write_chip_state(reg, chip_fields, chip_options)
	frappe.db.commit()
	frappe.clear_cache()
	return {
		"fieldname": fieldname,
		"label": df.label,
		"options": opt_list if opt_list is not None else (
			chip_options.get(fieldname, []) if fieldname in chip_fields else _select_options_from_field(df)
		),
	}


@frappe.whitelist(methods=["POST"])
def delete_field(space, fieldname):
	_require_manager()

	reg = frappe.get_doc("SP Space", space)
	if fieldname in _protected_fields(reg):
		frappe.throw(_("'{0}' is required by this space and cannot be deleted").format(fieldname))

	dt, df = _get_doctype_and_field(reg, fieldname)
	dt.remove(df)
	dt.save(ignore_permissions=True)

	chip_fields, chip_options = _read_chip_state(reg)
	if fieldname in chip_fields or fieldname in chip_options:
		chip_fields = [c for c in chip_fields if c != fieldname]
		chip_options.pop(fieldname, None)
		_write_chip_state(reg, chip_fields, chip_options)

	frappe.db.commit()
	frappe.clear_cache()
	return {"fieldname": fieldname}


@frappe.whitelist(methods=["POST"])
def reorder_fields(space, fieldnames):
	_require_manager()

	reg = frappe.get_doc("SP Space", space)
	wanted = _loads(fieldnames, "fieldnames") or []
	wanted = [str(f).strip() for f in wanted if str(f).strip()]
	if not wanted:
		frappe.throw(_("Field order is required"))

	dt = frappe.get_doc("DocType", reg.target_doctype)
	editable_names = [
		df.fieldname for df in dt.fields
		if df.fieldtype not in _LAYOUT_TYPES and df.fieldname not in _SYSTEM_FIELDS and not df.hidden
	]
	unknown = [f for f in wanted if f not in editable_names]
	if unknown:
		frappe.throw(_("Cannot reorder unknown field '{0}'").format(unknown[0]))

	ordered_visible = []
	for fieldname in wanted + editable_names:
		if fieldname in editable_names and fieldname not in ordered_visible:
			ordered_visible.append(fieldname)

	by_name = {df.fieldname: df for df in dt.fields}
	new_fields = []
	inserted = False
	for df in list(dt.fields):
		if df.fieldname in editable_names:
			if not inserted:
				new_fields.extend([by_name[name] for name in ordered_visible])
				inserted = True
			continue
		new_fields.append(df)
	if not inserted:
		new_fields.extend([by_name[name] for name in ordered_visible])

	dt.fields = new_fields
	for index, df in enumerate(dt.fields, start=1):
		df.idx = index
	dt.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache()
	return {"fieldnames": ordered_visible}


@frappe.whitelist(methods=["POST"])
def add_field(space, label, kind, options=None):
	_require_manager()
	"""Add a new field to a space's (custom) DocType from the UI.

	kind: multiselect | select | text | number | date | check | user
	options: choices for select/multiselect (JSON list or comma string).
	A `multiselect` field is created as Small Text + registered as a chip field
	with its options stored in chip_options.
	"""
	reg = frappe.get_doc("SP Space", space)
	doctype = reg.target_doctype

	label = (label or "").strip()
	if not label:
		frappe.throw(_("Field name is required"))
	if kind not in _FIELD_KINDS:
		frappe.throw(_("Unknown field type '{0}'").format(kind))

	fieldname = frappe.scrub(label)  # "Tech Debt" -> "tech_debt"
	if not fieldname:
		frappe.throw(_("Could not derive a field name from '{0}'").format(label))
	if fieldname in _RESERVED_FIELDS:
		frappe.throw(_("'{0}' is a reserved field name — pick another").format(fieldname))
	if any(df.fieldname == fieldname for df in frappe.get_meta(doctype).fields):
		frappe.throw(_("A field '{0}' already exists on this space").format(fieldname))

	opt_list = _parse_options(options)
	spec = _FIELD_KINDS[kind]
	new_field = {"fieldname": fieldname, "label": label, "fieldtype": spec["fieldtype"]}
	if spec.get("options"):
		new_field["options"] = spec["options"]
	if kind == "select":
		new_field["options"] = "\n".join(opt_list)
	if kind == "duration":
		# show hours + minutes only (hide days + seconds) — a task estimate
		new_field["hide_days"] = 1
		new_field["hide_seconds"] = 1
	if kind in ("text", "select", "multiselect", "number", "duration"):
		new_field["in_list_view"] = 1

	dt = frappe.get_doc("DocType", doctype)
	dt.append("fields", new_field)
	dt.save(ignore_permissions=True)

	if kind == "multiselect":
		chip_fields = [c.strip() for c in (reg.chip_fields or "").split(",") if c.strip()]
		if fieldname not in chip_fields:
			chip_fields.append(fieldname)
		reg.chip_fields = ",".join(chip_fields)
		try:
			current = json.loads(reg.chip_options) if reg.get("chip_options") else {}
		except Exception:
			current = {}
		current[fieldname] = opt_list
		reg.chip_options = json.dumps(current)
		reg.save(ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache()
	return {"fieldname": fieldname, "label": label, "kind": kind, "options": opt_list}


@frappe.whitelist(methods=["POST"])
def convert_to_multiselect(space, fieldname):
	_require_manager()
	"""Turn an existing Select field (defined natively in Frappe Desk) into a
	multi-select chip field, reusing its own options.

	A Frappe Select stores/validates a single value, so the field's type is
	flipped Select -> Small Text; its options become the predefined chip
	suggestions, and it's registered as a chip field. Existing single values
	survive as one chip.
	"""
	reg = frappe.get_doc("SP Space", space)
	doctype = reg.target_doctype
	dt = frappe.get_doc("DocType", doctype)
	df = next((f for f in dt.fields if f.fieldname == fieldname), None)
	if not df:
		frappe.throw(_("No field '{0}' on this space").format(fieldname))

	opt_list = []
	if df.fieldtype == "Select":
		opt_list = [o.strip() for o in (df.options or "").split("\n") if o.strip()]
		df.fieldtype = "Small Text"
		df.options = ""
		dt.save(ignore_permissions=True)
	elif df.fieldtype != "Small Text":
		frappe.throw(_("Only a Select (or Small Text) field can become multi-select"))

	chip_fields = [c.strip() for c in (reg.chip_fields or "").split(",") if c.strip()]
	if fieldname not in chip_fields:
		chip_fields.append(fieldname)
	reg.chip_fields = ",".join(chip_fields)
	try:
		current = json.loads(reg.chip_options) if reg.get("chip_options") else {}
	except Exception:
		current = {}
	if opt_list and not current.get(fieldname):
		current[fieldname] = opt_list
	reg.chip_options = json.dumps(current)
	reg.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache()
	return {"fieldname": fieldname, "options": current.get(fieldname, [])}


@frappe.whitelist(methods=["POST"])
def update_bucket(name, bucket_name=None, color=None, wip_limit=None, sort_order=None):
	_require_manager()
	"""Rename / recolour / set WIP / reorder a bucket."""
	doc = frappe.get_doc("SP Bucket", name)
	if bucket_name is not None:
		doc.bucket_name = bucket_name
	if color is not None:
		doc.color = color
	if wip_limit is not None:
		doc.wip_limit = wip_limit
	if sort_order is not None:
		doc.sort_order = sort_order
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "bucket_name": doc.bucket_name, "color": doc.color}


@frappe.whitelist(methods=["POST"])
def delete_bucket(name):
	_require_manager()
	"""Delete a bucket. Cards still linked to it fall into the unsorted lane."""
	frappe.delete_doc("SP Bucket", name, ignore_permissions=True)
	return {"deleted": name}


@frappe.whitelist(methods=["POST"])
def reorder_spaces(names):
	_require_manager()
	"""Persist the sidebar order of spaces."""
	if isinstance(names, str):
		names = _loads(names, "names")
	for i, n in enumerate(names):
		frappe.db.set_value("SP Space", n, "sort_order", i, update_modified=False)
	frappe.db.commit()
	frappe.publish_realtime(
		"list_update",
		{"doctype": "SP Space", "user": frappe.session.user},
		doctype="SP Space",
		after_commit=True,
	)
	return {"ok": True, "count": len(names)}


@frappe.whitelist(methods=["POST"])
def reorder_buckets(names):
	_require_manager()
	"""Persist a new left-to-right column order."""
	if isinstance(names, str):
		names = _loads(names, "names")
	for i, n in enumerate(names):
		frappe.db.set_value("SP Bucket", n, "sort_order", i, update_modified=False)
	frappe.db.commit()
	frappe.publish_realtime(
		"list_update",
		{"doctype": "SP Bucket", "user": frappe.session.user},
		doctype="SP Bucket",
		after_commit=True,
	)
	return {"ok": True, "count": len(names)}


@frappe.whitelist(methods=["POST"])
def bulk_set(doctype, names, values):
	"""Apply a set of field values to many cards at once (bulk actions)."""
	names = _loads(names, "names") or []
	values = _loads(values, "values") or {}
	reg = _space_reg(doctype=doctype)
	ticket = bool(reg and _is_ticket_reg(reg))
	if ticket and _SERVER_OWNED_TICKET_FIELDS.intersection(values):
		frappe.throw(_("One or more fields are managed by the server."))
	if not ticket:
		_require_space_access(reg=reg, doctype=doctype, mode="write")
	if reg:
		values = _clean_card_values(reg, values)
	for n in names:
		if ticket:
			_require_ticket_access(doctype, n, "write", reg=reg)
		doc = frappe.get_doc(doctype, n)
		doc.update(values)
		doc.save(ignore_permissions=True)
		_notify_card_changes(doc, reg=reg)
	frappe.db.commit()
	return {"updated": len(names)}


@frappe.whitelist(methods=["POST"])
def bulk_delete(doctype, names):
	"""Delete many cards at once."""
	names = _loads(names, "names") or []
	reg = _space_reg(doctype=doctype)
	ticket = bool(reg and _is_ticket_reg(reg))
	if not ticket:
		_require_space_access(reg=reg, doctype=doctype, mode="write")
	for n in names:
		if ticket:
			_require_ticket_access(doctype, n, "write", reg=reg)
		frappe.delete_doc(doctype, n, ignore_permissions=True)
	frappe.db.commit()
	return {"deleted": len(names)}


@frappe.whitelist(methods=["POST"])
def add_bucket(space, bucket_name, color=None):
	_require_manager()
	"""Create a new bucket (column) for a space from the UI."""
	last = frappe.db.sql(
		"select max(sort_order) from `tabSP Bucket` where space=%s", space
	)[0][0]
	doc = frappe.get_doc({
		"doctype": "SP Bucket",
		"space": space,
		"bucket_name": bucket_name,
		"color": color or "#9ca3af",
		"sort_order": (last or 0) + 1,
	}).insert(ignore_permissions=True)
	return {"name": doc.name, "bucket_name": doc.bucket_name, "color": doc.color,
	        "sort_order": doc.sort_order}


# ---------------------------------------------------------------------------
# saved views
# ---------------------------------------------------------------------------
def _view_dict(v):
	return {
		"name": v.name,
		"view_name": v.view_name,
		"view_type": v.view_type,
		"icon": v.icon,
		"group_by": v.group_by,
		"sort_field": v.sort_field,
		"sort_dir": v.sort_dir,
		"me_mode": v.me_mode,
		"is_shared": v.is_shared,
		"filters": json.loads(v.filters_json) if v.filters_json else [],
		"owner": v.owner,
	}


@frappe.whitelist()
def get_views(space):
	"""Saved views for a space: shared ones + the current user's private ones."""
	_require_space_access(space=space, mode="read")
	user = frappe.session.user
	views = frappe.get_all(
		"SP View",
		filters={"space": space},
		or_filters=[["is_shared", "=", 1], ["owner", "=", user]],
		fields=["name", "view_name", "view_type", "icon", "group_by", "sort_field",
		        "sort_dir", "me_mode", "is_shared", "filters_json", "owner"],
		order_by="creation asc",
	)
	for v in views:
		v["filters"] = json.loads(v.pop("filters_json")) if v.get("filters_json") else []
	return views


@frappe.whitelist(methods=["POST"])
def save_view(space, view_name, view_type="List", group_by=None, sort_field=None,
              sort_dir="asc", me_mode=0, is_shared=1, filters=None, name=None, icon=None):
	"""Create or update a saved view."""
	_require_space_access(space=space, mode="write")
	if isinstance(filters, str):
		filters = _loads(filters, "filters") or []
	values = {
		"space": space,
		"view_name": view_name,
		"view_type": view_type,
		"icon": icon,
		"group_by": group_by,
		"sort_field": sort_field,
		"sort_dir": sort_dir,
		"me_mode": int(me_mode or 0),
		"is_shared": int(is_shared or 0),
		"filters_json": json.dumps(filters or []),
	}
	if name and frappe.db.exists("SP View", name):
		doc = frappe.get_doc("SP View", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "SP View", **values}).insert(ignore_permissions=True)
	return _view_dict(doc)


@frappe.whitelist(methods=["POST"])
def delete_view(name):
	space = frappe.db.get_value("SP View", name, "space")
	_require_space_access(space=space, mode="write")
	frappe.delete_doc("SP View", name, ignore_permissions=True)
	return {"deleted": name}


# ---------------------------------------------------------------------------
# activity feed (audit trail + comments) — built on Frappe's Version + Comment
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_activity(doctype, name, limit=100):
	"""Merged, chronological feed: creation + field-change audit + comments.
	Returns the most recent `limit` entries (chronological order)."""
	_require_ticket_access(doctype, name, "read")
	meta = frappe.get_meta(doctype)
	labels = {df.fieldname: (df.label or df.fieldname) for df in meta.fields}
	ftypes = {df.fieldname: df.fieldtype for df in meta.fields}
	# rich/long text diffs are noise in an activity feed — don't audit them
	noisy = {"Text Editor", "Long Text", "Code", "Markdown Editor", "HTML Editor", "Text", "HTML"}

	# resolve bucket-link hashes -> readable names for nicer audit lines
	reg = _space_reg(doctype=doctype)
	bucket_field = reg.bucket_field if reg else None
	bucket_names = {}
	if bucket_field and reg:
		for b in frappe.get_all("SP Bucket", filters={"space": reg.name},
		                        fields=["name", "bucket_name"]):
			bucket_names[b.name] = b.bucket_name

	def fmt(field, value):
		if value in (None, ""):
			return None
		if field == bucket_field and value in bucket_names:
			return bucket_names[value]
		return value

	items = []

	created = frappe.db.get_value(doctype, name, ["owner", "creation"], as_dict=True)
	if created:
		items.append({"type": "created", "user": created.owner, "time": str(created.creation)})

	limit = frappe.utils.cint(limit) or 100
	for c in frappe.get_all(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
		fields=["name", "content", "owner", "comment_by", "creation"],
		order_by="creation desc",
		limit_page_length=limit,
	):
		items.append({
			"type": "comment", "name": c.name, "content": c.content,
			"user": c.comment_by or c.owner, "time": str(c.creation),
		})

	for v in frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": name},
		fields=["data", "owner", "creation"],
		order_by="creation desc",
		limit_page_length=limit,
	):
		try:
			data = json.loads(v.data or "{}")
		except Exception:
			continue
		for ch in data.get("changed", []):
			if len(ch) < 3:
				continue
			field, old, new = ch[0], ch[1], ch[2]
			if field in ("modified", "modified_by"):
				continue
			if ftypes.get(field) in noisy:
				continue
			items.append({
				"type": "change", "user": v.owner, "time": str(v.creation),
				"field": labels.get(field, field),
				"old": fmt(field, old), "new": fmt(field, new),
			})

	items.sort(key=lambda x: x["time"])
	return items[-limit:] if len(items) > limit else items


# ---------------------------------------------------------------------------
# attachments — built on Frappe's File doctype (uploads + external links)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_attachments(doctype, name):
	"""Files attached to a card: uploaded files + external links (Google Docs…)."""
	_require_ticket_access(doctype, name, "read")
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name},
		fields=["name", "file_name", "file_url", "is_private", "file_size", "creation", "owner"],
		order_by="creation desc",
	)


@frappe.whitelist(methods=["POST"])
def add_file_link(doctype, name, url, label=None):
	"""Attach an external link (Google Doc/Sheet, etc.) as a File record."""
	_require_ticket_access(doctype, name, "write")
	url = (url or "").strip()
	if not url:
		frappe.throw(_("A URL is required"))
	f = frappe.get_doc({
		"doctype": "File",
		"file_url": url,
		"file_name": (label or "").strip() or url,
		"attached_to_doctype": doctype,
		"attached_to_name": name,
		"is_private": 0,
	}).insert(ignore_permissions=True)
	return {"name": f.name, "file_name": f.file_name, "file_url": f.file_url}


@frappe.whitelist(methods=["POST"])
def remove_attachment(file_name):
	"""Detach + delete a File from a card."""
	f = frappe.db.get_value("File", file_name, ["attached_to_doctype", "attached_to_name"], as_dict=True)
	if not f:
		return {"deleted": file_name}
	if f.attached_to_doctype:
		_require_ticket_access(f.attached_to_doctype, f.attached_to_name, "write")
	frappe.delete_doc("File", file_name, ignore_permissions=True)
	return {"deleted": file_name}


@frappe.whitelist(methods=["POST"])
def add_comment(doctype, name, content, mentions=None):
	"""Add a user comment using Frappe's Comment infrastructure, and notify any
	@mentioned users (mentions = JSON list of user ids)."""
	_require_ticket_access(doctype, name, "write")
	doc = frappe.get_doc(doctype, name)
	c = doc.add_comment("Comment", content)

	users = _loads(mentions, "mentions") or []
	if users:
		_notify_mentions(doctype, name, content, users)

	# watchers hear about new comments too (mentioned users already notified)
	watchers = _card_watchers(doctype, name, exclude=set(users) | {frappe.session.user})
	if watchers:
		author_name = frappe.utils.get_fullname(frappe.session.user)
		_notify(
			watchers,
			_("{0} commented on “{1}”").format(author_name, _card_title(doctype, name)),
			doctype, name, content=(content or "")[:140], ntype="Alert",
		)

	from sprint.automation import dispatch_comment_event
	dispatch_comment_event(doctype, name, content)

	return {"name": c.name, "content": c.content, "user": c.comment_by or c.owner,
	        "time": str(c.creation)}


def _card_title(doctype, name):
	tf = frappe.db.get_value("SP Space", {"target_doctype": doctype}, "title_field") or "title"
	try:
		return frappe.db.get_value(doctype, name, tf) or name
	except Exception:
		return name


def _notify(users, subject, doctype, name, content="", ntype="Mention"):
	"""Persist a Notification Log (shows in the bell / Sprint inbox; Frappe
	also emails it if the site has outgoing mail and the user's Notification
	Settings allow) and push the sprint_notification realtime event (toast +
	live inbox badge) for each user, except the actor."""
	author = frappe.session.user
	author_name = frappe.utils.get_fullname(author)
	title = _card_title(doctype, name)
	for u in {x for x in users if x and x != author}:
		if not frappe.db.exists("User", u):
			continue
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": u,
				"from_user": author,
				"type": ntype,
				"document_type": doctype,
				"document_name": name,
				"subject": subject,
				"email_content": content,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.clear_last_message()
		frappe.publish_realtime(
			"sprint_notification",
			{"doctype": doctype, "name": name, "title": title, "ntype": ntype,
			 "from_name": author_name, "content": content, "subject": subject},
			user=u,
			after_commit=True,
		)


def _notify_mentions(doctype, name, content, users):
	author_name = frappe.utils.get_fullname(frappe.session.user)
	subject = _("{0} mentioned you in “{1}”").format(author_name, _card_title(doctype, name))
	_notify(users, subject, doctype, name, content=(content or "")[:140], ntype="Mention")


def _notify_card_changes(doc, reg=None, is_new=False):
	"""In-app notifications for meaningful card changes. Called after the ORM
	save inside Sprint's own mutation endpoints — edits made directly in Desk
	or by Server Scripts don't pass through here (a wildcard doc_events hook
	is the future upgrade if that ever matters)."""
	reg = reg or _space_reg(doctype=doc.doctype)
	if not reg:
		return
	actor = frappe.session.user
	actor_name = frappe.utils.get_fullname(actor)
	title = doc.get(reg.title_field or "title") or doc.name
	before = None if is_new else doc.get_doc_before_save()

	# assignee changed -> tell the new assignee
	assignee_field = reg.get("assignee_field")
	if assignee_field:
		new_assignee = doc.get(assignee_field)
		old_assignee = before.get(assignee_field) if before else None
		if new_assignee and new_assignee != old_assignee:
			noun = "ticket" if _is_ticket_reg(reg) else "task"
			_notify(
				[new_assignee],
				_("{0} assigned the {1} “{2}” to you").format(actor_name, noun, title),
				doc.doctype, doc.name, ntype="Assignment",
			)

	# ticket: the requester follows bucket (status) movement
	bucket_field = reg.bucket_field or "bucket"
	bucket_changed = before is not None and doc.get(bucket_field) != before.get(bucket_field)
	bucket_name = None
	if bucket_changed:
		new_bucket = doc.get(bucket_field)
		bucket_name = (
			frappe.db.get_value("SP Bucket", new_bucket, "bucket_name")
			if new_bucket else None
		) or "—"
	if _is_ticket_reg(reg) and bucket_changed:
		requester = doc.get("requester")
		if requester and requester != actor:
			_notify(
				[requester],
				_("Your ticket “{0}” moved to {1}").format(title, bucket_name),
				doc.doctype, doc.name, ntype="Alert",
			)

	# watchers follow bucket + assignee movement
	if before is not None:
		changes = []
		if bucket_changed:
			changes.append(_("moved to {0}").format(bucket_name))
		if assignee_field and doc.get(assignee_field) != before.get(assignee_field):
			new_a = doc.get(assignee_field)
			changes.append(_("assigned to {0}").format(
				frappe.utils.get_fullname(new_a) if new_a else "—"
			))
		if changes:
			exclude = {actor}
			if assignee_field and doc.get(assignee_field):
				exclude.add(doc.get(assignee_field))
			if _is_ticket_reg(reg) and doc.get("requester"):
				exclude.add(doc.get("requester"))
			watchers = _card_watchers(doc.doctype, doc.name, exclude=exclude)
			if watchers:
				_notify(
					watchers,
					_("“{0}” {1}").format(title, " · ".join(changes)),
					doc.doctype, doc.name, ntype="Alert",
				)

	# automations: same dispatch point, same documented trade-off (Desk /
	# Server-Script / import edits bypass the mutation funnel and won't fire).
	# Automation-made saves re-enter here, so cascades work under the depth guard.
	from sprint.automation import dispatch_card_event
	dispatch_card_event(doc, reg=reg, is_new=is_new)


# ---------------------------------------------------------------------------
# Home: my cards across spaces + notification inbox
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_my_cards(include_closed=0):
	"""Every card assigned to the current user across all readable spaces.
	Powers the Home page; grouping by due date happens client-side."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	include_closed = frappe.utils.cint(include_closed)
	has_is_closed = frappe.db.has_column("SP Bucket", "is_closed")
	out = []
	for name in frappe.get_all("SP Space", pluck="name", order_by="sort_order asc, label asc"):
		reg = frappe.get_doc("SP Space", name)
		assignee_field = reg.get("assignee_field")
		# no assignee pointer -> the space can't have "my" cards;
		# can_access_space is the same read guard get_spaces uses
		if not assignee_field or not can_access_space(reg, "read", user=user):
			continue
		doctype = reg.target_doctype
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if not meta.has_field(assignee_field):
			continue

		title_field = reg.title_field or "title"
		bucket_field = reg.bucket_field or "bucket"
		badge_field = reg.get("badge_field") or "sprint_points"
		due_field = reg.get("due_field")
		fields = ["name", "modified"] + [
			f for f in (title_field, bucket_field, badge_field, due_field)
			if f and meta.has_field(f)
		]

		filters = {assignee_field: user}
		if _is_ticket_reg(reg):
			filters.update(ticket_query_filter(user))
		if not include_closed and has_is_closed and meta.has_field(bucket_field):
			closed = frappe.get_all(
				"SP Bucket", filters={"space": reg.name, "is_closed": 1}, pluck="name"
			)
			if closed:
				filters[bucket_field] = ["not in", closed]

		rows = frappe.get_all(
			doctype,
			filters=filters,
			fields=list(dict.fromkeys(fields)),
			order_by="modified desc",
			limit_page_length=0,
			ignore_permissions=True,
		)
		if not rows:
			continue
		buckets = {
			b.name: b
			for b in frappe.get_all(
				"SP Bucket", filters={"space": reg.name}, fields=["name", "bucket_name", "color"]
			)
		}
		for r in rows:
			b = buckets.get(r.get(bucket_field))
			out.append({
				"space": reg.name,
				"space_label": reg.label,
				"space_icon": reg.icon,
				"space_color": reg.color,
				"space_type": reg.get("space_type") or "Task",
				"name": r.name,
				"title": r.get(title_field) or r.name,
				"bucket": r.get(bucket_field),
				"bucket_name": b.bucket_name if b else None,
				"bucket_color": b.color if b else None,
				"due_date": r.get(due_field) if due_field else None,
				"badge": r.get(badge_field),
				"modified": r.modified,
			})
	return out


def _sprint_doctype_map():
	return {
		s.target_doctype: s
		for s in frappe.get_all(
			"SP Space", fields=["name", "target_doctype", "space_type", "label", "icon"]
		)
	}


@frappe.whitelist()
def get_notifications(limit=50):
	"""Inbox: this user's Sprint notifications (mentions/assignments/alerts)."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	dt_map = _sprint_doctype_map()
	if not dt_map:
		return []
	rows = frappe.get_all(
		"Notification Log",
		filters={"for_user": user, "document_type": ["in", list(dt_map)]},
		fields=["name", "subject", "type", "document_type", "document_name",
		        "from_user", "read", "creation"],
		order_by="creation desc",
		limit_page_length=min(frappe.utils.cint(limit) or 50, 200),
		ignore_permissions=True,
	)
	for r in rows:
		s = dt_map.get(r.document_type)
		r["space"] = s.name if s else None
		r["space_type"] = (s.space_type or "Task") if s else "Task"
		r["space_label"] = s.label if s else None
		r["space_icon"] = s.icon if s else None
		r["from_name"] = frappe.utils.get_fullname(r.from_user) if r.from_user else ""
	return rows


@frappe.whitelist()
def get_unread_notification_count():
	user = frappe.session.user
	if user == "Guest":
		return 0
	doctypes = list(_sprint_doctype_map())
	if not doctypes:
		return 0
	return frappe.db.count(
		"Notification Log",
		{"for_user": user, "read": 0, "document_type": ["in", doctypes]},
	)


@frappe.whitelist(methods=["POST"])
def mark_notification_read(name):
	row = frappe.db.get_value("Notification Log", name, ["for_user", "read"], as_dict=True)
	if not row:
		return {"ok": True}
	if row.for_user != frappe.session.user:
		frappe.throw(_("Not your notification."), frappe.PermissionError)
	if not row.read:
		frappe.db.set_value("Notification Log", name, "read", 1, update_modified=False)
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
def mark_all_notifications_read():
	user = frappe.session.user
	doctypes = list(_sprint_doctype_map())
	if user == "Guest" or not doctypes:
		return {"ok": True}
	frappe.db.sql(
		"""update `tabNotification Log` set `read`=1
		   where for_user=%s and ifnull(`read`, 0)=0 and document_type in %s""",
		(user, tuple(doctypes)),
	)
	frappe.db.commit()
	return {"ok": True}


# ---------------------------------------------------------------------------
# watchers — per-card subscriptions (SP Watcher)
# ---------------------------------------------------------------------------
def _card_watchers(doctype, name, exclude=None):
	if not frappe.db.exists("DocType", "SP Watcher"):
		return []
	exclude = set(exclude or ())
	users = frappe.get_all(
		"SP Watcher", filters={"ref_doctype": doctype, "ref_name": name}, pluck="user"
	)
	return [u for u in users if u and u not in exclude]


def _require_card_access(doctype, name, mode="read"):
	if is_ticket_space(doctype=doctype):
		_require_ticket_access(doctype, name, mode)
	else:
		_require_space_access(doctype=doctype, mode=mode)


@frappe.whitelist()
def get_watch(doctype, name):
	"""Who watches this card, and whether the current user does."""
	_require_card_access(doctype, name, "read")
	watchers = _card_watchers(doctype, name)
	return {"watchers": watchers, "watching": frappe.session.user in watchers}


@frappe.whitelist(methods=["POST"])
def toggle_watch(doctype, name):
	"""Follow / unfollow a card. Watchers are notified on status or assignee
	changes and on new comments. Read access is enough to watch."""
	_require_card_access(doctype, name, "read")
	user = frappe.session.user
	existing = frappe.db.get_value(
		"SP Watcher", {"ref_doctype": doctype, "ref_name": name, "user": user}
	)
	if existing:
		frappe.delete_doc("SP Watcher", existing, ignore_permissions=True, force=1)
		watching = False
	else:
		frappe.get_doc({
			"doctype": "SP Watcher",
			"ref_doctype": doctype,
			"ref_name": name,
			"user": user,
		}).insert(ignore_permissions=True)
		watching = True
	frappe.db.commit()
	return {"watching": watching, "watchers": _card_watchers(doctype, name)}


# ---------------------------------------------------------------------------
# card templates (SP Template) — {field: value} presets for new cards
# ---------------------------------------------------------------------------
_TEMPLATE_EXCLUDED_FIELDS = {
	"doctype", "name", "owner", "creation", "modified", "modified_by",
	"docstatus", "idx", "position", "requester", "_assign",
}


@frappe.whitelist()
def get_templates(space):
	_require_space_access(space=space, mode="read")
	if not frappe.db.exists("DocType", "SP Template"):
		return []
	rows = frappe.get_all(
		"SP Template",
		filters={"space": space},
		fields=["name", "template_name", "values_json"],
		order_by="sort_order asc, template_name asc",
	)
	for r in rows:
		try:
			r["values"] = json.loads(r.pop("values_json") or "{}")
		except Exception:
			r["values"] = {}
	return rows


@frappe.whitelist(methods=["POST"])
def save_template(space, template_name, values, name=None):
	_require_manager()
	_require_space_access(space=space, mode="write")
	template_name = (template_name or "").strip()
	if not template_name:
		frappe.throw(_("Template name is required"))
	values = _loads(values, "values") or {}
	values = {
		k: v for k, v in values.items()
		if k not in _TEMPLATE_EXCLUDED_FIELDS and v not in (None, "")
	}
	if name and frappe.db.exists("SP Template", name):
		doc = frappe.get_doc("SP Template", name)
		doc.template_name = template_name
		doc.values_json = json.dumps(values)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({
			"doctype": "SP Template",
			"space": space,
			"template_name": template_name,
			"values_json": json.dumps(values),
		}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "template_name": doc.template_name}


@frappe.whitelist(methods=["POST"])
def delete_template(name):
	_require_manager()
	frappe.delete_doc("SP Template", name, ignore_permissions=True)
	frappe.db.commit()
	return {"deleted": name}


# ---------------------------------------------------------------------------
# data import / export (Excel) — meta-driven, with subtask Ref resolution
# ---------------------------------------------------------------------------
# fieldtypes we never round-trip through a spreadsheet cell
_NON_EXPORTABLE = _LAYOUT_TYPES | {"Table", "Table MultiSelect", "Signature", "Geolocation"}


def _read_xlsx(file_url):
	from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
	rows = read_xlsx_file_from_attached_file(file_url=file_url)
	return rows or []


def _export_fields(meta, reg):
	"""Card fields worth exporting (parent handled separately via Parent Ref)."""
	parent_field = reg.parent_field or "parent_task"
	out = []
	for df in meta.fields:
		if df.fieldtype in _NON_EXPORTABLE or df.fieldname in _SYSTEM_FIELDS or df.hidden:
			continue
		if df.fieldname == parent_field:
			continue
		out.append(df)
	return out


@frappe.whitelist()
def export_space(space):
	_require_manager()
	"""Stream an .xlsx of a space's cards. Columns: Ref (name), Parent Ref
	(parent name), then each field by label. Buckets export as their name,
	multi-select as comma strings — so the sheet round-trips through import."""
	reg = frappe.get_doc("SP Space", space)
	doctype = reg.target_doctype
	from frappe.utils.xlsxutils import make_xlsx

	meta = frappe.get_meta(doctype)
	parent_field = reg.parent_field or "parent_task"
	bucket_field = reg.bucket_field or "bucket"
	fields = _export_fields(meta, reg)
	bucket_names = {
		b.name: b.bucket_name
		for b in frappe.get_all("SP Bucket", filters={"space": space}, fields=["name", "bucket_name"])
	}

	wanted = list(dict.fromkeys(["name", parent_field] + [df.fieldname for df in fields]))
	records = frappe.get_all(doctype, fields=wanted, order_by="creation asc", limit_page_length=0)

	header = ["Ref", "Parent Ref"] + [(df.label or df.fieldname) for df in fields]
	data = [header]
	for r in records:
		line = [r.get("name"), r.get(parent_field) or ""]
		for df in fields:
			v = r.get(df.fieldname)
			if df.fieldname == bucket_field and v in bucket_names:
				v = bucket_names[v]
			line.append("" if v is None else v)
		data.append(line)

	xlsx = make_xlsx(data, "Export")
	frappe.response["filename"] = f"{(reg.label or doctype)}.xlsx"
	frappe.response["filecontent"] = xlsx.getvalue()
	frappe.response["type"] = "binary"


@frappe.whitelist()
def import_preview(space, file_url):
	_require_manager()
	"""Read an uploaded .xlsx: return headers, a sample, and a suggested
	header -> field mapping (matched by label/fieldname; Ref/Parent Ref by name)."""
	reg = frappe.get_doc("SP Space", space)
	doctype = reg.target_doctype

	rows = _read_xlsx(file_url)
	if not rows:
		frappe.throw(_("The file is empty."))
	headers = [str(h).strip() if h is not None else "" for h in rows[0]]

	meta = frappe.get_meta(doctype)
	by_label = {(df.label or "").strip().lower(): df.fieldname for df in meta.fields if df.fieldname}
	by_name = {df.fieldname.lower(): df.fieldname for df in meta.fields}
	suggested = {}
	for h in headers:
		hl = h.strip().lower()
		if hl == "ref":
			suggested[h] = "__ref__"
		elif hl in ("parent ref", "parent", "parent task", "parent_ref"):
			suggested[h] = "__parent_ref__"
		elif hl in by_label:
			suggested[h] = by_label[hl]
		elif hl.replace(" ", "_") in by_name:
			suggested[h] = by_name[hl.replace(" ", "_")]
		else:
			suggested[h] = ""

	sample = [["" if c is None else str(c) for c in r] for r in rows[1:6]]
	return {"headers": headers, "sample": sample, "rows": len(rows) - 1, "suggested": suggested}


@frappe.whitelist(methods=["POST"])
def import_commit(space, file_url, mapping, update_key=None):
	_require_manager()
	"""Insert (or update) cards from an .xlsx through the ORM, so validations,
	Server Scripts and audit all fire. Subtasks are wired in a second pass via
	the Ref / Parent Ref columns. Returns {created, updated, errors[]}."""
	reg = frappe.get_doc("SP Space", space)
	doctype = reg.target_doctype
	mapping = _loads(mapping, "mapping")

	parent_field = reg.parent_field or "parent_task"
	bucket_field = reg.bucket_field or "bucket"
	meta = frappe.get_meta(doctype)
	valid = {df.fieldname for df in meta.fields}
	bucket_by_name = {
		(b.bucket_name or "").strip().lower(): b.name
		for b in frappe.get_all("SP Bucket", filters={"space": space}, fields=["name", "bucket_name"])
	}
	bucket_ids = {b.name for b in frappe.get_all("SP Bucket", filters={"space": space}, fields=["name"])}

	rows = _read_xlsx(file_url)
	headers = [str(h).strip() if h is not None else "" for h in rows[0]]
	ref_idx = parent_ref_idx = None
	field_cols = []
	for i, h in enumerate(headers):
		tgt = mapping.get(h, "")
		if tgt == "__ref__":
			ref_idx = i
		elif tgt == "__parent_ref__":
			parent_ref_idx = i
		elif tgt and tgt in valid:
			field_cols.append((i, tgt))

	def cell(row, idx):
		if idx is None or idx >= len(row):
			return None
		v = row[idx]
		return None if v in (None, "") else v

	created = updated = 0
	errors = []
	ref_to_name = {}
	pending = []  # (name, parent_ref)

	for rno, row in enumerate(rows[1:], start=2):
		try:
			values = {}
			for idx, fn in field_cols:
				v = cell(row, idx)
				if v is None:
					continue
				if fn == bucket_field:
					sv = str(v).strip()
					if sv not in bucket_ids and sv.lower() in bucket_by_name:
						v = bucket_by_name[sv.lower()]
				values[fn] = v
			if not values:
				continue

			existing = None
			if update_key and update_key in valid and values.get(update_key):
				existing = frappe.db.get_value(doctype, {update_key: values[update_key]}, "name")

			if existing:
				doc = frappe.get_doc(doctype, existing)
				doc.update(values)
				doc.save(ignore_permissions=True)
				updated += 1
			else:
				doc = frappe.get_doc({"doctype": doctype, **values})
				doc.insert(ignore_permissions=True)
				created += 1

			ref_val = cell(row, ref_idx)
			if ref_val is not None:
				ref_to_name[str(ref_val).strip()] = doc.name
			parent_ref_val = cell(row, parent_ref_idx)
			if parent_ref_val is not None:
				pending.append((doc.name, str(parent_ref_val).strip()))
		except Exception as e:
			errors.append({"row": rno, "error": str(e)})

	for name, pref in pending:
		target = ref_to_name.get(pref)
		if not target:
			errors.append({"row": "link", "error": _("Row {0}: parent ref '{1}' not found").format(name, pref)})
			continue
		try:
			d = frappe.get_doc(doctype, name)
			d.set(parent_field, target)
			d.save(ignore_permissions=True)
		except Exception as e:
			errors.append({"row": "link", "error": f"{name}: {e}"})

	frappe.db.commit()
	return {"created": created, "updated": updated, "errors": errors}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=60)
def verify_password(password):
	"""Re-authenticate the current user (used to gate destructive admin actions).
	Rate-limited to 5 attempts/minute so it can't be used as a password oracle.

	Returns True on a correct password, False otherwise. Never reveals anything
	beyond the boolean.
	"""
	from frappe.utils.password import check_password

	try:
		check_password(frappe.session.user, password or "")
		return True
	except frappe.AuthenticationError:
		return False


@frappe.whitelist(methods=["POST"])
def delete_space(space):
	"""Administrator-only: delete a space entirely (buckets, registry, DocType,
	and all its cards). Irreversible — the UI gates this behind a password."""
	_require_manager()
	from sprint.setup import delete_space as _delete_space

	_delete_space(space)
	return {"deleted": space}


# ==========================================================================
# Auth, onboarding + user administration
# --------------------------------------------------------------------------
# Brings login/logout, password recovery and user management into the SPA so
# operators never touch Frappe Desk (B2B SaaS). Login/logout themselves use
# Frappe's built-in /api/method/login + /api/method/logout; the endpoints below
# cover boot-refresh, password recovery, manager-gated user administration and
# self-service account settings. Every admin endpoint is guarded by
# _require_manager() (Administrator OR the "Sprint Manager" role).
# ==========================================================================

MANAGER_ROLE = "Sprint Manager"


def _to_app_reset_url(link):
	"""Rewrite Frappe's absolute /update-password link to the in-app SPA route,
	so a copied invite/reset link lands on Sprint's own page, never Desk."""
	query = link.split("?", 1)[1] if "?" in link else ""
	return f"/sprint/update-password?{query}"


@frappe.whitelist(allow_guest=True)
def boot():
	"""SPA boot vars (user, csrf_token, can_manage, timezone…). The frontend
	re-fetches this right after login/logout so window.* and the CSRF token
	match the new session. Safe for guests — returns the guest boot."""
	from sprint.www.sprint import get_boot

	return get_boot()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def request_password_reset(email):
	"""Send a password-reset email. Delegates to Frappe's own reset flow, which
	is deliberately enumeration-safe (identical response whether or not the email
	exists, and self-rate-limited). We swallow its msgprint and return a plain ok
	so the SPA shows its own generic confirmation."""
	from frappe.core.doctype.user.user import reset_password

	reset_password(user=(email or "").strip())
	frappe.clear_messages()
	return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60)
def set_password_with_key(key, new_password):
	"""Set a password from a reset/invite key (the link in the welcome or
	forgot-password email, or a copied invite link). Wraps Frappe's key-validated
	update so the landing page stays inside the SPA. On success Frappe logs the
	user in; the caller then refreshes boot()."""
	from frappe.core.doctype.user.user import update_password

	if not key or not new_password:
		frappe.throw(_("A reset link and a new password are required."))
	update_password(new_password=new_password, key=key)
	# update_password sets a 410 status + returns a message (no exception) when
	# the key is invalid/expired — turn that into a clean error for the SPA.
	if frappe.local.response.get("http_status_code") == 410:
		frappe.local.response.http_status_code = None
		frappe.clear_messages()
		frappe.throw(_("This link has expired or is invalid. Please request a new one."))
	frappe.clear_messages()
	return {"ok": True, "user": frappe.session.user}


# ---- user administration (manager-gated) --------------------------------
@frappe.whitelist()
def list_users():
	"""Directory of real users for the admin page: enabled state, manager-role
	flag, the site's `manager` field (when present) and last login."""
	_require_manager()
	meta = frappe.get_meta("User")
	fields = ["name", "full_name", "enabled", "user_image", "last_login"]
	if meta.has_field("manager"):
		fields.append("manager")
	rows = frappe.get_all(
		"User",
		filters={"name": ["not in", ["Guest"]]},
		fields=fields,
		order_by="enabled desc, full_name asc",
		limit_page_length=0,
	)
	managers = set(
		frappe.get_all(
			"Has Role",
			filters={"role": MANAGER_ROLE, "parenttype": "User"},
			pluck="parent",
		)
	)
	for r in rows:
		r["enabled"] = bool(r.get("enabled"))
		r["is_manager"] = r["name"] in managers
		r["is_admin"] = r["name"] == "Administrator"
	return rows


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60)
def invite_user(email, full_name=None, manager=None, make_manager=0, send_email=1):
	"""Create a user and hand back a copyable in-app set-password link (and email
	it when mail is configured). Honours the site's mandatory `manager` field."""
	_require_manager()
	email = (email or "").strip().lower()
	if not email or "@" not in email:
		frappe.throw(_("A valid email address is required."))
	if frappe.db.exists("User", email):
		frappe.throw(_("A user with this email already exists."))

	full_name = (full_name or "").strip() or email.split("@")[0]
	parts = full_name.split(" ", 1)

	doc = frappe.new_doc("User")
	doc.email = email
	doc.first_name = parts[0]
	if len(parts) > 1:
		doc.last_name = parts[1]
	doc.enabled = 1
	doc.user_type = "System User"
	doc.send_welcome_email = 0  # we send our own link so the email + copy link share one key

	mf = frappe.get_meta("User").get_field("manager")
	if mf:
		mgr = (manager or "").strip()
		if not mgr and mf.reqd:
			frappe.throw(_("A manager is required for new users on this site."))
		if mgr:
			if not frappe.db.exists("User", mgr):
				frappe.throw(_("Manager '{0}' does not exist.").format(mgr))
			doc.manager = mgr

	doc.insert(ignore_permissions=True)
	if cint(make_manager):
		doc.add_roles(MANAGER_ROLE)

	link = doc._reset_password(send_email=False)  # one key, shared by email + copy link
	email_sent = False
	if cint(send_email):
		try:
			doc.password_reset_mail(link)
			email_sent = True
		except Exception:
			frappe.clear_messages()  # mail not configured — the copy link still works
	frappe.db.commit()
	return {"user": doc.name, "invite_url": _to_app_reset_url(link), "email_sent": email_sent}


@frappe.whitelist(methods=["POST"])
def set_user_role(user, is_manager):
	"""Grant or revoke the Sprint Manager role."""
	_require_manager()
	user = (user or "").strip()
	if not frappe.db.exists("User", user):
		frappe.throw(_("User '{0}' does not exist.").format(user))
	if user == "Administrator":
		frappe.throw(_("Administrator's roles can't be changed here."))
	doc = frappe.get_doc("User", user)
	want = bool(cint(is_manager))
	if want:
		doc.add_roles(MANAGER_ROLE)
	else:
		doc.remove_roles(MANAGER_ROLE)
	frappe.db.commit()
	return {"user": user, "is_manager": want}


@frappe.whitelist(methods=["POST"])
def set_user_enabled(user, enabled):
	"""Activate or deactivate a user. Disabled users drop out of every picker
	(assignee/access filter on enabled=1). Can't disable yourself or the
	Administrator."""
	_require_manager()
	user = (user or "").strip()
	enabled = cint(enabled)
	if not frappe.db.exists("User", user):
		frappe.throw(_("User '{0}' does not exist.").format(user))
	if not enabled and user in ("Administrator", frappe.session.user):
		frappe.throw(_("You can't disable yourself or the Administrator."))
	doc = frappe.get_doc("User", user)
	doc.enabled = enabled
	doc.save(ignore_permissions=True)  # User.on_update clears sessions on disable
	frappe.db.commit()
	return {"user": user, "enabled": bool(enabled)}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60)
def send_user_reset(user):
	"""Manager action: (re)send a set-password link to a user — used both to
	resend an invite and to reset a forgotten password. Returns a fresh copyable
	in-app link even when mail isn't configured."""
	_require_manager()
	user = (user or "").strip()
	if not frappe.db.exists("User", user):
		frappe.throw(_("User '{0}' does not exist.").format(user))
	if user == "Administrator":
		frappe.throw(_("Use the account page to change the Administrator password."))
	doc = frappe.get_doc("User", user)
	link = doc._reset_password(send_email=False)
	email_sent = False
	try:
		doc.password_reset_mail(link)
		email_sent = True
	except Exception:
		frappe.clear_messages()
	frappe.db.commit()
	return {"user": user, "invite_url": _to_app_reset_url(link), "email_sent": email_sent}


# ---- self-service account (current user only) ---------------------------
def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)


@frappe.whitelist()
def get_my_profile():
	_require_login()
	u = frappe.get_doc("User", frappe.session.user)
	return {
		"user": u.name,
		"email": u.email or u.name,
		"full_name": u.full_name or u.name,
		"image": u.user_image,
		"time_zone": u.time_zone,
	}


@frappe.whitelist(methods=["POST"])
def update_my_profile(full_name=None, time_zone=None, user_image=None):
	_require_login()
	u = frappe.get_doc("User", frappe.session.user)
	if full_name is not None:
		parts = (full_name or "").strip().split(" ", 1)
		if parts[0]:
			u.first_name = parts[0]
			u.last_name = parts[1] if len(parts) > 1 else ""
	if time_zone is not None:
		u.time_zone = time_zone
	if user_image is not None:
		u.user_image = user_image
	u.save(ignore_permissions=True)
	frappe.db.commit()
	return get_my_profile()


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=60)
def change_my_password(old_password, new_password):
	"""Change the current user's own password after re-verifying the old one.
	Frappe's doc save enforces the site's password policy on new_password."""
	_require_login()
	from frappe.utils.password import check_password

	try:
		check_password(frappe.session.user, old_password or "")
	except frappe.AuthenticationError:
		frappe.throw(_("Your current password is incorrect."))
	if not new_password:
		frappe.throw(_("Please choose a new password."))
	doc = frappe.get_doc("User", frappe.session.user)
	doc.new_password = new_password
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}
