"""Automation engine tests — matcher, dispatch, guards, scheduling.

Ephemeral space (setUpClass/tearDownClass) so nothing touches real spaces.
    bench --site <site> run-tests --module sprint.tests.test_automation
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sprint import api, automation, setup

SPACE = "ZZ Automation Test Space"


class TestAutomation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		setup.ensure_space_doctype(SPACE, [
			{"fieldname": "title", "label": "Title", "fieldtype": "Data",
			 "reqd": 1, "in_list_view": 1},
			{"fieldname": "assignee", "label": "Assignee", "fieldtype": "Link",
			 "options": "User"},
			{"fieldname": "priority", "label": "Priority", "fieldtype": "Select",
			 "options": "Low\nHigh"},
		])
		setup.create_space(
			SPACE, label=SPACE, assignee_field="assignee",
			buckets=[{"bucket_name": "Todo"}, {"bucket_name": "Doing"}, {"bucket_name": "Done"}],
		)
		frappe.db.commit()
		cls.buckets = {
			b.bucket_name: b.name
			for b in frappe.get_all("SP Bucket", filters={"space": SPACE},
			                        fields=["name", "bucket_name"])
		}

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		setup.delete_space(SPACE)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		for r in frappe.get_all("SP Automation", filters={"space": SPACE}):
			frappe.delete_doc("SP Automation", r.name, force=1, ignore_permissions=1)
		frappe.db.delete("SP Automation Run", {"space": SPACE})
		for c in frappe.get_all(SPACE):
			frappe.delete_doc(SPACE, c.name, force=1, ignore_permissions=1)
		self._reset_request_caches()
		frappe.db.commit()

	def _reset_request_caches(self):
		for attr in ("_sprint_automation_seen", "_sprint_quota", "_sprint_rules",
		             "_sprint_automation_depth", "_sprint_automation_ready"):
			if hasattr(frappe.local, attr):
				delattr(frappe.local, attr)

	def _rule(self, name, trigger_type, actions, trigger_config=None, conditions=None):
		return automation.save_automation(
			SPACE, name, trigger_type,
			trigger_config=json.dumps(trigger_config or {}),
			conditions=json.dumps(conditions or []),
			actions=json.dumps(actions),
		)

	def _card(self, **kw):
		return api.create_card(SPACE, json.dumps({"title": "card", **kw}))

	# ---- matcher (mirrors board.js) ---------------------------------------
	def test_match_conditions_operators(self):
		card = {"priority": "High", "tags": "bug,seo", "blank": ""}
		cases = [
			([{"field": "priority", "operator": "is", "value": "High"}], True),
			([{"field": "priority", "operator": "is", "value": "Low"}], False),
			([{"field": "priority", "operator": "is not", "value": "Low"}], True),
			([{"field": "priority", "operator": "is any of", "value": ["Low", "High"]}], True),
			([{"field": "priority", "operator": "is any of", "value": []}], True),
			([{"field": "priority", "operator": "is none of", "value": ["High"]}], False),
			([{"field": "tags", "operator": "contains", "value": "BUG"}], True),
			([{"field": "blank", "operator": "is empty", "value": None}], True),
			([{"field": "priority", "operator": "is set", "value": None}], True),
			([{"field": "", "operator": "is", "value": "x"}], True),
		]
		for conds, expected in cases:
			self.assertEqual(automation.match_conditions(card, conds), expected, conds)

	# ---- event dispatch ---------------------------------------------------
	def test_card_created_fires_and_logs_run(self):
		self._rule("greet", "card_created",
		           [{"type": "add_comment", "message": "welcome {title}"}])
		self._reset_request_caches()
		card = self._card(title="hello")
		frappe.db.commit()
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": SPACE, "reference_name": card["name"],
			"comment_type": "Comment"}, pluck="content")
		self.assertTrue(any("welcome hello" in (c or "") for c in comments))
		runs = frappe.get_all("SP Automation Run",
		                      filters={"space": SPACE}, fields=["status"])
		self.assertEqual(len(runs), 1)
		self.assertEqual(runs[0].status, "Success")

	def test_conditions_gate_execution(self):
		self._rule("only high", "card_created",
		           [{"type": "add_comment", "message": "hi"}],
		           conditions=[{"field": "priority", "operator": "is", "value": "High"}])
		self._reset_request_caches()
		self._card(title="low one", priority="Low")
		frappe.db.commit()
		# condition miss → no run logged (v1: non-matches aren't logged)
		self.assertEqual(frappe.db.count("SP Automation Run", {"space": SPACE}), 0)

	def test_moved_to_bucket_specific(self):
		self._rule("on done", "moved_to_bucket",
		           [{"type": "add_comment", "message": "done"}],
		           trigger_config={"bucket": self.buckets["Done"]})
		self._reset_request_caches()
		card = self._card(title="mover", bucket=self.buckets["Todo"])
		frappe.db.commit()
		self._reset_request_caches()
		api.set_field(SPACE, card["name"], "bucket", self.buckets["Doing"])
		frappe.db.commit()
		self.assertEqual(frappe.db.count("SP Automation Run", {"space": SPACE}), 0)  # wrong bucket
		self._reset_request_caches()
		api.set_field(SPACE, card["name"], "bucket", self.buckets["Done"])
		frappe.db.commit()
		self.assertEqual(frappe.db.count("SP Automation Run", {"space": SPACE}), 1)

	# ---- guards ------------------------------------------------------------
	def test_loop_guard_bounds_cascade(self):
		self._rule("toDoing", "moved_to_bucket",
		           [{"type": "move_to_bucket", "bucket": self.buckets["Doing"]}],
		           trigger_config={"bucket": self.buckets["Todo"]})
		self._rule("toTodo", "moved_to_bucket",
		           [{"type": "move_to_bucket", "bucket": self.buckets["Todo"]}],
		           trigger_config={"bucket": self.buckets["Doing"]})
		self._reset_request_caches()
		card = self._card(title="loop", bucket=self.buckets["Done"])
		frappe.db.commit()
		self._reset_request_caches()
		api.set_field(SPACE, card["name"], "bucket", self.buckets["Todo"])
		frappe.db.commit()
		# depth-bounded: at most MAX_DEPTH cascaded runs, and it terminates
		runs = frappe.db.count("SP Automation Run", {"space": SPACE, "status": ["!=", "Skipped"]})
		self.assertLessEqual(runs, automation.MAX_DEPTH)
		self.assertIn(frappe.db.get_value(SPACE, card["name"], "bucket"),
		              (self.buckets["Todo"], self.buckets["Doing"]))

	def test_quota_caps_and_logs_one_skip(self):
		frappe.conf["sprint_automation_daily_quota"] = 3
		try:
			self._rule("greet", "card_created",
			           [{"type": "add_comment", "message": "hi"}])
			for i in range(5):
				self._reset_request_caches()
				self._card(title=f"q{i}")
				frappe.db.commit()
			self.assertEqual(frappe.db.count("SP Automation Run",
			                                 {"space": SPACE, "status": "Success"}), 3)
			self.assertEqual(frappe.db.count("SP Automation Run",
			                                 {"space": SPACE, "status": "Skipped"}), 1)
		finally:
			frappe.conf.pop("sprint_automation_daily_quota", None)

	# ---- scheduling --------------------------------------------------------
	def test_compute_next_run_presets(self):
		from datetime import datetime
		after = datetime(2026, 3, 4, 10, 0, 0)  # a Wednesday
		daily = automation.compute_next_run({"frequency": "daily", "time": "09:00"}, after=after)
		self.assertEqual((daily.hour, daily.minute), (9, 0))
		self.assertGreater(daily, after)
		weekly = automation.compute_next_run(
			{"frequency": "weekly", "weekday": 0, "time": "09:00"}, after=after)
		self.assertEqual(weekly.weekday(), 0)
		self.assertGreater(weekly, after)
		monthly = automation.compute_next_run(
			{"frequency": "monthly", "day_of_month": 1, "time": "09:00"}, after=after)
		self.assertEqual(monthly.day, 1)
		self.assertGreater(monthly, after)

	# ---- validation --------------------------------------------------------
	def test_save_rejects_bad_definition(self):
		with self.assertRaises(frappe.ValidationError):
			self._rule("bad field", "field_changed",
			           [{"type": "add_comment", "message": "x"}],
			           trigger_config={"field": "does_not_exist"})
		with self.assertRaises(frappe.ValidationError):
			self._rule("bad webhook", "card_created",
			           [{"type": "webhook", "url": "http://169.254.169.254/"}])

	def test_dry_run_writes_nothing(self):
		rule = self._rule("dry", "card_created",
		                  [{"type": "add_comment", "message": "hi {title}"}])
		card = self._card(title="dryprobe")
		frappe.db.commit()
		before = frappe.db.count("SP Automation Run")
		report = automation.run_automation_test(rule["name"], card["name"])
		self.assertTrue(report["trigger_would_match"])
		self.assertEqual(frappe.db.count("SP Automation Run"), before)

	def test_non_manager_cannot_save(self):
		user = "auto-test-nonmgr@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "NM",
			                "send_welcome_email": 0, "manager": "Administrator"}).insert(ignore_permissions=True)
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				self._rule("nope", "card_created", [{"type": "add_comment", "message": "x"}])
		finally:
			frappe.set_user("Administrator")
