"""Stage 4 regression checks against a fresh, isolated SQLite file per test."""

import re

import pytest
from jinja2 import StrictUndefined
from werkzeug.security import check_password_hash

from app import create_app
from app.db import get_db, reset_db, seed_db


@pytest.fixture(params=("secure", "vulnerable"))
def lab(request, tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "stage-four-test-only-secret",
        "DATABASE": str(tmp_path / "isolated.sqlite3"),
        "LAB_MODE": request.param,
    })
    app.jinja_env.undefined = StrictUndefined
    with app.app_context():
        seed_db()
    return app, app.test_client(), request.param


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client, username, password):
    assert client.get("/login").status_code == 200
    response = client.post("/login", data={
        "username": username, "password": password, "csrf_token": csrf(client),
    })
    if response.status_code == 302:
        # Login clears the old session. The next page creates the new CSRF token.
        assert client.get(response.headers["Location"]).status_code == 200
    return response


def api_post(client, path, data):
    return client.post(path, json=data, headers={"X-CSRF-Token": csrf(client)})


def db_one(app, query, parameters=()):
    with app.app_context():
        row = get_db().execute(query, parameters).fetchone()
        return tuple(row) if row is not None else None


def test_authentication_and_logout(lab):
    _, client, _ = lab
    bad = login(client, "alice", "wrong password")
    assert bad.status_code == 200
    assert b"Invalid username or password" in bad.data
    assert client.get("/student/dashboard").status_code == 302
    good = login(client, "alice", "Student123!")
    assert good.status_code == 302
    assert good.headers["Location"] == "/student/dashboard"
    assert client.get("/student/dashboard").status_code == 200
    assert client.post("/logout", data={"csrf_token": csrf(client)}).status_code == 302
    assert client.get("/api/requests/101").status_code == 401
    assert client.get("/student/dashboard").status_code == 302


def test_anonymous_and_wrong_role_access(lab):
    app, client, _ = lab
    for path in ("/student/dashboard", "/student/profile", "/student/requests",
                 "/admin/dashboard", "/admin/requests", "/admin/announcements"):
        assert client.get(path).status_code == 302
    assert client.get("/api/requests/101").status_code == 401
    assert client.post("/api/admin/announcements", json={"title": "A", "body": "B"}).status_code == 401
    assert client.post("/api/profile", json={"phone": "1"}).status_code == 401
    assert login(client, "alice", "Student123!").status_code == 302
    for path in ("/admin/dashboard", "/admin/requests", "/admin/announcements"):
        assert client.get(path).status_code == 403
    assert client.post("/admin/requests/101/status", data={
        "decision": "approve", "csrf_token": csrf(client),
    }).status_code == 403
    assert db_one(app, "SELECT status FROM academic_requests WHERE id = 101") == ("pending",)


def test_object_authorization_and_unknown_id(lab):
    _, client, mode = lab
    assert login(client, "alice", "Student123!").status_code == 302
    own = client.get("/api/requests/101")
    assert own.status_code == 200
    assert own.json["request"]["student_id"] == 1
    other = client.get("/api/requests/201")
    assert other.status_code == (403 if mode == "secure" else 200)
    if mode == "vulnerable":
        assert (other.json["request"]["id"], other.json["request"]["student_id"]) == (201, 2)
    else:
        assert other.json["error"] == "forbidden"
    assert client.get("/api/requests/999").status_code == 404
    assert client.get("/student/requests/201").status_code == 404
    assert client.post("/logout", data={"csrf_token": csrf(client)}).status_code == 302
    assert login(client, "bob", "Student123!").status_code == 302
    bob = client.get("/api/requests/201")
    assert bob.status_code == 200
    assert bob.json["request"]["student_id"] == 2
    assert client.get("/api/requests/999").status_code == 404


