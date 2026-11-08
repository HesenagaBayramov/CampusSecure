"""Small SQLite data layer and repeatable fictional fixtures."""

import sqlite3

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin'))
);
CREATE TABLE IF NOT EXISTS student_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    department TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS academic_requests (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    details TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    submitted_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    published_on TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    get_db().executescript(SCHEMA)
    get_db().commit()


def seed_db():
    """Insert missing demo rows without changing existing data."""
    connection = get_db()
    init_db()
    accounts = (
        (1, "alice", "Student123!", "student"),
        (2, "bob", "Student123!", "student"),
        (3, "admin", "Admin123!", "admin"),
    )
    for user_id, username, password, role in accounts:
        connection.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (user_id, username, generate_password_hash(password), role),
        )
    alice_id = connection.execute("SELECT id FROM users WHERE username = 'alice'").fetchone()[0]
    bob_id = connection.execute("SELECT id FROM users WHERE username = 'bob'").fetchone()[0]
    admin_id = connection.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
    connection.executemany(
        "INSERT OR IGNORE INTO student_profiles "
        "(user_id, full_name, email, phone, department) VALUES (?, ?, ?, ?, ?)",
        (
            (alice_id, "Alice Carter", "alice@example.test", "+1 555 0101", "Computer Science"),
            (bob_id, "Bob Rivera", "bob@example.test", "+1 555 0102", "Mathematics"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO academic_requests "
        "(id, student_id, request_type, details, status, submitted_on) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            (101, alice_id, "Transcript", "Official transcript for scholarship application.", "pending", "2026-09-10"),
            (201, bob_id, "Enrollment letter", "Proof of enrollment for local library.", "approved", "2026-09-11"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO announcements "
        "(id, title, body, created_by, published_on) VALUES (?, ?, ?, ?, ?)",
        (
            (1, "Welcome to the autumn term", "Classes begin on September 14.", admin_id, "2026-09-01"),
            (2, "Library hours", "The campus library is open weekdays from 08:00 to 20:00.", admin_id, "2026-09-05"),
        ),
    )
    connection.commit()


def reset_db():
    """Clear demo tables and restore their original rows and credentials."""
    connection = get_db()
    init_db()
    with connection:
        for table in ("announcements", "academic_requests", "student_profiles", "users"):
            connection.execute(f"DELETE FROM {table}")
    seed_db()


@click.command("seed-db")
def seed_db_command():
    seed_db()
    click.echo("Demo data seeded.")


@click.command("reset-db")
def reset_db_command():
    reset_db()
    click.echo("Demo data reset.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(seed_db_command)
    app.cli.add_command(reset_db_command)
