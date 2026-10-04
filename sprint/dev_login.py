"""Passwordless login for LOCAL DEVELOPMENT only.

Enter an email in the SPA → a 6-digit code and a one-click login link are
printed to the server's terminal (`docker compose logs -f frappe`) instead of
being emailed. Both are single-use and expire after 10 minutes.

Enabled only when the site config has BOTH `developer_mode` and
`sprint_dev_login` set (the Docker dev stack sets them; production never does).
Every endpoint refuses to run otherwise, so this can't leak into production.
"""

import secrets
from urllib.parse import quote

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

TTL_SECONDS = 10 * 60
MAX_ATTEMPTS = 5


def is_enabled():
	return bool(cint(frappe.conf.get("developer_mode")) and cint(frappe.conf.get("sprint_dev_login")))


def _require_enabled():
	if not is_enabled():
		frappe.throw(_("Dev login is not enabled on this site."), frappe.PermissionError)


def _code_key(user):
	return f"sprint_dev_login:code:{user}"


def _link_key(token):
	return f"sprint_dev_login:link:{token}"


def _resolve_user(login_id):
	"""Email or username → an enabled, non-Guest User name (or None)."""
	login_id = (login_id or "").strip()
	if not login_id:
		return None
	user = frappe.db.get_value("User", {"email": login_id}, "name") or (
		login_id if frappe.db.exists("User", login_id) else None
	)
	if not user or user == "Guest" or not cint(frappe.db.get_value("User", user, "enabled")):
		return None
	return user


def _login_as(user):
	frappe.local.login_manager.login_as(user)


def _safe_redirect(path):
	"""Only same-app paths: '/sprint/…'. Anything else → the app root."""
	path = path or ""
	if path.startswith("/sprint") and not path.startswith("//"):
		return path
	return "/sprint/"


def _print_to_terminal(user, code, link):
	bar = "=" * 64
	print(
		f"\n{bar}\n"
		f"  SPRINT DEV LOGIN  (local development only)\n"
		f"  user : {user}\n"
		f"  code : {code}      valid {TTL_SECONDS // 60} min, single use\n"
		f"  link : {link}\n"
		f"{bar}\n",
		flush=True,
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60)
def request_code(email, redirect=None):
	"""Print a login code + link for `email` to the server terminal.

	Same response whether or not the user exists (no enumeration), even in dev."""
	_require_enabled()
	user = _resolve_user(email)
	if user:
		code = f"{secrets.randbelow(10**6):06d}"
		token = secrets.token_urlsafe(32)
		frappe.cache.set_value(_code_key(user), {"code": code, "attempts": 0}, expires_in_sec=TTL_SECONDS)
		frappe.cache.set_value(_link_key(token), user, expires_in_sec=TTL_SECONDS)
		# the host the browser used (:8000, or :8080 via the Vite proxy)
		request = getattr(frappe.local, "request", None)
		host = request.host_url.rstrip("/") if request else frappe.utils.get_url()
		link = (
			f"{host}/api/method/sprint.dev_login.login_with_link"
			f"?token={token}&redirect={quote(_safe_redirect(redirect))}"
		)
		_print_to_terminal(user, code, link)
	else:
		print(f"[sprint dev login] no enabled user matches {email!r}; nothing sent", flush=True)
	return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60)
def verify_code(email, code):
	"""Log in with the 6-digit code printed by request_code."""
	_require_enabled()
	user = _resolve_user(email)
	entry = frappe.cache.get_value(_code_key(user)) if user else None
	if not entry:
		frappe.throw(_("No active code for this email. Request a new one."), frappe.AuthenticationError)
	if not secrets.compare_digest(str(entry["code"]), str(code or "").strip()):
		entry["attempts"] += 1
		if entry["attempts"] >= MAX_ATTEMPTS:
			frappe.cache.delete_value(_code_key(user))
			frappe.throw(_("Too many wrong codes. Request a new one."), frappe.AuthenticationError)
		frappe.cache.set_value(_code_key(user), entry, expires_in_sec=TTL_SECONDS)
		frappe.throw(_("That code is not right."), frappe.AuthenticationError)
	frappe.cache.delete_value(_code_key(user))
	_login_as(user)
	return {"ok": True, "user": user}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=10, seconds=60)
def login_with_link(token, redirect=None):
	"""One-click login from the link printed by request_code."""
	_require_enabled()
	user = frappe.cache.get_value(_link_key(token)) if token else None
	frappe.local.response["type"] = "redirect"
	if not user:
		frappe.local.response["location"] = "/sprint/login?dev_link=expired"
		return
	frappe.cache.delete_value(_link_key(token))
	frappe.cache.delete_value(_code_key(user))
	_login_as(user)
	frappe.local.response["location"] = _safe_redirect(redirect)
