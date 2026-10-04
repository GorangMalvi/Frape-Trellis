"""Local-development passwordless login (sprint.dev_login).

Run with:
    bench --site <site> run-tests --module sprint.tests.test_dev_login
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sprint import dev_login

ON = {"developer_mode": 1, "sprint_dev_login": 1}


class TestDevLogin(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Guest")
		self.printed = []
		self.logged_in = []
		patches = [
			patch.object(dev_login, "_print_to_terminal", lambda u, c, l: self.printed.append((u, c, l))),
			patch.object(dev_login, "_login_as", lambda u: self.logged_in.append(u)),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		frappe.cache.delete_value(dev_login._code_key("Administrator"))

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _request(self):
		with patch.dict(frappe.conf, ON):
			dev_login.request_code("Administrator")
		return self.printed[-1]

	def test_disabled_without_both_flags(self):
		for conf in ({}, {"developer_mode": 1}, {"sprint_dev_login": 1}, {"developer_mode": 0, "sprint_dev_login": 1}):
			with patch.dict(frappe.conf, {"developer_mode": 0, "sprint_dev_login": 0, **conf}):
				self.assertFalse(dev_login.is_enabled())
				with self.assertRaises(frappe.PermissionError):
					dev_login.request_code("Administrator")
				with self.assertRaises(frappe.PermissionError):
					dev_login.verify_code("Administrator", "000000")
				with self.assertRaises(frappe.PermissionError):
					dev_login.login_with_link("x")
		self.assertEqual(self.printed, [])
		self.assertEqual(self.logged_in, [])

	def test_code_logs_in_once(self):
		user, code, link = self._request()
		self.assertEqual(user, "Administrator")
		self.assertRegex(code, r"^\d{6}$")
		self.assertIn("/api/method/sprint.dev_login.login_with_link?token=", link)
		with patch.dict(frappe.conf, ON):
			self.assertEqual(dev_login.verify_code("Administrator", code)["user"], "Administrator")
			self.assertEqual(self.logged_in, ["Administrator"])
			with self.assertRaises(frappe.AuthenticationError):  # single use
				dev_login.verify_code("Administrator", code)

	def test_wrong_codes_burn_the_code(self):
		_, code, _ = self._request()
		wrong = f"{(int(code) + 1) % 10**6:06d}"
		with patch.dict(frappe.conf, ON):
			for _ in range(dev_login.MAX_ATTEMPTS):
				with self.assertRaises(frappe.AuthenticationError):
					dev_login.verify_code("Administrator", wrong)
			with self.assertRaises(frappe.AuthenticationError):  # the right code is gone too
				dev_login.verify_code("Administrator", code)
		self.assertEqual(self.logged_in, [])

	def test_link_logs_in_once_and_redirects_safely(self):
		_, _, link = self._request()
		token = link.split("token=", 1)[1].split("&", 1)[0]
		with patch.dict(frappe.conf, ON):
			dev_login.login_with_link(token, redirect="https://evil.example/")
			self.assertEqual(self.logged_in, ["Administrator"])
			self.assertEqual(frappe.local.response["location"], "/sprint/")
			dev_login.login_with_link(token)  # single use
			self.assertEqual(frappe.local.response["location"], "/sprint/login?dev_link=expired")
		self.assertEqual(self.logged_in, ["Administrator"])

	def test_frappe_login_page_link_goes_to_desk(self):
		with patch.dict(frappe.conf, ON):
			dev_login.send_login_link("admin@example.com")  # Administrator's email
		user, _, link = self.printed[-1]
		self.assertEqual(user, "Administrator")
		self.assertIn("redirect=/desk", link)
		token = link.split("token=", 1)[1].split("&", 1)[0]
		with patch.dict(frappe.conf, ON):
			dev_login.login_with_link(token, redirect="/desk")
		self.assertEqual(self.logged_in, ["Administrator"])
		self.assertEqual(frappe.local.response["location"], "/desk")

	def test_frappe_login_page_delegates_when_disabled(self):
		with patch.dict(frappe.conf, {"developer_mode": 0, "sprint_dev_login": 0}):
			with patch("frappe.www.login.send_login_link") as original:
				dev_login.send_login_link("admin@example.com")
		original.assert_called_once_with("admin@example.com")
		self.assertEqual(self.printed, [])

	def test_unknown_user_prints_nothing(self):
		with patch.dict(frappe.conf, ON):
			self.assertEqual(dev_login.request_code("nobody@example.com"), {"ok": True})
			with self.assertRaises(frappe.AuthenticationError):
				dev_login.verify_code("nobody@example.com", "123456")
		self.assertEqual(self.printed, [])