def test_announcement_authorization_and_persistence(lab):
    app, student, mode = lab
    admin = app.test_client()
    assert login(admin, "admin", "Admin123!").status_code == 302
    created = api_post(admin, "/api/admin/announcements", {
        "title": "Admin lab notice", "body": "Synthetic campus update",
    })
    assert created.status_code == 201
    assert created.json["announcement"]["created_by"] == 3
    assert db_one(app, "SELECT created_by, body FROM announcements WHERE title = ?",
                  ("Admin lab notice",)) == (3, "Synthetic campus update")

    assert login(student, "alice", "Student123!").status_code == 302
    result = api_post(student, "/api/admin/announcements", {
        "title": "Student lab notice", "body": "Synthetic student update",
    })
    assert result.status_code == (403 if mode == "secure" else 201)
    stored = db_one(app, "SELECT created_by, body FROM announcements WHERE title = ?",
                    ("Student lab notice",))
    if mode == "secure":
        assert result.json["error"] == "forbidden"
        assert stored is None
    else:
        assert result.json["announcement"]["created_by"] == 1
        assert stored == (1, "Synthetic student update")
    assert student.get("/admin/announcements").status_code == 403


def test_profile_field_authorization_and_role_refresh(lab):
    app, client, mode = lab
    assert login(client, "alice", "Student123!").status_code == 302
    updated = api_post(client, "/api/profile", {
        "full_name": "Alice Updated", "email": "alice.updated@example.test", "phone": "555 0111",
    })
    assert updated.status_code == 200
    assert db_one(app, "SELECT full_name, email, phone FROM student_profiles WHERE user_id = 1") == (
        "Alice Updated", "alice.updated@example.test", "555 0111",
    )
    attempt = api_post(client, "/api/profile", {"role": "admin"})
    assert attempt.status_code == (403 if mode == "secure" else 200)
    assert db_one(app, "SELECT role FROM users WHERE username = 'alice'") == (
        "student" if mode == "secure" else "admin",
    )
    assert client.get("/admin/dashboard").status_code == (403 if mode == "secure" else 200)
    if mode == "secure":
        assert attempt.json["error"] == "forbidden"
        assert client.get("/student/dashboard").status_code == 200
    else:
        assert attempt.json["user"]["role"] == "admin"
        assert client.get("/student/dashboard").status_code == 403


def test_secure_profile_rejects_mixed_fields_without_partial_write(tmp_path):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "secure-only-test-key",
        "DATABASE": str(tmp_path / "secure.sqlite3"), "LAB_MODE": "secure",
    })
    with app.app_context():
        seed_db()
    client = app.test_client()
    assert login(client, "alice", "Student123!").status_code == 302
    result = api_post(client, "/api/profile", {"full_name": "Should Not Save", "role": "admin"})
    assert result.status_code == 403
    assert db_one(app, "SELECT role FROM users WHERE id = 1") == ("student",)
    assert db_one(app, "SELECT full_name FROM student_profiles WHERE user_id = 1") == ("Alice Carter",)
    assert api_post(client, "/api/profile", {"user_id": 2}).status_code == 403


def test_csrf_and_input_validation_keep_database_unchanged(lab):
    app, client, _ = lab
    assert login(client, "alice", "Student123!").status_code == 302
    assert client.post("/api/profile", json={"phone": "changed"}).status_code == 400
    assert api_post(client, "/api/profile", {"email": "invalid"}).status_code == 400
    assert db_one(app, "SELECT phone, email FROM student_profiles WHERE user_id = 1") == (
        "+1 555 0101", "alice@example.test",
    )


