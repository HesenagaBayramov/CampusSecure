"""Behavior tests using an isolated SQLite database for each case."""

import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from flask import abort
from jinja2 import StrictUndefined
from werkzeug.security import check_password_hash

from app import create_app
from app.db import get_db, reset_db, seed_db


class CampusSecureTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATABASE": os.path.join(self.directory.name, "test.sqlite3"),
            "LAB_MODE": "secure",
        })
        with self.app.app_context():
            seed_db()
        self.client = self.app.test_client()

    def tearDown(self):
        self.directory.cleanup()

    def token(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, username, password):
        self.client.get("/login")
        return self.client.post("/login", data={
            "username": username, "password": password, "csrf_token": self.token()
        })

    def post(self, path, data=None):
        payload = dict(data or {})
        payload["csrf_token"] = self.token()
        return self.client.post(path, data=payload)

    def test_seed_is_idempotent_and_passwords_are_hashed(self):
        with self.app.app_context():
            seed_db()
            users = get_db().execute("SELECT username, password_hash FROM users ORDER BY id").fetchall()
            self.assertEqual([row["username"] for row in users], ["alice", "bob", "admin"])
            self.assertEqual(len(get_db().execute("SELECT id FROM academic_requests").fetchall()), 2)
            self.assertNotEqual(users[0]["password_hash"], "Student123!")
            self.assertTrue(check_password_hash(users[0]["password_hash"], "Student123!"))
            self.assertTrue(check_password_hash(users[2]["password_hash"], "Admin123!"))

    def test_login_logout_and_wrong_password(self):
        bad = self.login("alice", "wrong")
        self.assertEqual(bad.status_code, 200)
        self.assertIn(b"Invalid username or password", bad.data)
        good = self.login("alice", "Student123!")
        self.assertEqual(good.status_code, 302)
        self.assertEqual(good.headers["Location"], "/student/dashboard")
        self.assertEqual(self.client.get("/student/dashboard").status_code, 200)
        self.assertEqual(self.post("/logout").status_code, 302)
        self.assertEqual(self.client.get("/student/dashboard").status_code, 302)

    def test_protected_routes_and_role_boundaries(self):
        for path in ("/student/dashboard", "/student/profile", "/student/requests", "/admin/dashboard", "/admin/announcements"):
            self.assertEqual(self.client.get(path).status_code, 302)
        self.login("alice", "Student123!")
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 403)
        self.assertEqual(self.client.get("/admin/announcements").status_code, 403)
        self.assertEqual(self.post("/admin/announcements", {"title": "Blocked", "body": "Blocked"}).status_code, 403)
        with self.app.app_context():
            self.assertIsNone(get_db().execute("SELECT id FROM announcements WHERE title = 'Blocked'").fetchone())
        self.post("/logout")
        self.login("admin", "Admin123!")
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 200)
        self.assertEqual(self.client.get("/student/profile").status_code, 403)

    def test_request_ownership_and_profile_update(self):
        self.login("alice", "Student123!")
        self.assertEqual(self.client.get("/student/requests/101").status_code, 200)
        self.assertEqual(self.client.get("/student/requests/201").status_code, 404)
        response = self.client.get("/student/requests")
        self.assertIn(b"101", response.data)
        self.assertNotIn(b'href="/student/requests/201"', response.data)
        changed = self.post("/student/profile", {
            "full_name": "Alice Example", "email": "alice.new@example.test", "phone": "555 0199",
            "user_id": "2", "role": "admin", "department": "Changed",
        })
        self.assertEqual(changed.status_code, 302)
        with self.app.app_context():
            alice = get_db().execute("SELECT * FROM student_profiles WHERE user_id = 1").fetchone()
            bob = get_db().execute("SELECT * FROM student_profiles WHERE user_id = 2").fetchone()
            self.assertEqual(alice["full_name"], "Alice Example")
            self.assertEqual(alice["department"], "Computer Science")
            self.assertEqual(bob["full_name"], "Bob Rivera")
        self.post("/logout")
        self.login("bob", "Student123!")
        self.assertEqual(self.client.get("/student/requests/101").status_code, 404)
        self.assertEqual(self.client.get("/student/requests/201").status_code, 200)

    def test_admin_announcement_crud_and_csrf(self):
        self.login("admin", "Admin123!")
        self.assertEqual(self.client.post("/admin/announcements", data={"title": "No token", "body": "Denied"}).status_code, 400)
        created = self.post("/admin/announcements", {"title": "Test notice", "body": "Original body"})
        self.assertEqual(created.status_code, 302)
        with self.app.app_context():
            row = get_db().execute("SELECT id FROM announcements WHERE title = ?", ("Test notice",)).fetchone()
            announcement_id = row["id"]
        edited = self.post(f"/admin/announcements/{announcement_id}/edit", {
            "title": "Updated notice", "body": "Updated body"
        })
        self.assertEqual(edited.status_code, 302)
        self.assertIn(b"Updated notice", self.client.get("/admin/announcements").data)
        self.assertEqual(self.post(f"/admin/announcements/{announcement_id}/delete").status_code, 302)
        with self.app.app_context():
            self.assertIsNone(get_db().execute("SELECT id FROM announcements WHERE id = ?", (announcement_id,)).fetchone())

    def test_admin_approves_pending_request_and_student_sees_result(self):
        self.login("admin", "Admin123!")
        self.assertIn(b'href="/admin/requests"', self.client.get("/admin/dashboard").data)
        listing = self.client.get("/admin/requests")
        self.assertEqual(listing.status_code, 200)
        self.assertIn(b"Alice Carter", listing.data)
        self.assertIn(b"Bob Rivera", listing.data)
        self.assertIn(b"#101", listing.data)
        self.assertIn(b"#201", listing.data)
        self.assertIn(b"Transcript", listing.data)
        self.assertIn(b"2026-09-10", listing.data)
        self.assertIn(b"Pending", listing.data)
        self.assertIn(b"Approved", listing.data)
        detail = self.client.get("/admin/requests/101")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"scholarship application", detail.data)
        self.assertGreaterEqual(detail.data.count(b'name="csrf_token"'), 3)
        self.assertEqual(
            self.client.post("/admin/requests/101/status", data={"decision": "approve"}).status_code,
            400,
        )
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0], "pending")
        changed = self.post("/admin/requests/101/status", {"decision": "approve"})
        self.assertEqual(changed.status_code, 302)
        with self.app.app_context():
            status = get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0]
            self.assertEqual(status, "approved")
        self.assertIn(b"Approved", self.client.get("/admin/requests/101").data)
        self.assertEqual(self.post("/admin/requests/101/status", {"decision": "reject"}).status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0], "approved")
        self.post("/logout")
        self.login("alice", "Student123!")
        self.assertIn(b"Approved", self.client.get("/student/requests/101").data)
        self.assertIn(b"Approved", self.client.get("/student/requests").data)

    def test_admin_rejects_pending_request_and_bob_sees_result(self):
        with self.app.app_context():
            get_db().execute(
                "INSERT INTO academic_requests (id, student_id, request_type, details, status, submitted_on) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (202, 2, "Course appeal", "Review a fictional course decision.", "pending", "2026-09-12"),
            )
            get_db().commit()
        self.login("admin", "Admin123!")
        self.assertIn(b"Course appeal", self.client.get("/admin/requests/202").data)
        rejected = self.post("/admin/requests/202/status", {"decision": "reject"})
        self.assertEqual(rejected.status_code, 302)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 202").fetchone()[0], "rejected")
        self.post("/logout")
        self.login("bob", "Student123!")
        self.assertIn(b"Rejected", self.client.get("/student/requests/202").data)

    def test_student_cannot_manage_requests_or_change_status(self):
        self.login("alice", "Student123!")
        self.client.get("/student/requests")
        self.assertEqual(self.client.get("/admin/requests").status_code, 403)
        self.assertEqual(self.client.get("/admin/requests/101").status_code, 403)
        self.assertEqual(self.post("/admin/requests/101/status", {"decision": "approve"}).status_code, 403)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0], "pending")
        self.assertEqual(self.client.get("/student/requests/201").status_code, 404)

    def test_request_status_rejects_invalid_decisions_and_unknown_ids(self):
        self.login("admin", "Admin123!")
        self.client.get("/admin/requests")
        self.assertEqual(self.post("/admin/requests/101/status", {"decision": "pending"}).status_code, 400)
        self.assertEqual(self.post("/admin/requests/999/status", {"decision": "approve"}).status_code, 404)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0], "pending")

    def test_reset_restores_original_data_and_credentials(self):
        with self.app.app_context():
            get_db().execute("UPDATE student_profiles SET full_name = 'Changed' WHERE user_id = 1")
            get_db().execute("UPDATE academic_requests SET status = 'rejected' WHERE id = 101")
            get_db().execute("UPDATE academic_requests SET status = 'rejected' WHERE id = 201")
            get_db().execute("DELETE FROM academic_requests WHERE id = 201")
            get_db().commit()
            reset_db()
            self.assertEqual(get_db().execute("SELECT full_name FROM student_profiles WHERE user_id = 1").fetchone()[0], "Alice Carter")
            self.assertEqual(get_db().execute("SELECT student_id FROM academic_requests WHERE id = 201").fetchone()[0], 2)
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 101").fetchone()[0], "pending")
            self.assertEqual(get_db().execute("SELECT status FROM academic_requests WHERE id = 201").fetchone()[0], "approved")
            hashed = get_db().execute("SELECT password_hash FROM users WHERE username = 'alice'").fetchone()[0]
            self.assertTrue(check_password_hash(hashed, "Student123!"))

    def test_reset_script_restores_original_request_statuses(self):
        database = os.path.join(self.directory.name, "script-reset.sqlite3")
        environment = os.environ.copy()
        environment["CAMPUSSECURE_DATABASE"] = database
        environment["LAB_MODE"] = "secure"
        project_root = Path(__file__).resolve().parents[1]
        for command in ("seed_db", "reset_db"):
            if command == "reset_db":
                with closing(sqlite3.connect(database)) as connection:
                    with connection:
                        connection.execute("UPDATE academic_requests SET status = 'rejected'")
            result = subprocess.run(
                [sys.executable, "-m", f"scripts.{command}"],
                cwd=project_root, env=environment, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        with closing(sqlite3.connect(database)) as connection:
            statuses = connection.execute(
                "SELECT id, status FROM academic_requests ORDER BY id"
            ).fetchall()
        self.assertEqual(statuses, [(101, "pending"), (201, "approved")])

    def test_html_routes_remain_secure_after_config_mutation(self):
        self.app.config["LAB_MODE"] = "vulnerable"
        self.login("alice", "Student123!")
        self.assertEqual(self.client.get("/student/requests/201").status_code, 404)
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 403)
        self.assertEqual(self.client.get("/admin/requests").status_code, 403)

    def test_stage_two_pages_render_with_local_assets(self):
        self.app.jinja_env.undefined = StrictUndefined
        pages = [("/login", b"Sign in to your account")]
        self.login("alice", "Student123!")
        pages.extend([
            ("/student/dashboard", b"Alice Carter"),
            ("/student/profile", b"alice@example.test"),
            ("/student/requests", b"Transcript"),
            ("/student/requests/101", b"scholarship application"),
        ])
        asset_paths = set()
        for path, expected in pages[1:]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(expected, response.data)
            self.assertNotIn(b'href="/admin', response.data)
            asset_paths.update(re.findall(rb'(?:href|src)="(/static/[^"#]+)', response.data))
        self.post("/logout")
        login_page = self.client.get(pages[0][0])
        self.assertEqual(login_page.status_code, 200)
        self.assertIn(pages[0][1], login_page.data)
        asset_paths.update(re.findall(rb'(?:href|src)="(/static/[^"#]+)', login_page.data))
        self.login("admin", "Admin123!")
        for path, expected in (
            ("/admin/dashboard", b"Student overview"),
            ("/admin/requests", b"Alice Carter"),
            ("/admin/requests/101", b"Approve request"),
            ("/admin/announcements", b"Create announcement"),
            ("/admin/announcements/1/edit", b"Welcome to the autumn term"),
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(expected, response.data)
            self.assertNotIn(b'href="/student', response.data)
            asset_paths.update(re.findall(rb'(?:href|src)="(/static/[^"#]+)', response.data))
        self.assertIn(b"/static/css/portal.css", asset_paths)
        self.assertIn(b"/static/vendor/bootstrap/css/bootstrap.min.css", asset_paths)
        self.assertIn(b"/static/vendor/bootstrap/js/bootstrap.bundle.min.js", asset_paths)
        for path in asset_paths:
            asset = self.client.get(path.decode())
            self.assertEqual(asset.status_code, 200, path)
            asset.close()

    def test_form_feedback_keeps_entered_values(self):
        self.login("alice", "Student123!")
        self.client.get("/student/profile")
        profile = self.post("/student/profile", {
            "full_name": "", "email": "attempt@example.test", "phone": "555 0123"
        })
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"Enter a name and email", profile.data)
        self.assertIn(b'attempt@example.test', profile.data)
        self.post("/logout")
        self.login("admin", "Admin123!")
        self.client.get("/admin/announcements")
        announcement = self.post("/admin/announcements", {"title": "Draft title", "body": ""})
        self.assertEqual(announcement.status_code, 200)
        self.assertIn(b"Draft title", announcement.data)
        self.assertIn(b"Title and body are required", announcement.data)

    def test_custom_error_pages(self):
        self.assertIn(b"Page not found", self.client.get("/missing-page").data)
        self.login("alice", "Student123!")
        forbidden = self.client.get("/admin/dashboard")
        self.assertEqual(forbidden.status_code, 403)
        self.assertIn(b"Access restricted", forbidden.data)
        missing_request = self.client.get("/student/requests/201")
        self.assertEqual(missing_request.status_code, 404)
        self.assertIn(b"Page not found", missing_request.data)
        isolated = create_app({"TESTING": False, "SECRET_KEY": "test-only-secret", "DATABASE": os.path.join(self.directory.name, "test.sqlite3")})

        @isolated.get("/forced-error")
        def forced_error():
            abort(500)

        failed = isolated.test_client().get("/forced-error")
        self.assertEqual(failed.status_code, 500)
        self.assertIn(b"Something went wrong", failed.data)


if __name__ == "__main__":
    unittest.main()
