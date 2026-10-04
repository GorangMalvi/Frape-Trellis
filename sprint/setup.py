"""
Sprint — a meta-driven, ClickUp-like board over Frappe DocTypes.

Model
-----
- Each *space* IS a DocType (the card entity). For runtime/admin creation these
  are Custom DocTypes (custom=1).
- `SP Space` is a thin registry: one row per space, naming itself after the
  target DocType, holding display config (icon/color/order) and pointers to the
  important fields (title / bucket / assignee / body).
- `SP Bucket` rows are the board columns for a space (color + order + wip).
  A card links to its bucket, so renaming/reordering a bucket never touches the
  card records.

Run order (idempotent):
    bench --site SITE execute sprint.setup.install_all
"""

import json

import frappe

MODULE = "Sprint"

# default option list seeded onto every space's `tags` chip field
DEFAULT_TAG_OPTIONS = ["b2b", "b2c", "seo", "feature", "bug", "tech_debt", "keka", "exploratory"]
SPACE_TYPE_OPTIONS = "Task\nTicket"
TICKET_PRIORITY_OPTIONS = "Low\nMedium\nHigh\nUrgent"

FULL_PERMS = [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1,
     "report": 1, "export": 1, "share": 1},
]

V1_DOCTYPES = ["SP Task", "SP Task Assignee", "SP List", "SP Folder", "SP Space"]


# --------------------------------------------------------------------------
# cleanup of the v1 prototype
# --------------------------------------------------------------------------
def cleanup_v1():
    """Remove the throwaway v1 doctypes so SP Space can be redefined."""
    for dt in V1_DOCTYPES:
        if frappe.db.exists("DocType", dt):
            frappe.delete_doc("DocType", dt, force=1, ignore_permissions=1)
            print("dropped", dt)
    frappe.db.commit()
    frappe.clear_cache()


# --------------------------------------------------------------------------
# meta doctypes: SP Space (registry) + SP Bucket
# --------------------------------------------------------------------------
def _doctype(name, title_field, fields, autoname="hash", istable=0, custom=0):
    return {
        "doctype": "DocType",
        "name": name,
        "module": MODULE,
        "custom": custom,
        "istable": istable,
        "editable_grid": istable,
        "autoname": autoname,
        "naming_rule": "Expression"
        if autoname.startswith(("format:", "field:"))
        else "Random",
        "title_field": title_field,
        "track_changes": 0 if istable else 1,
        "allow_rename": 0,
        "fields": fields,
        "permissions": [] if istable else FULL_PERMS,
    }


