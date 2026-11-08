"""Student pages; queries always scope records to the signed-in student."""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.get("/dashboard")
@login_required("student")
def dashboard():
    connection = get_db()
    profile = connection.execute(
        "SELECT * FROM student_profiles WHERE user_id = ?", (g.user["id"],)
    ).fetchone()
    request_count = connection.execute(
        "SELECT COUNT(*) FROM academic_requests WHERE student_id = ?", (g.user["id"],)
    ).fetchone()[0]
    pending_count = connection.execute(
        "SELECT COUNT(*) FROM academic_requests WHERE student_id = ? AND status = 'pending'",
        (g.user["id"],),
    ).fetchone()[0]
    approved_count = connection.execute(
        "SELECT COUNT(*) FROM academic_requests WHERE student_id = ? AND status = 'approved'",
        (g.user["id"],),
    ).fetchone()[0]
    recent_requests = connection.execute(
        "SELECT id, request_type, status, submitted_on FROM academic_requests "
        "WHERE student_id = ? ORDER BY submitted_on DESC, id DESC LIMIT 4",
        (g.user["id"],),
    ).fetchall()
    announcements = connection.execute(
        "SELECT id, title, body, published_on FROM announcements ORDER BY published_on DESC, id DESC"
    ).fetchall()
    return render_template(
        "student/dashboard.html", profile=profile, request_count=request_count,
        pending_count=pending_count, approved_count=approved_count,
        recent_requests=recent_requests, announcements=announcements,
    )


@bp.route("/profile", methods=["GET", "POST"])
@login_required("student")
def profile():
    connection = get_db()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        if not full_name or len(full_name) > 100 or not email or len(email) > 254 or "@" not in email or len(phone) > 40:
            flash("Enter a name and email, within the field length limits.", "error")
        else:
            connection.execute(
                "UPDATE student_profiles SET full_name = ?, email = ?, phone = ? WHERE user_id = ?",
                (full_name, email, phone, g.user["id"]),
            )
            connection.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("student.profile"))
    row = connection.execute(
        "SELECT full_name, email, phone, department FROM student_profiles WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()
    return render_template("student/profile.html", profile=row)


@bp.get("/requests")
@login_required("student")
def requests_list():
    rows = get_db().execute(
        "SELECT id, request_type, details, status, submitted_on FROM academic_requests "
        "WHERE student_id = ? ORDER BY id", (g.user["id"],)
    ).fetchall()
    return render_template("student/requests.html", requests=rows)


@bp.get("/requests/<int:request_id>")
@login_required("student")
def request_detail(request_id):
    row = get_db().execute(
        "SELECT id, request_type, details, status, submitted_on FROM academic_requests "
        "WHERE id = ? AND student_id = ?", (request_id, g.user["id"])
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("student/request_detail.html", academic_request=row)
