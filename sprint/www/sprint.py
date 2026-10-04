import frappe
from frappe.utils import cint, get_system_timezone

no_cache = 1


def get_context(context):
	# Sprint renders its own in-app login (B2B white-label), so we serve the SPA
	# to guests too — the Vue router guard shows the login screen when the boot
	# user is "Guest". No bounce to Frappe Desk's native /login.
	context.boot = get_boot()
	context.no_cache = 1
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw("This method is only meant for developer mode")
	return get_boot()


def _boot_can_manage():
	from sprint.api import _is_manager

	return frappe.session.user != "Guest" and _is_manager()


def _boot_dev_login():
	from sprint.dev_login import is_enabled

	return is_enabled()


def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/sprint",
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
			# Administrator OR the "Sprint Manager" role — mirrors api._is_manager
			# so the in-app User admin page gates correctly before any space loads.
			"can_manage": _boot_can_manage(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			# local development only: login code/link printed to the terminal
			"dev_login": _boot_dev_login(),
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)