def create_meta_doctypes():
    if not frappe.db.exists("DocType", "SP Space"):
        frappe.get_doc(
            _doctype(
                "SP Space",
                "label",
                [
                    {"fieldname": "target_doctype", "label": "Target DocType",
                     "fieldtype": "Link", "options": "DocType", "reqd": 1,
                     "in_list_view": 1},
                    {"fieldname": "label", "label": "Label", "fieldtype": "Data",
                     "reqd": 1, "in_list_view": 1},
                    {"fieldname": "icon", "label": "Icon", "fieldtype": "Data"},
                    {"fieldname": "color", "label": "Color", "fieldtype": "Data"},
                    {"fieldname": "sort_order", "label": "Order", "fieldtype": "Int"},
                    {"fieldname": "space_type", "label": "Space Type",
                     "fieldtype": "Select", "options": SPACE_TYPE_OPTIONS,
                     "default": "Task", "in_list_view": 1},
                    {"fieldname": "read_access", "label": "View Access",
                     "fieldtype": "Select", "options": "All\nSelected Users",
                     "default": "All"},
                    {"fieldname": "write_access", "label": "Edit Access",
                     "fieldtype": "Select", "options": "All\nSelected Users",
                     "default": "All"},
                    {"fieldname": "access_users", "label": "Space Access Users",
                     "fieldtype": "Table", "options": "SP Space Access"},
                    {"fieldname": "cb1", "fieldtype": "Column Break"},
                    {"fieldname": "title_field", "label": "Title Field",
                     "fieldtype": "Data", "default": "title"},
                    {"fieldname": "bucket_field", "label": "Bucket Field",
                     "fieldtype": "Data", "default": "bucket"},
                    {"fieldname": "assignee_field", "label": "Assignee Field",
                     "fieldtype": "Data"},
                    {"fieldname": "body_field", "label": "Body Field",
                     "fieldtype": "Data"},
                    {"fieldname": "parent_field", "label": "Parent (Subtask) Field",
                     "fieldtype": "Data", "default": "parent_task"},
                    {"fieldname": "badge_field", "label": "Badge Field",
                     "fieldtype": "Data", "default": "sprint_points"},
                    {"fieldname": "due_field", "label": "Due Date Field",
                     "fieldtype": "Data"},
                    {"fieldname": "chip_fields", "label": "Chip Fields (comma-sep)",
                     "fieldtype": "Data"},
                    {"fieldname": "chip_options", "label": "Chip Options (JSON)",
                     "fieldtype": "Long Text"},
                    {"fieldname": "ticket_members", "label": "Ticket Members",
                     "fieldtype": "Table", "options": "SP Ticket Member"},
                ],
                autoname="field:target_doctype",
            )
        ).insert(ignore_permissions=True)
        print("created SP Space")

    if not frappe.db.exists("DocType", "SP Ticket Member"):
        frappe.get_doc(
            _doctype(
                "SP Ticket Member",
                "user",
                [
                    {"fieldname": "user", "label": "User", "fieldtype": "Link",
                     "options": "User", "reqd": 1, "in_list_view": 1},
                ],
                istable=1,
            )
        ).insert(ignore_permissions=True)
        print("created SP Ticket Member")

    if not frappe.db.exists("DocType", "SP Space Access"):
        frappe.get_doc(
            _doctype(
                "SP Space Access",
                "user",
                [
                    {"fieldname": "user", "label": "User", "fieldtype": "Link",
                     "options": "User", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "can_read", "label": "Can View",
                     "fieldtype": "Check", "default": "1", "in_list_view": 1},
                    {"fieldname": "can_write", "label": "Can Edit",
                     "fieldtype": "Check", "default": "0", "in_list_view": 1},
                ],
                istable=1,
            )
        ).insert(ignore_permissions=True)
        print("created SP Space Access")

    if not frappe.db.exists("DocType", "SP Bucket"):
        frappe.get_doc(
            _doctype(
                "SP Bucket",
                "bucket_name",
                [
                    {"fieldname": "bucket_name", "label": "Bucket Name",
                     "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "space", "label": "Space", "fieldtype": "Link",
                     "options": "SP Space", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "color", "label": "Color", "fieldtype": "Data"},
                    {"fieldname": "sort_order", "label": "Order", "fieldtype": "Int",
                     "in_list_view": 1},
                    {"fieldname": "wip_limit", "label": "WIP Limit", "fieldtype": "Int"},
                ],
            )
        ).insert(ignore_permissions=True)
        print("created SP Bucket")

    if not frappe.db.exists("DocType", "SP View"):
        frappe.get_doc(
            _doctype(
                "SP View",
                "view_name",
                [
                    {"fieldname": "view_name", "label": "View Name", "fieldtype": "Data",
                     "reqd": 1, "in_list_view": 1},
                    {"fieldname": "space", "label": "Space", "fieldtype": "Link",
                     "options": "SP Space", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "view_type", "label": "View Type", "fieldtype": "Select",
                     "options": "Board\nList\nCalendar", "default": "Board", "in_list_view": 1},
                    {"fieldname": "icon", "label": "Icon", "fieldtype": "Data"},
                    {"fieldname": "group_by", "label": "Group By", "fieldtype": "Data"},
                    {"fieldname": "sort_field", "label": "Sort Field", "fieldtype": "Data"},
                    {"fieldname": "sort_dir", "label": "Sort Direction", "fieldtype": "Select",
                     "options": "asc\ndesc", "default": "asc"},
                    {"fieldname": "me_mode", "label": "Me Mode", "fieldtype": "Check", "default": "0"},
                    {"fieldname": "is_shared", "label": "Shared", "fieldtype": "Check", "default": "1"},
                    {"fieldname": "filters_json", "label": "Filters JSON", "fieldtype": "Long Text"},
                ],
            )
        ).insert(ignore_permissions=True)
        print("created SP View")

    ensure_space_fields()
    ensure_roles()
    frappe.db.commit()
    frappe.clear_cache()


def ensure_space_type_field():
    ensure_space_fields()


