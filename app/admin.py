"""Administrator dashboard, request review, and announcement management."""

from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/dashboard")
@login_required("admin")
def dashboard():
    connection = get_db()
    student_count = connection.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    request_count = connection.execute("SELECT COUNT(*) FROM academic_requests").fetchone()[0]
    announcement_count = connection.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    recent_requests = connection.execute(
        "SELECT r.id, r.request_type, r.status, r.submitted_on, p.full_name "
        "FROM academic_requests AS r JOIN student_profiles AS p ON p.user_id = r.student_id "
        "ORDER BY r.submitted_on DESC, r.id DESC LIMIT 5"
    ).fetchall()
    students = connection.execute(
        "SELECT p.full_name, p.department, u.username FROM student_profiles AS p "
        "JOIN users AS u ON u.id = p.user_id ORDER BY p.full_name LIMIT 5"
    ).fetchall()
    recent_announcements = connection.execute(
        "SELECT id, title, published_on FROM announcements ORDER BY published_on DESC, id DESC LIMIT 3"
    ).fetchall()
    return render_template(
        "admin/dashboard.html", student_count=student_count,
        request_count=request_count, announcement_count=announcement_count,
        recent_requests=recent_requests, students=students,
        recent_announcements=recent_announcements,
    )


@bp.get("/requests")
@login_required("admin")
def requests_list():
    rows = get_db().execute(
        "SELECT r.id, r.request_type, r.details, r.status, r.submitted_on, "
        "COALESCE(p.full_name, u.username) AS student_name "
        "FROM academic_requests AS r "
        "JOIN users AS u ON u.id = r.student_id "
        "LEFT JOIN student_profiles AS p ON p.user_id = r.student_id "
        "ORDER BY r.submitted_on DESC, r.id DESC"
    ).fetchall()
    return render_template("admin/requests.html", requests=rows)


@bp.get("/requests/<int:request_id>")
@login_required("admin")
def request_detail(request_id):
    row = get_db().execute(
        "SELECT r.id, r.request_type, r.details, r.status, r.submitted_on, "
        "COALESCE(p.full_name, u.username) AS student_name, u.username "
        "FROM academic_requests AS r "
        "JOIN users AS u ON u.id = r.student_id "
        "LEFT JOIN student_profiles AS p ON p.user_id = r.student_id "
        "WHERE r.id = ?", (request_id,)
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("admin/request_detail.html", academic_request=row)


@bp.post("/requests/<int:request_id>/status")
@login_required("admin")
def update_request_status(request_id):
    decisions = {"approve": "approved", "reject": "rejected"}
    status = decisions.get(request.form.get("decision"))
    if status is None:
        abort(400)

    connection = get_db()
    # The pending condition prevents a second review from overwriting a decision.
    result = connection.execute(
        "UPDATE academic_requests SET status = ? WHERE id = ? AND status = 'pending'",
        (status, request_id),
    )
    connection.commit()
    if result.rowcount == 0:
        exists = connection.execute(
            "SELECT id FROM academic_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if exists is None:
            abort(404)
        flash("This request has already been reviewed.", "error")
    else:
        flash(f"Request #{request_id} {status}.", "success")
    return redirect(url_for("admin.request_detail", request_id=request_id))


def valid_announcement_form():
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or len(title) > 150 or not body or len(body) > 5000:
        flash("Title and body are required and must fit the length limits.", "error")
        return None
    return title, body


@bp.route("/announcements", methods=["GET", "POST"])
@login_required("admin")
def announcements():
    connection = get_db()
    if request.method == "POST":
        values = valid_announcement_form()
        if values is not None:
            connection.execute(
                "INSERT INTO announcements (title, body, created_by, published_on) VALUES (?, ?, ?, ?)",
                (*values, g.user["id"], date.today().isoformat()),
            )
            connection.commit()
            flash("Announcement created.", "success")
            return redirect(url_for("admin.announcements"))
    rows = connection.execute(
        "SELECT id, title, body, published_on FROM announcements ORDER BY published_on DESC, id DESC"
    ).fetchall()
    return render_template("admin/announcements.html", announcements=rows)


@bp.route("/announcements/<int:announcement_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def edit_announcement(announcement_id):
    connection = get_db()
    row = connection.execute(
        "SELECT id, title, body FROM announcements WHERE id = ?", (announcement_id,)
    ).fetchone()
    if row is None:
        abort(404)
    if request.method == "POST":
        values = valid_announcement_form()
        if values is not None:
            connection.execute(
                "UPDATE announcements SET title = ?, body = ? WHERE id = ?", (*values, announcement_id)
            )
            connection.commit()
            flash("Announcement updated.", "success")
            return redirect(url_for("admin.announcements"))
    return render_template("admin/edit_announcement.html", announcement=row)


@bp.post("/announcements/<int:announcement_id>/delete")
@login_required("admin")
def delete_announcement(announcement_id):
    connection = get_db()
    result = connection.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
    connection.commit()
    if result.rowcount == 0:
        abort(404)
    flash("Announcement deleted.", "success")
    return redirect(url_for("admin.announcements"))
