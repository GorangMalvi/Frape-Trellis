"""Access-control and hardening tests for sprint.api.

Uses an ephemeral space (created in setUpClass, dropped in tearDownClass) so
nothing touches real spaces. Run with:
    bench --site <site> run-tests --module sprint.tests.test_api
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sprint import api, setup

SPACE = "ZZ Sprint Test Space"
USER = "sprint-test-user@example.com"
INVITEE = "sprint-invitee@example.com"


class TestSprintApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		if not frappe.db.exists("User", USER):
			frappe.get_doc({
				"doctype": "User",
				"email": USER,
				"first_name": "Sprint Test",
				"send_welcome_email": 0,
				"enabled": 1,
				# this site adds a mandatory custom `manager` field on User
				# (drives the ticket visibility tree)
				"manager": "Administrator",
			}).insert(ignore_permissions=True)
		setup.ensure_space_doctype(SPACE, [
			{"fieldname": "title", "label": "Title", "fieldtype": "Data",
			 "reqd": 1, "in_list_view": 1},
			{"fieldname": "assignee", "label": "Assignee", "fieldtype": "Link",
			 "options": "User"},
		])
		setup.create_space(
			SPACE, label=SPACE, assignee_field="assignee",
			buckets=[{"bucket_name": "Todo"}, {"bucket_name": "Done"}],
		)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		setup.delete_space(SPACE)
		for u in (INVITEE,):
			if frappe.db.exists("User", u):
				frappe.delete_doc("User", u, ignore_permissions=True, force=1)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_value(
			"SP Space", SPACE,
			{"read_access": "All", "write_access": "All"},
			update_modified=False,
		)
		self._drop_role()
		super().tearDown()

	# ---- helpers ----------------------------------------------------------
	def _make_card(self, **kw):
		return api.create_card(SPACE, json.dumps({"title": "test card", **kw}))

	def _restrict_space(self):
		frappe.db.set_value(
			"SP Space", SPACE,
			{"read_access": "Selected Users", "write_access": "Selected Users"},
			update_modified=False,
		)

	def _grant_role(self):
		user = frappe.get_doc("User", USER)
		if not any(r.role == "Sprint Manager" for r in user.roles):
			user.append("roles", {"role": "Sprint Manager"})
			user.save(ignore_permissions=True)

	def _drop_role(self):
		user = frappe.get_doc("User", USER)
		if any(r.role == "Sprint Manager" for r in user.roles):
			user.roles = [r for r in user.roles if r.role != "Sprint Manager"]
			user.save(ignore_permissions=True)

	# ---- access control ----------------------------------------------------
	def test_restricted_space_is_hidden_and_read_blocked(self):
		self._make_card()
		self._restrict_space()
		frappe.set_user(USER)
		self.assertNotIn(SPACE, [s["name"] for s in api.get_spaces()])
		with self.assertRaises(frappe.PermissionError):
			api.get_cards(SPACE)
		# Home must not leak restricted-space cards either
		self.assertFalse([r for r in api.get_my_cards() if r["space"] == SPACE])

	def test_restricted_space_write_blocked(self):
		card = self._make_card()
		self._restrict_space()
		frappe.set_user(USER)
		with self.assertRaises(frappe.PermissionError):
			api.set_field(SPACE, card["name"], "title", "hacked")
		with self.assertRaises(frappe.PermissionError):
			api.create_card(SPACE, json.dumps({"title": "nope"}))

	def test_structural_endpoints_require_manager(self):
		frappe.set_user(USER)
		with self.assertRaises(frappe.PermissionError):
			api.add_bucket(SPACE, "Blocked")
		with self.assertRaises(frappe.PermissionError):
			api.delete_space(SPACE)

	def test_sprint_manager_role_grants_structural_access(self):
		self._grant_role()
		frappe.set_user(USER)
		created = api.add_bucket(SPACE, "Role Bucket")
		self.assertTrue(created["name"])
		frappe.set_user("Administrator")
		frappe.delete_doc("SP Bucket", created["name"], ignore_permissions=True, force=1)

	# ---- hardening ----------------------------------------------------------
	def test_move_card_rejects_foreign_bucket(self):
		card = self._make_card()
		foreign = frappe.get_all("SP Bucket", filters={"space": ["!=", SPACE]}, limit=1)
		if not foreign:
			self.skipTest("no other space on this site")
		with self.assertRaises(frappe.ValidationError):
			api.move_card(SPACE, card["name"], foreign[0].name)

	def test_generic_write_rejects_unknown_fields(self):
		card = self._make_card()
		with self.assertRaises(frappe.ValidationError):
			api.update_card(SPACE, card["name"], json.dumps({"not_a_field": 1}))

	def test_generic_write_strips_system_columns(self):
		card = self._make_card()
		api.update_card(SPACE, card["name"], json.dumps({"owner": "hacker@x.com", "title": "ok"}))
		self.assertNotEqual(frappe.db.get_value(SPACE, card["name"], "owner"), "hacker@x.com")
		self.assertEqual(frappe.db.get_value(SPACE, card["name"], "title"), "ok")

	def test_malformed_json_raises_clean_error(self):
		with self.assertRaises(frappe.ValidationError):
			api.create_card(SPACE, "{not json")

	def test_ticket_server_owned_fields_blocked(self):
		# non-ticket space: requester isn't special, but ticket guard fields
		# must never pass through the generic clean on a ticket space; here we
		# just prove _clean_card_values rejects unknown fields consistently.
		reg = frappe.get_doc("SP Space", SPACE)
		cleaned = api._clean_card_values(reg, {"title": "x", "owner": "y"})
		self.assertEqual(cleaned, {"title": "x"})

	# ---- auth + user administration ----------------------------------------
	def _cleanup_invitee(self):
		if frappe.db.exists("User", INVITEE):
			frappe.delete_doc("User", INVITEE, ignore_permissions=True, force=1)

	def test_boot_reports_current_session(self):
		boot = api.boot()
		self.assertEqual(boot["user"], "Administrator")
		self.assertTrue(boot["csrf_token"])
		self.assertTrue(boot["can_manage"])

	def test_user_admin_endpoints_require_manager(self):
		frappe.set_user(USER)
		for call in (
			lambda: api.list_users(),
			lambda: api.invite_user("x@example.com"),
			lambda: api.set_user_role(USER, 1),
			lambda: api.set_user_enabled(USER, 0),
			lambda: api.send_user_reset(USER),
		):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_list_users_shape_and_manager_flag(self):
		self._grant_role()
		rows = {r["name"]: r for r in api.list_users()}
		self.assertIn(USER, rows)
		self.assertNotIn("Guest", rows)
		self.assertTrue(rows[USER]["is_manager"])
		self.assertTrue(rows["Administrator"]["is_admin"])

	def test_invite_user_creates_user_with_app_link(self):
		self._cleanup_invitee()
		try:
			res = api.invite_user(INVITEE, full_name="New Invitee", manager="Administrator")
			self.assertEqual(res["user"], INVITEE)
			self.assertTrue(res["invite_url"].startswith("/sprint/update-password?"))
			self.assertTrue(frappe.db.exists("User", INVITEE))
			self.assertEqual(frappe.db.get_value("User", INVITEE, "enabled"), 1)
		finally:
			self._cleanup_invitee()

	def test_invite_rejects_duplicate_and_bad_email(self):
		with self.assertRaises(frappe.ValidationError):
			api.invite_user("not-an-email")
		with self.assertRaises(frappe.ValidationError):
			api.invite_user(USER)  # already exists

	def test_set_user_role_toggles_manager(self):
		self._drop_role()
		api.set_user_role(USER, 1)
		self.assertIn("Sprint Manager", frappe.get_roles(USER))
		api.set_user_role(USER, 0)
		frappe.clear_cache(user=USER)
		self.assertNotIn("Sprint Manager", frappe.get_roles(USER))

	def test_cannot_disable_self_or_administrator(self):
		with self.assertRaises(frappe.ValidationError):
			api.set_user_enabled("Administrator", 0)
		with self.assertRaises(frappe.ValidationError):
			api.set_user_enabled(frappe.session.user, 0)

	def test_set_user_enabled_toggles_other(self):
		api.set_user_enabled(USER, 0)
		self.assertEqual(frappe.db.get_value("User", USER, "enabled"), 0)
		api.set_user_enabled(USER, 1)
		self.assertEqual(frappe.db.get_value("User", USER, "enabled"), 1)

	def test_request_password_reset_is_generic(self):
		# never raises + never reveals existence, for known or unknown emails
		self.assertEqual(api.request_password_reset(USER), {"ok": True})
		self.assertEqual(api.request_password_reset("nobody@nowhere.example"), {"ok": True})

	def test_change_my_password_rejects_wrong_old(self):
		frappe.set_user(USER)
		with self.assertRaises(frappe.ValidationError):
			api.change_my_password("definitely-wrong", "NewPassw0rd!")

	def test_account_profile_is_self_scoped(self):
		frappe.set_user(USER)
		prof = api.get_my_profile()
		self.assertEqual(prof["user"], USER)