def ensure_space_fields():
    """Add access/ticket-related fields to existing SP Space benches."""
    if not frappe.db.exists("DocType", "SP Ticket Member"):
        frappe.get_doc(
            _doctype(
                "SP Ticket Member",
                "user",
                [
                    {"fieldname": "user", "label": "User", "fieldtype": "Link",
                     "options": "User", "reqd": 1, "in_list_view": 1},
                ],
                istable=1,
            )
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("created SP Ticket Member")
    if not frappe.db.exists("DocType", "SP Space Access"):
        frappe.get_doc(
            _doctype(
                "SP Space Access",
                "user",
                [
                    {"fieldname": "user", "label": "User", "fieldtype": "Link",
                     "options": "User", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "can_read", "label": "Can View",
                     "fieldtype": "Check", "default": "1", "in_list_view": 1},
                    {"fieldname": "can_write", "label": "Can Edit",
                     "fieldtype": "Check", "default": "0", "in_list_view": 1},
                ],
                istable=1,
            )
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("created SP Space Access")
    if not frappe.db.exists("DocType", "SP Space"):
        return
    dt = frappe.get_doc("DocType", "SP Space")
    changed = False
    if not any(f.fieldname == "space_type" for f in dt.fields):
        dt.append("fields", {
            "fieldname": "space_type",
            "label": "Space Type",
            "fieldtype": "Select",
            "options": SPACE_TYPE_OPTIONS,
            "default": "Task",
            "in_list_view": 1,
        })
        changed = True
    if not any(f.fieldname == "ticket_members" for f in dt.fields):
        dt.append("fields", {
            "fieldname": "ticket_members",
            "label": "Ticket Members",
            "fieldtype": "Table",
            "options": "SP Ticket Member",
        })
        changed = True
    for field in [
        {
            "fieldname": "read_access",
            "label": "View Access",
            "fieldtype": "Select",
            "options": "All\nSelected Users",
            "default": "All",
        },
        {
            "fieldname": "write_access",
            "label": "Edit Access",
            "fieldtype": "Select",
            "options": "All\nSelected Users",
            "default": "All",
        },
        {
            "fieldname": "access_users",
            "label": "Space Access Users",
            "fieldtype": "Table",
            "options": "SP Space Access",
        },
        {
            "fieldname": "due_field",
            "label": "Due Date Field",
            "fieldtype": "Data",
        },
    ]:
        if not any(f.fieldname == field["fieldname"] for f in dt.fields):
            dt.append("fields", field)
            changed = True
    if changed:
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("added ticket fields to SP Space")
    if frappe.db.has_column("SP Space", "space_type"):
        frappe.db.sql("update `tabSP Space` set space_type='Task' where ifnull(space_type, '')=''")
        frappe.db.commit()
    if frappe.db.has_column("SP Space", "read_access"):
        frappe.db.sql("update `tabSP Space` set read_access='All' where ifnull(read_access, '')=''")
    if frappe.db.has_column("SP Space", "write_access"):
        frappe.db.sql("update `tabSP Space` set write_access='All' where ifnull(write_access, '')=''")
    frappe.db.commit()


CLOSED_BUCKET_NAMES = {"done", "closed", "complete", "completed", "cancelled", "resolved"}


def ensure_batch2_meta():
    """Additive migration for calendar views, card templates and watchers.

    - `SP View.view_type` gains a Calendar option.
    - `SP Template` — per-space card templates ({field: value} JSON presets).
    - `SP Watcher` — per-card subscriptions (who gets notified on changes).

    Run: bench --site SITE execute sprint.setup.ensure_batch2_meta
    """
    vd = frappe.get_doc("DocType", "SP View")
    vt = next((f for f in vd.fields if f.fieldname == "view_type"), None)
    if vt and "Calendar" not in (vt.options or ""):
        vt.options = "Board\nList\nCalendar"
        vd.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("added Calendar to SP View.view_type")

    if not frappe.db.exists("DocType", "SP Template"):
        frappe.get_doc(
            _doctype(
                "SP Template",
                "template_name",
                [
                    {"fieldname": "template_name", "label": "Template Name",
                     "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "space", "label": "Space", "fieldtype": "Link",
                     "options": "SP Space", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "sort_order", "label": "Order", "fieldtype": "Int"},
                    {"fieldname": "values_json", "label": "Values JSON",
                     "fieldtype": "Long Text"},
                ],
            )
        ).insert(ignore_permissions=True)
        print("created SP Template")

    if not frappe.db.exists("DocType", "SP Watcher"):
        frappe.get_doc(
            _doctype(
                "SP Watcher",
                "user",
                [
                    {"fieldname": "ref_doctype", "label": "Ref DocType",
                     "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "ref_name", "label": "Ref Name",
                     "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "user", "label": "User", "fieldtype": "Link",
                     "options": "User", "reqd": 1, "in_list_view": 1},
                ],
            )
        ).insert(ignore_permissions=True)
        print("created SP Watcher")

    frappe.db.commit()
    frappe.clear_cache()
    print("ensure_batch2_meta done")


def ensure_due_and_closed_fields():
    """Additive migration for the Home page + dashboards:

    - `SP Space.due_field` — registry pointer to the space's due-date field
      (backfilled to 'due_date' where the target doctype has one).
    - `SP Bucket.is_closed` — marks a bucket as terminal ("Done"), so "my
      open tasks" and "overdue" can exclude finished work. Backfilled by
      common closed-bucket names.

    Run: bench --site SITE execute sprint.setup.ensure_due_and_closed_fields
    """
    ensure_space_fields()  # adds due_field to SP Space (among others)

    bd = frappe.get_doc("DocType", "SP Bucket")
    if not any(f.fieldname == "is_closed" for f in bd.fields):
        bd.append("fields", {
            "fieldname": "is_closed",
            "label": "Closed (terminal)",
            "fieldtype": "Check",
            "default": "0",
            "in_list_view": 1,
        })
        bd.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("added is_closed to SP Bucket")

    # backfill due_field where the space's doctype actually has a due_date
    for sp in frappe.get_all("SP Space", fields=["name", "target_doctype", "due_field"]):
        if sp.due_field or not frappe.db.exists("DocType", sp.target_doctype):
            continue
        meta = frappe.get_meta(sp.target_doctype)
        f = meta.get_field("due_date")
        if f and f.fieldtype in ("Date", "Datetime"):
            frappe.db.set_value("SP Space", sp.name, "due_field", "due_date",
                                update_modified=False)
            print(f"  {sp.name}: due_field -> due_date")

    # backfill is_closed for buckets with obviously-terminal names
    for b in frappe.get_all("SP Bucket", fields=["name", "bucket_name", "is_closed"]):
        if not b.is_closed and (b.bucket_name or "").strip().lower() in CLOSED_BUCKET_NAMES:
            frappe.db.set_value("SP Bucket", b.name, "is_closed", 1, update_modified=False)
            print(f"  bucket {b.bucket_name}: is_closed = 1")
    frappe.db.commit()
    frappe.clear_cache()
    print("ensure_due_and_closed_fields done")


def ensure_dashboard_field():
    """Additive migration for the configurable dashboard: a per-space
    `dashboard_json` holding the widget layout (null = show auto-defaults).
    Idempotent; run from after_migrate.

    Run: bench --site SITE execute sprint.setup.ensure_dashboard_field
    """
    if not frappe.db.exists("DocType", "SP Space"):
        return
    dt = frappe.get_doc("DocType", "SP Space")
    if not any(f.fieldname == "dashboard_json" for f in dt.fields):
        dt.append("fields", {
            "fieldname": "dashboard_json",
            "label": "Dashboard (JSON)",
            "fieldtype": "Long Text",
        })
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache()
        print("added dashboard_json to SP Space")


AUTOMATION_TRIGGERS = "\n".join([
    "card_created", "moved_to_bucket", "field_changed", "assignee_changed",
    "comment_added", "due_date_arrived", "due_date_approaching", "card_inactive",
    "scheduled",
])


def ensure_automation_meta():
    """Additive migration for the automation engine (SP Automation rules +
    SP Automation Run log). Idempotent; run from after_migrate.

    Run: bench --site SITE execute sprint.setup.ensure_automation_meta
    """
    if not frappe.db.exists("DocType", "SP Space"):
        return

    if not frappe.db.exists("DocType", "SP Automation"):
        frappe.get_doc(
            _doctype(
                "SP Automation",
                "automation_name",
                [
                    {"fieldname": "automation_name", "label": "Automation Name",
                     "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "space", "label": "Space", "fieldtype": "Link",
                     "options": "SP Space", "reqd": 1, "in_list_view": 1,
                     "search_index": 1},
                    {"fieldname": "enabled", "label": "Enabled",
                     "fieldtype": "Check", "default": "1", "in_list_view": 1},
                    {"fieldname": "description", "label": "Description",
                     "fieldtype": "Small Text"},
                    {"fieldname": "trigger_type", "label": "Trigger Type",
                     "fieldtype": "Select", "options": AUTOMATION_TRIGGERS,
                     "reqd": 1, "in_list_view": 1},
                    {"fieldname": "trigger_config", "label": "Trigger Config (JSON)",
                     "fieldtype": "Long Text"},
                    {"fieldname": "conditions", "label": "Conditions (JSON)",
                     "fieldtype": "Long Text"},
                    {"fieldname": "actions", "label": "Actions (JSON)",
                     "fieldtype": "Long Text"},
                    {"fieldname": "webhook_secret", "label": "Webhook Secret",
                     "fieldtype": "Password"},
                    {"fieldname": "next_run", "label": "Next Run", "fieldtype": "Datetime"},
                    {"fieldname": "last_run", "label": "Last Run", "fieldtype": "Datetime"},
                    {"fieldname": "last_status", "label": "Last Status", "fieldtype": "Data"},
                    {"fieldname": "run_count", "label": "Run Count", "fieldtype": "Int"},
                    {"fieldname": "rr_index", "label": "Round-robin Index",
                     "fieldtype": "Int"},
                ],
            )
        ).insert(ignore_permissions=True)
        print("created SP Automation")

    if not frappe.db.exists("DocType", "SP Automation Run"):
        run_dt = _doctype(
            "SP Automation Run",
            "automation_label",
            [
                # automation is Data (not Link) on purpose: runs must survive
                # rule deletion so the daily quota can't be reset by
                # delete-and-recreate, and there's no dangling-link validation.
                {"fieldname": "automation", "label": "Automation",
                 "fieldtype": "Data", "search_index": 1},
                {"fieldname": "automation_label", "label": "Automation Label",
                 "fieldtype": "Data", "in_list_view": 1},
                {"fieldname": "space", "label": "Space", "fieldtype": "Link",
                 "options": "SP Space", "search_index": 1, "in_list_view": 1},
                {"fieldname": "ref_doctype", "label": "Ref DocType", "fieldtype": "Data"},
                {"fieldname": "ref_name", "label": "Ref Name", "fieldtype": "Data"},
                {"fieldname": "trigger_type", "label": "Trigger Type",
                 "fieldtype": "Data", "in_list_view": 1},
                {"fieldname": "trigger_snapshot", "label": "Trigger Snapshot (JSON)",
                 "fieldtype": "Long Text"},
                {"fieldname": "status", "label": "Status", "fieldtype": "Select",
                 "options": "Success\nPartial\nFailed\nSkipped", "in_list_view": 1},
                {"fieldname": "actions_log", "label": "Actions Log (JSON)",
                 "fieldtype": "Long Text"},
                {"fieldname": "error", "label": "Error", "fieldtype": "Small Text"},
                {"fieldname": "duration_ms", "label": "Duration (ms)", "fieldtype": "Int"},
                {"fieldname": "triggered_by", "label": "Triggered By", "fieldtype": "Data"},
            ],
        )
        run_dt["track_changes"] = 0  # a log table needs no Version rows
        frappe.get_doc(run_dt).insert(ignore_permissions=True)
        print("created SP Automation Run")

    frappe.db.commit()
    frappe.clear_cache()
    print("ensure_automation_meta done")


def ensure_roles():
    """The 'Sprint Manager' role grants structural rights (spaces, fields,
    buckets, data import) without handing out the Administrator account."""
    if not frappe.db.exists("Role", "Sprint Manager"):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": "Sprint Manager",
            "desk_access": 0,
        }).insert(ignore_permissions=True)
        print("created role Sprint Manager")