def test_reset_restores_every_fixture_and_is_repeatable(lab):
    app, client, _ = lab
    with app.app_context():
        connection = get_db()
        connection.execute("UPDATE users SET role = 'admin', password_hash = 'changed' WHERE id = 1")
        connection.execute("UPDATE academic_requests SET status = 'rejected' WHERE id = 101")
        connection.execute("DELETE FROM academic_requests WHERE id = 201")
        connection.execute("DELETE FROM announcements WHERE id = 1")
        connection.execute("INSERT INTO announcements (title, body, created_by, published_on) "
                           "VALUES ('temporary', 'temporary', 3, '2026-09-15')")
        connection.commit()
        reset_db()
        reset_db()
        users = [tuple(row) for row in connection.execute(
            "SELECT id, username, role FROM users ORDER BY id")]
        requests = [tuple(row) for row in connection.execute(
            "SELECT id, student_id, status FROM academic_requests ORDER BY id")]
        notices = [tuple(row) for row in connection.execute(
            "SELECT id, title FROM announcements ORDER BY id")]
        hash_value = connection.execute("SELECT password_hash FROM users WHERE id = 1").fetchone()[0]
    assert users == [(1, "alice", "student"), (2, "bob", "student"), (3, "admin", "admin")]
    assert requests == [(101, 1, "pending"), (201, 2, "approved")]
    assert notices == [(1, "Welcome to the autumn term"), (2, "Library hours")]
    assert check_password_hash(hash_value, "Student123!")
    assert login(client, "alice", "Student123!").status_code == 302
    assert client.get("/api/requests/101").status_code == 200


def test_page_rendering_and_local_assets(lab):
    app, student, _ = lab
    pages = (("/student/dashboard", b"Alice Carter"),
             ("/student/profile", b"alice@example.test"),
             ("/student/requests", b"Transcript"),
             ("/student/requests/101", b"scholarship application"))
    assert login(student, "alice", "Student123!").status_code == 302
    assets = set()
    for path, expected in pages:
        response = student.get(path)
        assert response.status_code == 200
        assert expected in response.data
        assert b'href="/admin' not in response.data
        assets.update(re.findall(rb'(?:href|src)="(/static/[^"#]+)', response.data))
    admin = app.test_client()
    assert login(admin, "admin", "Admin123!").status_code == 302
    for path in ("/admin/dashboard", "/admin/requests", "/admin/requests/101",
                 "/admin/announcements", "/admin/announcements/1/edit"):
        response = admin.get(path)
        assert response.status_code == 200
        assert b'href="/student' not in response.data
        assets.update(re.findall(rb'(?:href|src)="(/static/[^"#]+)', response.data))
    assert {b"/static/css/portal.css", b"/static/vendor/bootstrap/css/bootstrap.min.css",
            b"/static/vendor/bootstrap/js/bootstrap.bundle.min.js"} <= assets
    for path in assets:
        assert admin.get(path.decode()).status_code == 200


def test_admin_review_survives_lab_modes(lab):
    app, client, _ = lab
    assert login(client, "admin", "Admin123!").status_code == 302
    assert client.post("/admin/requests/101/status", data={"decision": "approve"}).status_code == 400
    assert client.post("/admin/requests/101/status", data={
        "decision": "approve", "csrf_token": csrf(client),
    }).status_code == 302
    assert db_one(app, "SELECT status FROM academic_requests WHERE id = 101") == ("approved",)
    assert client.post("/logout", data={"csrf_token": csrf(client)}).status_code == 302
    assert login(client, "alice", "Student123!").status_code == 302
    assert b"Approved" in client.get("/student/requests/101").data


def test_default_mode_and_environment_selection(tmp_path, monkeypatch):
    monkeypatch.delenv("LAB_MODE", raising=False)
    monkeypatch.setenv("CAMPUSSECURE_DATABASE", str(tmp_path / "default.sqlite3"))
    app = create_app({"TESTING": True})
    assert app.extensions["campussecure_lab_mode"] == "secure"
    with app.app_context():
        seed_db()
    client = app.test_client()
    assert login(client, "alice", "Student123!").status_code == 302
    assert client.get("/api/requests/201").status_code == 403
    monkeypatch.setenv("LAB_MODE", "vulnerable")
    assert client.get("/api/requests/201").status_code == 403  # Restart required.
    vulnerable = create_app({"TESTING": True, "DATABASE": str(tmp_path / "vulnerable.sqlite3")})
    with vulnerable.app_context():
        seed_db()
    other = vulnerable.test_client()
    assert login(other, "alice", "Student123!").status_code == 302
    assert other.get("/api/requests/201").status_code == 200


def test_unsupported_mode_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_MODE", "unsupported")
    with pytest.raises(ValueError, match="LAB_MODE"):
        create_app({"TESTING": True, "DATABASE": str(tmp_path / "bad.sqlite3")})
