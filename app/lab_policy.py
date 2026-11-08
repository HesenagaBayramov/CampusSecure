"""The three mode-dependent authorization decisions for the isolated lab.

Only the API routes call these functions. The normal HTML portal keeps its
existing ownership and role checks in either mode.
"""

from flask import current_app


def mode():
    # Captured when the app starts; changing an environment variable later
    # cannot switch the behavior of a running instance.
    return current_app.extensions["campussecure_lab_mode"]


def may_read_student_request(student_id, owner_id):
    return student_id == owner_id or mode() == "vulnerable"


def may_create_announcement(role):
    return role == "admin" or (mode() == "vulnerable" and role == "student")


def may_assign_own_role():
    return mode() == "vulnerable"