# --------------------------------------------------------------------------
# generic space creation — used by demo + the UI's "+ New Space"
# --------------------------------------------------------------------------
def ensure_space_doctype(doctype_name, fields):
    """Create a Custom DocType (custom=1) representing a space's card entity.

    `fields` is a list of field dicts. A `bucket` Link->SP Bucket and a
    `parent_task` self-link are always appended if not already present so every
    space supports the board + subtasks.
    """
    if frappe.db.exists("DocType", doctype_name):
        return frappe.get_doc("DocType", doctype_name)

    fieldnames = {f["fieldname"] for f in fields}
    if "bucket" not in fieldnames:
        fields.append({"fieldname": "bucket", "label": "Bucket",
                       "fieldtype": "Link", "options": "SP Bucket"})
    if "parent_task" not in fieldnames:
        fields.append({"fieldname": "parent_task", "label": "Parent Task",
                       "fieldtype": "Link", "options": doctype_name})
    if "position" not in fieldnames:
        # manual drag-ordering rank; hidden from the card UI
        fields.append({"fieldname": "position", "label": "Position",
                       "fieldtype": "Float", "hidden": 1})

    doc = frappe.get_doc(
        _doctype(doctype_name, "title", fields,
                 autoname="hash", custom=1)
    )
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("created space doctype", doctype_name)
    return doc


