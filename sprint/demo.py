"""Demo-data snapshot.

`export_demo_data()` snapshots the current site's Sprint content — every SP
Space with its DocType fields, buckets, and cards — into `demo_data.json`,
replacing every real user with a stable fake identity (in User-link fields,
ticket members, and best-effort inside text values such as @mentions).

`seed_demo_data()` recreates that snapshot on any site: demo users, space
DocTypes, SP Space registry rows, buckets, then cards (parents wired in a
second pass). Idempotent — spaces whose DocType already exists are skipped.

    bench --site <site> execute sprint.demo.export_demo_data   # maintainer
    bench --site <site> execute sprint.demo.seed_demo_data     # anyone
"""

import json
import os
import re

import frappe

from sprint.setup import create_space, ensure_space_doctype

DATA_FILE = os.path.join(os.path.dirname(__file__), "demo_data.json")

# DocField properties worth round-tripping (ensure_space_doctype consumes these)
_FIELD_PROPS = [
	"fieldname", "label", "fieldtype", "options", "reqd", "hidden",
	"read_only", "default", "in_list_view", "depends_on",
	"mandatory_depends_on", "read_only_depends_on", "description",
]
_LAYOUT_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Heading"}

# SP Space pointer/config columns copied verbatim
_SPACE_PROPS = [
	"label", "icon", "color", "space_type", "sort_order",
	"title_field", "bucket_field", "assignee_field", "body_field",
	"parent_field", "badge_field", "due_field", "chip_fields", "chip_options",
]

# fake identities assigned to real users in sorted order (Administrator/Guest
# are never mapped); overflow becomes person<N>@example.com
_DEMO_IDENTITIES = [
	("olivia@example.com", "Olivia", "Bennett"),
	("liam@example.com", "Liam", "Ford"),
	("maya@example.com", "Maya", "Patel"),
	("noah@example.com", "Noah", "Kim"),
	("ava@example.com", "Ava", "Romero"),
	("ethan@example.com", "Ethan", "Wright"),
	("zoe@example.com", "Zoe", "Chen"),
	("lucas@example.com", "Lucas", "Meyer"),
	("ines@example.com", "Ines", "Duarte"),
	("ravi@example.com", "Ravi", "Sharma"),
	("emma@example.com", "Emma", "Larsen"),
	("omar@example.com", "Omar", "Haddad"),
]
_KEEP_USERS = {"Administrator", "Guest", "", None}

# company / brand names scrubbed (case-insensitive) from EVERY exported string —
# card text, space labels, and DocType names alike ("GyanDhan Tech" → "Acme Tech").
# The `ga?yandhan` pattern also catches common typos of the name.
_COMPANY_SCRUB = [(re.compile(r"ga?yandhan", re.IGNORECASE), "Acme")]


def _identity(i):
	if i < len(_DEMO_IDENTITIES):
		return _DEMO_IDENTITIES[i]
	return (f"person{i + 1}@example.com", "Person", str(i + 1))


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def export_demo_data():
	spaces = frappe.get_all(
		"SP Space", fields=["name"] + _SPACE_PROPS, order_by="sort_order asc, name asc"
	)

	# collect every real user referenced anywhere, then build a stable mapping
	real_users = set()
	metas = {}
	for sp in spaces:
		meta = frappe.get_meta(sp.name)
		metas[sp.name] = meta
		user_fields = [
			df.fieldname for df in meta.fields
			if df.fieldtype == "Link" and df.options == "User"
		]
		if user_fields:
			for row in frappe.get_all(sp.name, fields=user_fields, limit_page_length=0):
				for uf in user_fields:
					if row.get(uf) and row[uf] not in _KEEP_USERS:
						real_users.add(row[uf])
		for tm in frappe.get_doc("SP Space", sp.name).ticket_members or []:
			if tm.user not in _KEEP_USERS:
				real_users.add(tm.user)

	user_map, demo_users = {}, []
	for i, email in enumerate(sorted(real_users)):
		demo_email, first, last = _identity(i)
		user_map[email] = demo_email
		demo_users.append({"email": demo_email, "first_name": first, "last_name": last})

	# best-effort scrub of emails/full names inside text values (@mentions etc.)
	replacements = []
	for email, demo_email in user_map.items():
		replacements.append((email, demo_email))
		full_name = frappe.db.get_value("User", email, "full_name")
		demo = next(u for u in demo_users if u["email"] == demo_email)
		if full_name:
			replacements.append((full_name, f"{demo['first_name']} {demo['last_name']}"))

	demo_emails = {u["email"] for u in demo_users}

	def scrub(value):
		if not isinstance(value, str):
			return value
		for old, new in replacements:
			value = value.replace(old, new)
		for pattern, new in _COMPANY_SCRUB:
			value = pattern.sub(new, value)
		# catch-all: any email that survived (typos, ad-hoc text) gets masked
		return re.sub(
			r"[\w.+-]+@[\w-]+\.[\w.-]+",
			lambda m: m.group(0) if m.group(0) in demo_emails else "someone@example.com",
			value,
		)

	def scrub_tree(node):
		"""Apply scrub to every string in a nested structure."""
		if isinstance(node, str):
			return scrub(node)
		if isinstance(node, list):
			return [scrub_tree(x) for x in node]
		if isinstance(node, dict):
			return {k: scrub_tree(v) for k, v in node.items()}
		return node

	out_spaces = []
	for sp in spaces:
		meta = metas[sp.name]
		fields = []
		for df in meta.fields:
			d = {}
			for prop in _FIELD_PROPS:
				v = df.get(prop)
				if v not in (None, ""):
					d[prop] = v
			fields.append(d)
		user_fields = {
			df.fieldname for df in meta.fields
			if df.fieldtype == "Link" and df.options == "User"
		}
		value_fields = [
			df.fieldname for df in meta.fields if df.fieldtype not in _LAYOUT_TYPES
		]

		buckets = frappe.get_all(
			"SP Bucket", filters={"space": sp.name},
			fields=["name", "bucket_name", "color", "sort_order", "wip_limit"],
			order_by="sort_order asc",
		)
		bucket_label = {b.pop("name"): b["bucket_name"] for b in buckets}

		bucket_field = sp.bucket_field or "bucket"
		parent_field = sp.parent_field or "parent_task"
		cards = []
		for row in frappe.get_all(
			sp.name, fields=["name"] + value_fields,
			order_by="creation asc", limit_page_length=0,
		):
			card = {"_ref": row.pop("name")}
			for fn, v in row.items():
				if v in (None, ""):
					continue
				if fn == bucket_field:
					card["_bucket"] = bucket_label.get(v)
				elif fn == parent_field:
					card["_parent_ref"] = v
				elif fn in user_fields:
					card[fn] = user_map.get(v, v if v in _KEEP_USERS else None)
				else:
					# the final scrub_tree pass handles anonymization
					card[fn] = str(v) if not isinstance(v, (int, float)) else v
			cards.append(card)

		out_spaces.append({
			"doctype": sp.name,
			**{p: sp.get(p) for p in _SPACE_PROPS},
			"ticket_members": [
				user_map.get(tm.user, tm.user)
				for tm in frappe.get_doc("SP Space", sp.name).ticket_members or []
			],
			"fields": fields,
			"buckets": buckets,
			"cards": cards,
		})

	# one recursive scrub over everything — card text, labels, bucket names,
	# field options, and the DocType names themselves stay consistent
	payload = scrub_tree({"users": demo_users, "spaces": out_spaces})
	with open(DATA_FILE, "w") as f:
		json.dump(payload, f, indent=1, default=str)
	print(f"exported {len(out_spaces)} spaces, "
	      f"{sum(len(s['cards']) for s in out_spaces)} cards, "
	      f"{len(demo_users)} anonymized users -> {DATA_FILE}")


