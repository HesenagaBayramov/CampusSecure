"""Focused comparisons for the three deliberately scoped lab scenarios."""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from app.db import get_db, reset_db, seed_db
from run import selected_host


class LabModeTest(unittest.TestCase):
    def make_lab(self, mode):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "isolated-lab-test-key",
            "DATABASE": os.path.join(directory.name, "campussecure.sqlite3"),
            "LAB_MODE": mode,
        })
        with app.app_context():
            seed_db()
        return app, app.test_client()

    def login(self, client, username, password):
        client.get("/login")
        with client.session_transaction() as session:
            token = session["csrf_token"]
        result = client.post("/login", data={
            "username": username, "password": password, "csrf_token": token,
        })
        self.assertEqual(result.status_code, 302)
        client.get(result.headers["Location"])

    @staticmethod
    def csrf_headers(client):
        with client.session_transaction() as session:
            return {"X-CSRF-Token": session["csrf_token"]}

    def test_mode_selection_is_captured_at_factory_startup(self):
        for mode in ("secure", "vulnerable"):
            with self.subTest(mode=mode):
                directory = tempfile.TemporaryDirectory()
                self.addCleanup(directory.cleanup)
                with patch.dict(os.environ, {
                    "LAB_MODE": mode,
                    "CAMPUSSECURE_DATABASE": os.path.join(directory.name, "environment.sqlite3"),
                }):
                    app = create_app()
                with app.app_context():
                    seed_db()
                client = app.test_client()
                self.assertEqual(app.extensions["campussecure_lab_mode"], mode)
                self.assertEqual(client.get("/login").status_code, 200)
        app, client = self.make_lab("secure")
        self.login(client, "alice", "Student123!")
        app.config["LAB_MODE"] = "vulnerable"
        self.assertEqual(client.get("/api/requests/201").status_code, 403)

    def test_modes_have_the_same_routes_and_database_schema(self):
        secure_app, _ = self.make_lab("secure")
        vulnerable_app, _ = self.make_lab("vulnerable")
        secure_routes = {(rule.rule, tuple(sorted(rule.methods))) for rule in secure_app.url_map.iter_rules()}
        vulnerable_routes = {(rule.rule, tuple(sorted(rule.methods))) for rule in vulnerable_app.url_map.iter_rules()}
        self.assertEqual(secure_routes, vulnerable_routes)
        schemas = []
        for app in (secure_app, vulnerable_app):
            with app.app_context():
                schemas.append([
                    (row["name"], row["sql"]) for row in get_db().execute(
                        "SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
                    )
                ])
        self.assertEqual(schemas[0], schemas[1])

    def test_request_idor_comparison_and_json_errors(self):
        _, secure = self.make_lab("secure")
        self.assertEqual(secure.get("/api/requests/101").status_code, 401)
        self.login(secure, "alice", "Student123!")
        own = secure.get("/api/requests/101")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json["request"]["student_id"], 1)
        other = secure.get("/api/requests/201")
        self.assertEqual(other.status_code, 403)
        self.assertEqual(other.json["error"], "forbidden")
        self.assertEqual(secure.get("/api/requests/999").status_code, 404)
        self.assertEqual(secure.get("/api/not-an-endpoint").json["error"], "not_found")

        _, vulnerable = self.make_lab("vulnerable")
        self.login(vulnerable, "alice", "Student123!")
        result = vulnerable.get("/api/requests/201")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["request"]["id"], 201)
        self.assertEqual(result.json["request"]["student_id"], 2)
        # The ordinary HTML student route keeps its original ownership check.
        self.assertEqual(vulnerable.get("/student/requests/201").status_code, 404)
        self.assertEqual(vulnerable.post(
            "/admin/requests/101/status", data={
                "decision": "approve", "csrf_token": self.csrf_headers(vulnerable)["X-CSRF-Token"],
            },
        ).status_code, 403)

    def test_announcement_function_authorization_comparison(self):
        secure_app, secure = self.make_lab("secure")
        self.assertEqual(secure.post("/api/admin/announcements", json={"title": "A", "body": "B"}).status_code, 401)
        self.login(secure, "alice", "Student123!")
        headers = self.csrf_headers(secure)
        denied = secure.post("/api/admin/announcements", json={"title": "Blocked", "body": "No"}, headers=headers)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json["error"], "forbidden")
        with secure_app.app_context():
            self.assertIsNone(get_db().execute("SELECT id FROM announcements WHERE title = 'Blocked'").fetchone())
        self.assertEqual(secure.get("/admin/announcements").status_code, 403)

        _, admin_client = self.make_lab("secure")
        self.login(admin_client, "admin", "Admin123!")
        created = admin_client.post("/api/admin/announcements", json={"title": "Admin notice", "body": "Campus update"}, headers=self.csrf_headers(admin_client))
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["announcement"]["created_by"], 3)

        vulnerable_app, vulnerable = self.make_lab("vulnerable")
        self.login(vulnerable, "alice", "Student123!")
        self.assertEqual(vulnerable.post("/api/admin/announcements", json={"title": "No token", "body": "No"}).status_code, 400)
        allowed = vulnerable.post(
            "/api/admin/announcements",
            data={"title": "Student notice", "body": "Fictional lab notice", "csrf_token": self.csrf_headers(vulnerable)["X-CSRF-Token"]},
        )
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.json["announcement"]["created_by"], 1)
        with vulnerable_app.app_context():
            row = get_db().execute("SELECT created_by FROM announcements WHERE title = 'Student notice'").fetchone()
            self.assertEqual(row[0], 1)
        self.assertEqual(vulnerable.get("/admin/announcements").status_code, 403)

    def test_profile_field_authorization_comparison_and_role_refresh(self):
        secure_app, secure = self.make_lab("secure")
        self.login(secure, "alice", "Student123!")
        headers = self.csrf_headers(secure)
        denied = secure.post("/api/profile", json={"full_name": "Alice Updated", "role": "admin"}, headers=headers)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json["error"], "forbidden")
        with secure_app.app_context():
            role = get_db().execute("SELECT role FROM users WHERE username = 'alice'").fetchone()[0]
            name = get_db().execute("SELECT full_name FROM student_profiles WHERE user_id = 1").fetchone()[0]
            self.assertEqual((role, name), ("student", "Alice Carter"))
        ordinary = secure.post("/api/profile", json={"phone": "555 0900"}, headers=headers)
        self.assertEqual(ordinary.status_code, 200)
        self.assertEqual(ordinary.json["profile"]["phone"], "555 0900")
        self.assertEqual(secure.post("/api/profile", json={"user_id": 2}, headers=headers).status_code, 403)

        vulnerable_app, vulnerable = self.make_lab("vulnerable")
        self.login(vulnerable, "alice", "Student123!")
        changed = vulnerable.post("/api/profile", json={"full_name": "Alice Lab", "role": "admin"}, headers=self.csrf_headers(vulnerable))
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json["user"]["role"], "admin")
        with vulnerable_app.app_context():
            role = get_db().execute("SELECT role FROM users WHERE username = 'alice'").fetchone()[0]
            self.assertEqual(role, "admin")
        self.assertEqual(vulnerable.get("/admin/dashboard").status_code, 200)
        self.assertEqual(vulnerable.get("/student/dashboard").status_code, 403)
        self.assertEqual(vulnerable.get("/api/requests/101").status_code, 403)
        with vulnerable_app.app_context():
            reset_db()
            restored = get_db().execute("SELECT role FROM users WHERE username = 'alice'").fetchone()[0]
            self.assertEqual(restored, "student")
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM announcements").fetchone()[0], 2)
            self.assertEqual(get_db().execute("SELECT student_id FROM academic_requests WHERE id = 101").fetchone()[0], 1)
            self.assertEqual(get_db().execute("SELECT student_id FROM academic_requests WHERE id = 201").fetchone()[0], 2)
        self.assertEqual(vulnerable.get("/student/dashboard").status_code, 200)

    def test_api_body_validation_and_csrf_failures_are_json(self):
        app, client = self.make_lab("secure")
        self.login(client, "alice", "Student123!")
        missing_token = client.post("/api/profile", json={"phone": "555"})
        self.assertEqual(missing_token.status_code, 400)
        self.assertTrue(missing_token.is_json)
        self.assertEqual(missing_token.json["error"], "bad_request")
        bad_body = client.post("/api/profile", data="[]", content_type="application/json", headers=self.csrf_headers(client))
        self.assertEqual(bad_body.status_code, 400)
        self.assertEqual(bad_body.json["error"], "invalid_body")
        self.assertEqual(client.post("/api/profile", json={"role": "owner"}, headers=self.csrf_headers(client)).status_code, 403)
        json_token = client.post("/api/profile", json={
            "phone": "555 0901", "csrf_token": self.csrf_headers(client)["X-CSRF-Token"],
        })
        self.assertEqual(json_token.status_code, 200)

    def test_reset_restores_all_fictional_data_after_lab_actions(self):
        app, client = self.make_lab("vulnerable")
        self.login(client, "alice", "Student123!")
        headers = self.csrf_headers(client)
        created = client.post("/api/admin/announcements", json={
            "title": "Temporary lab notice", "body": "Removed on reset",
        }, headers=headers)
        self.assertEqual(created.status_code, 201)
        promoted = client.post("/api/profile", json={"role": "admin"}, headers=headers)
        self.assertEqual(promoted.status_code, 200)
        with app.app_context():
            reset_db()
            connection = get_db()
            self.assertEqual(
                [(row["username"], row["role"]) for row in connection.execute(
                    "SELECT username, role FROM users ORDER BY id"
                )],
                [("alice", "student"), ("bob", "student"), ("admin", "admin")],
            )
            self.assertEqual(
                [(row["id"], row["student_id"], row["status"]) for row in connection.execute(
                    "SELECT id, student_id, status FROM academic_requests ORDER BY id"
                )],
                [(101, 1, "pending"), (201, 2, "approved")],
            )
            self.assertEqual(
                [(row["id"], row["title"]) for row in connection.execute(
                    "SELECT id, title FROM announcements ORDER BY id"
                )],
                [(1, "Welcome to the autumn term"), (2, "Library hours")],
            )
        self.assertEqual(client.get("/student/dashboard").status_code, 200)
        self.assertEqual(client.get("/admin/dashboard").status_code, 403)

    def test_host_binding_requires_explicit_named_interface(self):
        names = ("CAMPUSSECURE_HOST_ONLY_IP", "CAMPUSSECURE_ENABLE_HOST_ONLY", "CAMPUSSECURE_HOST_ONLY_INTERFACE")
        with patch.dict(os.environ, {name: "" for name in names}):
            self.assertEqual(selected_host(), "127.0.0.1")
        with patch.dict(os.environ, {names[0]: "192.168.56.10", names[1]: "1", names[2]: ""}):
            with self.assertRaises(ValueError):
                selected_host()
        with patch.dict(os.environ, {names[0]: "0.0.0.0", names[1]: "1", names[2]: "hostonly0"}):
            with self.assertRaises(ValueError):
                selected_host()
        with patch.dict(os.environ, {names[0]: "192.168.56.10", names[1]: "1", names[2]: "hostonly0"}):
            with patch("run.interface_ipv4_addresses", return_value={"192.168.56.10"}):
                self.assertEqual(selected_host(), "192.168.56.10")
            with patch("run.interface_ipv4_addresses", return_value={"192.168.56.11"}):
                with self.assertRaises(ValueError):
                    selected_host()


if __name__ == "__main__":
    unittest.main()