def create_space(target_doctype, label, icon=None, color=None, order=0,
                 title_field="title", bucket_field="bucket",
                 assignee_field=None, body_field=None,
                 parent_field="parent_task", badge_field="sprint_points",
                 chip_fields="", buckets=None, space_type="Task",
                 due_field=None):
    """Register a DocType as a space and (re)create its buckets."""
    if not frappe.db.exists("SP Space", target_doctype):
        frappe.get_doc({
            "doctype": "SP Space",
            "target_doctype": target_doctype,
            "label": label,
            "icon": icon,
            "color": color,
            "order": order,
            "space_type": space_type,
            "title_field": title_field,
            "bucket_field": bucket_field,
            "assignee_field": assignee_field,
            "body_field": body_field,
            "parent_field": parent_field,
            "badge_field": badge_field,
            "due_field": due_field,
            "chip_fields": chip_fields,
            "sort_order": order,
        }).insert(ignore_permissions=True)
        print("registered space", target_doctype)

    created_buckets = []
    for i, b in enumerate(buckets or []):
        exists = frappe.db.exists(
            "SP Bucket", {"space": target_doctype, "bucket_name": b["bucket_name"]}
        )
        if exists:
            created_buckets.append(exists)
            continue
        doc = frappe.get_doc({
            "doctype": "SP Bucket",
            "space": target_doctype,
            "bucket_name": b["bucket_name"],
            "color": b.get("color"),
            "sort_order": b.get("sort_order", i),
            "wip_limit": b.get("wip_limit", 0),
        }).insert(ignore_permissions=True)
        created_buckets.append(doc.name)

    frappe.db.commit()
    frappe.clear_cache()
    return created_buckets