# --------------------------------------------------------------------------
# seed
# --------------------------------------------------------------------------
def seed_demo_data():
	if not os.path.exists(DATA_FILE):
		print("no demo_data.json shipped with this build — nothing to seed")
		return
	with open(DATA_FILE) as f:
		data = json.load(f)

	for u in data.get("users", []):
		if frappe.db.exists("User", u["email"]):
			continue
		user = frappe.get_doc({
			"doctype": "User",
			"email": u["email"],
			"first_name": u["first_name"],
			"last_name": u.get("last_name"),
			"user_type": "System User",
			"send_welcome_email": 0,
			"enabled": 1,
		})
		# demo users are placeholders — don't trip over site-specific
		# mandatory customisations on User
		user.flags.ignore_mandatory = True
		user.insert(ignore_permissions=True)
		print("created demo user", u["email"])

	for s in data.get("spaces", []):
		if frappe.db.exists("DocType", s["doctype"]):
			print("skipping", s["doctype"], "(already exists)")
			continue

		ensure_space_doctype(s["doctype"], [dict(f) for f in s["fields"]])
		create_space(
			s["doctype"],
			label=s["label"],
			icon=s.get("icon"),
			color=s.get("color"),
			order=s.get("sort_order") or 0,
			title_field=s.get("title_field") or "title",
			bucket_field=s.get("bucket_field") or "bucket",
			assignee_field=s.get("assignee_field"),
			body_field=s.get("body_field"),
			parent_field=s.get("parent_field") or "parent_task",
			badge_field=s.get("badge_field"),
			due_field=s.get("due_field"),
			chip_fields=s.get("chip_fields") or "",
			buckets=s["buckets"],
			space_type=s.get("space_type") or "Task",
		)
		sp = frappe.get_doc("SP Space", s["doctype"])
		if s.get("chip_options"):
			sp.chip_options = s["chip_options"]
		for user in s.get("ticket_members", []):
			if frappe.db.exists("User", user):
				sp.append("ticket_members", {"user": user})
		sp.save(ignore_permissions=True)

		bucket_map = {
			b.bucket_name: b.name
			for b in frappe.get_all(
				"SP Bucket", filters={"space": s["doctype"]},
				fields=["name", "bucket_name"],
			)
		}
		bucket_field = s.get("bucket_field") or "bucket"
		parent_field = s.get("parent_field") or "parent_task"

		ref_to_name, deferred_parents = {}, []
		for card in s["cards"]:
			values = {
				k: v for k, v in card.items()
				if not k.startswith("_") and v not in (None, "")
			}
			if card.get("_bucket") and bucket_map.get(card["_bucket"]):
				values[bucket_field] = bucket_map[card["_bucket"]]
			doc = frappe.get_doc({"doctype": s["doctype"], **values})
			doc.insert(ignore_permissions=True)
			ref_to_name[card["_ref"]] = doc.name
			if card.get("_parent_ref"):
				deferred_parents.append((doc.name, card["_parent_ref"]))

		for name, parent_ref in deferred_parents:
			if parent_ref in ref_to_name:
				frappe.db.set_value(
					s["doctype"], name, parent_field, ref_to_name[parent_ref],
					update_modified=False,
				)

		print(f"seeded {s['doctype']}: {len(s['cards'])} cards, "
		      f"{len(s['buckets'])} buckets")

	frappe.db.commit()
	frappe.clear_cache()
	print("demo data seeded")
