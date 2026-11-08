"""JSON endpoints for the three controlled, synthetic authorization scenarios."""

from datetime import date

from flask import Blueprint, g, jsonify, request

from . import lab_policy
from .db import get_db

bp = Blueprint("api", __name__, url_prefix="/api")


def error_response(status, code, message):
    return jsonify(error=code, message=message), status


@bp.before_request
def require_session():
    if g.user is None:
        return error_response(401, "authentication_required", "Sign in before using this endpoint.")


def payload():
    """Accept JSON or form data so requests can be inspected in Burp Repeater."""
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None
        return data
    if request.mimetype in ("application/x-www-form-urlencoded", "multipart/form-data"):
        return request.form.to_dict(flat=True)
    return None


@bp.get("/requests/<int:request_id>")
def request_record(request_id):
    if g.user["role"] != "student":
        return error_response(403, "forbidden", "Student access is required.")
    row = get_db().execute(
        "SELECT id, student_id, request_type, details, status, submitted_on "
        "FROM academic_requests WHERE id = ?", (request_id,)
    ).fetchone()
    if row is None:
        return error_response(404, "not_found", "Academic request not found.")
    if not lab_policy.may_read_student_request(g.user["id"], row["student_id"]):
        return error_response(403, "forbidden", "This request belongs to another student.")
    return jsonify(request={key: row[key] for key in row.keys()})


@bp.post("/admin/announcements")
def create_announcement():
    if not lab_policy.may_create_announcement(g.user["role"]):
        return error_response(403, "forbidden", "Administrator access is required.")
    data = payload()
    if data is None:
        return error_response(400, "invalid_body", "Send a JSON object or form fields.")
    title = data.get("title")
    body = data.get("body")
    if not isinstance(title, str) or not isinstance(body, str):
        return error_response(400, "invalid_fields", "Title and body must be text.")
    title, body = title.strip(), body.strip()
    if not title or len(title) > 150 or not body or len(body) > 5000:
        return error_response(400, "invalid_fields", "Title and body are required within field limits.")
    published_on = date.today().isoformat()
    connection = get_db()
    cursor = connection.execute(
        "INSERT INTO announcements (title, body, created_by, published_on) VALUES (?, ?, ?, ?)",
        (title, body, g.user["id"], published_on),
    )
    connection.commit()
    return jsonify(announcement={
        "id": cursor.lastrowid, "title": title, "body": body,
        "created_by": g.user["id"], "published_on": published_on,
    }), 201


@bp.post("/profile")
def update_profile():
    if g.user["role"] != "student":
        return error_response(403, "forbidden", "Student access is required.")
    data = payload()
    if data is None:
        return error_response(400, "invalid_body", "Send a JSON object or form fields.")
    data.pop("csrf_token", None)
    if not data:
        return error_response(400, "invalid_fields", "Provide a profile field to update.")
    ordinary_fields = {"full_name", "email", "phone"}
    if "role" in data and not lab_policy.may_assign_own_role():
        return error_response(403, "forbidden", "The role field is not editable.")
    allowed = ordinary_fields | ({"role"} if lab_policy.may_assign_own_role() else set())
    if set(data) - allowed:
        return error_response(403, "forbidden", "One or more fields are not editable.")

    connection = get_db()
    current = connection.execute(
        "SELECT full_name, email, phone, department FROM student_profiles WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()
    if current is None:
        return error_response(404, "not_found", "Student profile not found.")
    updated = {field: data.get(field, current[field]) for field in ordinary_fields}
    if any(not isinstance(value, str) for value in updated.values()):
        return error_response(400, "invalid_fields", "Profile fields must be text.")
    updated = {field: value.strip() for field, value in updated.items()}
    if (not updated["full_name"] or len(updated["full_name"]) > 100
            or not updated["email"] or len(updated["email"]) > 254
            or "@" not in updated["email"] or len(updated["phone"]) > 40):
        return error_response(400, "invalid_fields", "Profile fields are invalid or too long.")
    new_role = data.get("role", g.user["role"])
    if new_role not in ("student", "admin"):
        return error_response(400, "invalid_fields", "Role must be student or admin.")

    with connection:
        connection.execute(
            "UPDATE student_profiles SET full_name = ?, email = ?, phone = ? WHERE user_id = ?",
            (updated["full_name"], updated["email"], updated["phone"], g.user["id"]),
        )
        if "role" in data:
            connection.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, g.user["id"]))
    return jsonify(user={
        "id": g.user["id"], "username": g.user["username"], "role": new_role,
    }, profile={**updated, "department": current["department"]})