def ticket_core_fields():
    """Core fields every ticket-space DocType must carry."""
    return [
        {"fieldname": "title", "label": "Title", "fieldtype": "Data",
         "reqd": 1, "in_list_view": 1},
        {"fieldname": "requester", "label": "Requester", "fieldtype": "Link",
         "options": "User", "reqd": 1, "read_only": 1, "in_list_view": 1},
        {"fieldname": "assignee", "label": "Assignee", "fieldtype": "Link",
         "options": "User", "in_list_view": 1},
        {"fieldname": "priority", "label": "Priority", "fieldtype": "Select",
         "options": TICKET_PRIORITY_OPTIONS, "default": "Medium", "in_list_view": 1},
        {"fieldname": "description", "label": "Description", "fieldtype": "Text Editor"},
    ]


def create_ticket_space(target_doctype, label, icon=None, color=None, order=0, buckets=None, members=None):
    """Create/register a ticket space using the same meta-driven renderer."""
    ensure_space_doctype(target_doctype, ticket_core_fields())
    created_buckets = create_space(
        target_doctype,
        label=label,
        icon=icon,
        color=color,
        order=order,
        title_field="title",
        bucket_field="bucket",
        assignee_field="assignee",
        body_field="description",
        badge_field="priority",
        buckets=buckets or [],
        space_type="Ticket",
    )
    if members:
        sp = frappe.get_doc("SP Space", target_doctype)
        sp.ticket_members = []
        for user in members:
            if user and frappe.db.exists("User", user):
                sp.append("ticket_members", {"user": user})
        sp.save(ignore_permissions=True)
        frappe.db.commit()
    return created_buckets


# --------------------------------------------------------------------------
# demo space — mirrors the real admin flow (a Custom DocType at runtime)
# --------------------------------------------------------------------------
DEMO_DOCTYPE = "Dev Task"


def setup_demo():
    ensure_space_doctype(
        DEMO_DOCTYPE,
        [
            {"fieldname": "title", "label": "Title", "fieldtype": "Data",
             "reqd": 1, "in_list_view": 1},
            {"fieldname": "sprint_points", "label": "Sprint Points", "fieldtype": "Select",
             "options": "\n".join(str(i) for i in range(1, 11)), "in_list_view": 1},
            {"fieldname": "developer", "label": "Developer", "fieldtype": "Link",
             "options": "User"},
            {"fieldname": "apm", "label": "APM", "fieldtype": "Link",
             "options": "User"},
            {"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date"},
            {"fieldname": "sec_body", "label": "Task Context",
             "fieldtype": "Section Break"},
            {"fieldname": "body", "label": "Body", "fieldtype": "Text Editor"},
        ],
    )

    buckets = create_space(
        DEMO_DOCTYPE,
        label="Dev Tasks",
        icon="💻",
        color="#6366f1",
        order=0,
        title_field="title",
        bucket_field="bucket",
        assignee_field="developer",
        body_field="body",
        buckets=[
            {"bucket_name": "Backlog", "color": "#9ca3af", "order": 0},
            {"bucket_name": "In Progress", "color": "#3b82f6", "order": 1},
            {"bucket_name": "In Review", "color": "#a855f7", "order": 2},
            {"bucket_name": "Done", "color": "#22c55e", "order": 3},
        ],
    )
    backlog, in_prog, in_review, done = buckets

    if not frappe.db.count(DEMO_DOCTYPE):
        seeds = [
            ("Set up CI pipeline", "8", in_prog, "Administrator",
             "<p>Configure GitHub Actions to run tests on every PR.</p>"),
            ("Design board view", "5", in_prog, "Administrator",
             "<p>Kanban with draggable cards grouped by bucket.</p>"),
            ("Fix login redirect bug", "3", backlog, "Administrator",
             "<p>Users land on a 404 after SSO login.</p>"),
            ("Write API docs", "2", backlog, "Administrator", ""),
            ("Add dark mode", "5", in_review, "Administrator", ""),
            ("Ship v1.0", "10", done, "Administrator", ""),
        ]
        parent_name = None
        for i, (title, sp, bucket, dev, body) in enumerate(seeds):
            d = frappe.get_doc({
                "doctype": DEMO_DOCTYPE, "title": title, "sprint_points": sp,
                "bucket": bucket, "developer": dev, "body": body,
            }).insert(ignore_permissions=True)
            if i == 0:
                parent_name = d.name
        # a couple of subtasks under the first card (same space)
        for st in ["Add test runner", "Cache dependencies"]:
            frappe.get_doc({
                "doctype": DEMO_DOCTYPE, "title": st, "sprint_points": "3",
                "bucket": in_prog, "parent_task": parent_name,
            }).insert(ignore_permissions=True)
        frappe.db.commit()
        print("seeded demo cards + subtasks")


