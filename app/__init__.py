"""CampusSecure Flask application factory."""

import os
import secrets

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for

from . import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CAMPUSSECURE_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("CAMPUSSECURE_DATABASE")
        or os.path.join(app.instance_path, "campussecure.sqlite3"),
        LAB_MODE=os.environ.get("LAB_MODE", "secure"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if app.config["LAB_MODE"] not in ("secure", "vulnerable"):
        raise ValueError("LAB_MODE must be 'secure' or 'vulnerable'")
    app.extensions["campussecure_lab_mode"] = app.config["LAB_MODE"]
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    @app.before_request
    def load_user_and_check_csrf():
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            g.user = db.get_db().execute(
                "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if g.user is None:
                session.clear()
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        if request.method == "POST":
            if request.path.startswith("/api/") and g.user is None:
                return None  # The API returns 401 for an unsigned-in caller.
            supplied = request.headers.get("X-CSRF-Token", "")
            if not supplied:
                if request.is_json:
                    body = request.get_json(silent=True)
                    supplied = body.get("csrf_token", "") if isinstance(body, dict) else ""
                else:
                    supplied = request.form.get("csrf_token", "")
            if not isinstance(supplied, str) or not secrets.compare_digest(session["csrf_token"], supplied):
                abort(400, "Invalid form token")

    @app.context_processor
    def template_context():
        return {"current_user": g.get("user"), "csrf_token": session.get("csrf_token")}

    @app.route("/")
    def index():
        if g.user is None:
            return redirect(url_for("auth.login"))
        target = "admin.dashboard" if g.user["role"] == "admin" else "student.dashboard"
        return redirect(url_for(target))

    from .auth import bp as auth_bp
    from .student import bp as student_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    def error_page(status, heading, message, api_code):
        if request.path.startswith("/api/"):
            return jsonify(error=api_code, message=message), status
        return render_template("errors/error.html", code=status, heading=heading,
                               message=message), status

    @app.errorhandler(400)
    def bad_request(error):
        return error_page(400, "Invalid request",
                          "The submitted request could not be processed.", "bad_request")

    @app.errorhandler(401)
    def unauthorized(error):
        return error_page(401, "Sign in required", "Sign in before using this endpoint.",
                          "authentication_required")

    @app.errorhandler(403)
    def forbidden(error):
        return error_page(403, "Access restricted",
                          "Your account does not have access to this page.", "forbidden")

    @app.errorhandler(404)
    def not_found(error):
        return error_page(404, "Page not found",
                          "The page or record you requested is unavailable.", "not_found")

    @app.errorhandler(405)
    def method_not_allowed(error):
        return error_page(405, "Method not allowed",
                          "This action does not support that HTTP method.", "method_not_allowed")

    @app.errorhandler(500)
    def server_error(error):
        return error_page(500, "Something went wrong",
                          "We could not load this page. Please try again shortly.", "server_error")

    return app