def ensure_position_field(doctype):
    """Add the hidden `position` rank field to an existing space DocType and
    backfill any unset positions. Idempotent."""
    dt = frappe.get_doc("DocType", doctype)
    if not any(f.fieldname == "position" for f in dt.fields):
        dt.append("fields", {"fieldname": "position", "label": "Position",
                             "fieldtype": "Float", "hidden": 1})
        dt.save()
        frappe.db.commit()
        frappe.clear_cache()
        print("added position field to", doctype)

    rows = frappe.get_all(doctype, filters={"position": ["in", [0, None]]},
                          fields=["name"], order_by="creation asc")
    for i, r in enumerate(rows, start=1):
        frappe.db.set_value(doctype, r.name, "position", float(i), update_modified=False)
    frappe.db.commit()
    print("backfilled", len(rows), "positions in", doctype)


def setup_positions():
    ensure_position_field(DEMO_DOCTYPE)


def delete_space(target_doctype):
    """Remove a space entirely: its buckets, registry row, and the DocType+table."""
    for b in frappe.get_all("SP Bucket", filters={"space": target_doctype}):
        frappe.delete_doc("SP Bucket", b.name, force=1, ignore_permissions=1)
    # automation rules + run log for this space (both keyed by SP Space name)
    for dt in ("SP Automation", "SP Automation Run"):
        if frappe.db.exists("DocType", dt):
            frappe.db.delete(dt, {"space": target_doctype})
    if frappe.db.exists("SP Space", target_doctype):
        frappe.delete_doc("SP Space", target_doctype, force=1, ignore_permissions=1)
    if frappe.db.exists("DocType", target_doctype):
        frappe.delete_doc("DocType", target_doctype, force=1, ignore_permissions=1)
        frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{target_doctype}`")
    frappe.db.commit()
    frappe.clear_cache()
    print("deleted space", target_doctype)


SPRINT_POINT_OPTIONS = "\n".join(str(i) for i in range(1, 11))


def migrate_to_sprint_points():
    """Replace the `priority` Select field with `sprint_points` (1-10) on every
    space DocType, add `badge_field` to the registry, and point all spaces at
    `sprint_points`. Old priority values are dropped (column orphaned)."""
    # 1. ensure SP Space has the badge_field column
    spd = frappe.get_doc("DocType", "SP Space")
    if not any(f.fieldname == "badge_field" for f in spd.fields):
        spd.append("fields", {"fieldname": "badge_field", "label": "Badge Field",
                              "fieldtype": "Data", "default": "sprint_points"})
        spd.save()
        frappe.db.commit()
        frappe.clear_cache()
        print("added badge_field to SP Space")

    # 2. each space: swap priority -> sprint_points on the entity doctype + set pointer
    for sp in frappe.get_all("SP Space", fields=["name", "target_doctype"]):
        dt_name = sp.target_doctype
        if not frappe.db.exists("DocType", dt_name):
            continue
        dt = frappe.get_doc("DocType", dt_name)
        has_priority = any(f.fieldname == "priority" for f in dt.fields)
        has_sp = any(f.fieldname == "sprint_points" for f in dt.fields)
        if has_priority or not has_sp:
            dt.fields = [f for f in dt.fields if f.fieldname != "priority"]
            if not has_sp:
                dt.append("fields", {"fieldname": "sprint_points", "label": "Sprint Points",
                                     "fieldtype": "Select", "options": SPRINT_POINT_OPTIONS,
                                     "in_list_view": 1})
            dt.save()
            print(f"  {dt_name}: priority -> sprint_points")
        frappe.db.set_value("SP Space", sp.name, "badge_field", "sprint_points",
                            update_modified=False)
    frappe.db.commit()
    frappe.clear_cache()
    print("migrate_to_sprint_points done")


def migrate_tags():
    """Add `chip_fields` to SP Space, and make every space's `tags` a free-form
    chip field (Small Text), registering it in chip_fields. Idempotent."""
    spd = frappe.get_doc("DocType", "SP Space")
    if not any(f.fieldname == "chip_fields" for f in spd.fields):
        spd.append("fields", {"fieldname": "chip_fields", "label": "Chip Fields (comma-sep)",
                              "fieldtype": "Data"})
        spd.save()
        frappe.db.commit()
        frappe.clear_cache()
        print("added chip_fields to SP Space")

    for sp in frappe.get_all("SP Space", fields=["name", "target_doctype"]):
        dt = frappe.get_doc("DocType", sp.target_doctype)
        tags = next((f for f in dt.fields if f.fieldname == "tags"), None)
        if tags:
            tags.fieldtype = "Small Text"
            tags.options = ""
        else:
            dt.append("fields", {"fieldname": "tags", "label": "Tags", "fieldtype": "Small Text"})
        dt.save()
        # register tags as a chip field
        existing = (frappe.db.get_value("SP Space", sp.name, "chip_fields") or "").split(",")
        existing = [c.strip() for c in existing if c.strip()]
        if "tags" not in existing:
            existing.append("tags")
        frappe.db.set_value("SP Space", sp.name, "chip_fields", ",".join(existing),
                            update_modified=False)
        print(f"  {sp.target_doctype}: tags -> Small Text chip field")
    frappe.db.commit()
    frappe.clear_cache()
    print("migrate_tags done")


def migrate_chip_options():
    """Add `chip_options` (a JSON map fieldname -> [options]) to SP Space and
    seed the default option list onto every space's `tags` chip field. Idempotent."""
    spd = frappe.get_doc("DocType", "SP Space")
    if not any(f.fieldname == "chip_options" for f in spd.fields):
        spd.append("fields", {"fieldname": "chip_options", "label": "Chip Options (JSON)",
                              "fieldtype": "Long Text"})
        spd.save()
        frappe.db.commit()
        frappe.clear_cache()
        print("added chip_options to SP Space")

    for sp in frappe.get_all("SP Space", fields=["name", "chip_fields", "chip_options"]):
        chip_fields = [c.strip() for c in (sp.chip_fields or "").split(",") if c.strip()]
        try:
            opts = json.loads(sp.chip_options) if sp.chip_options else {}
        except Exception:
            opts = {}
        changed = False
        if "tags" in chip_fields and not opts.get("tags"):
            opts["tags"] = list(DEFAULT_TAG_OPTIONS)
            changed = True
        if changed:
            frappe.db.set_value("SP Space", sp.name, "chip_options", json.dumps(opts),
                                update_modified=False)
            print(f"  {sp.name}: seeded default tag options")
    frappe.db.commit()
    frappe.clear_cache()
    print("migrate_chip_options done")


def clear_audit():
    """Dev helper: wipe the activity audit (Version field-changes + Comments)
    for every space doctype, so feeds reset to just 'created this task'."""
    doctypes = [s.target_doctype for s in frappe.get_all("SP Space", fields=["target_doctype"])]
    for dt in doctypes:
        frappe.db.delete("Version", {"ref_doctype": dt})
        frappe.db.delete("Comment", {"reference_doctype": dt})
    frappe.db.commit()
    print("cleared audit (Version + Comment) for:", doctypes)


def reset():
    """Drop everything Sprint created (meta doctypes + demo space) for a clean rebuild."""
    for dt in [DEMO_DOCTYPE, "SP View", "SP Bucket", "SP Space"]:
        if frappe.db.exists("DocType", dt):
            frappe.delete_doc("DocType", dt, force=1, ignore_permissions=1)
            frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{dt}`")
            print("dropped", dt)
    frappe.db.commit()
    frappe.clear_cache()


def after_migrate():
    """Registered in hooks.py — keeps the registry schema current on every
    `bench migrate` so fresh benches don't miss additive columns. All the
    ensure_* functions are idempotent."""
    if not frappe.db.exists("DocType", "SP Space"):
        return  # app installed but Sprint not set up yet (run install_all)
    ensure_space_fields()
    ensure_due_and_closed_fields()
    ensure_batch2_meta()
    ensure_automation_meta()
    ensure_dashboard_field()
    ensure_roles()


def install_all():
    cleanup_v1()
    create_meta_doctypes()
    setup_demo()
    print("Sprint install complete.")


def rebuild():
    reset()
    install_all()
