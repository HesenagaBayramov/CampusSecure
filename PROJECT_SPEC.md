# CampusSecure project specification

## Purpose and scope

A fictional university student portal used for manual web application penetration testing and security hardening with Burp Suite in a strictly isolated, locally controlled educational laboratory. No real accounts, student data, university integrations, external APIs or cloud services. Stages 1–5 have delivered the application, automated verification, and documentation; manual Ubuntu/Kali Burp evidence remains pending. Preserve these routes and seeded IDs unless this specification is deliberately revised.

## Five-stage delivery plan

1. **Backend foundation (complete):** Flask factory, SQLite schema and repeatable fixtures, hashed demo passwords, session login/logout, protected student and administrator routes, secure role and ownership checks, tests and startup instructions.
2. **Interface (complete):** Responsive HTML5/Bootstrap 5 and vanilla JavaScript for the student and admin pages, preserving form actions, parameter names, route contracts and server-side checks. Includes sidebar/offcanvas navigation, status badges, dashboard previews, request search/filter, administrator academic request review, form feedback and error pages.
3. **Controlled authorization lab (complete):** Exactly three API scenarios differ by `LAB_MODE`: request ownership, administrator announcement creation, and profile role-field authorization. Both modes use identical endpoints and schema. The HTML portal retains its original authorization checks; mode selection requires an application restart and has no website control.
4. **Verification and lab guide (complete):** Pytest regression checks for both modes use a fresh temporary SQLite file per case. `docs/LAB_GUIDE.md` documents authorized manual Burp Suite request/response procedures, expected observations, reset steps, isolation, and shutdown. The guide does not claim that a Burp session has been executed.
5. **Final documentation and handoff (documentation complete; manual evidence pending):** README setup and safety instructions, a security assessment with explicit evidence placeholders, architecture documentation, a seven-slide outline and editable PowerPoint deck, and final automated quality checks. Genuine Burp screenshots and Host-only VM observations must be added only after the student performs the authorized manual exercise.

## Architecture

- Python 3, Flask application factory (`app.create_app`) and blueprints (`auth`, `student`, `admin`, `api`).
- SQLite through a small parameterized data layer in `app/db.py`; connection stored per request/application context, foreign keys enabled.
- Werkzeug password hashes in `users.password_hash`; Flask signed cookie sessions store only `user_id` and the CSRF token.
- Jinja templates escape rendered data. All state-changing browser actions use POST and require a session CSRF token.
- Bootstrap 5.3.3 CSS and bundle JavaScript, source maps and MIT license are checked into `app/static/vendor/bootstrap/` for offline use. `app/static/css/portal.css`, `app/static/js/portal.js` and `app/static/icons.svg` provide the portal design and small enhancements. Bootstrap's offcanvas component powers mobile navigation; no other frontend framework is used.
- The student and administrator dashboards use additional read-only queries to show recent requests, announcements, and student summaries. Client-side request search/filter acts only on rows already authorized and rendered by the server.
- Administrators can list every academic request, view full details, and make a one-time approve/reject decision on pending requests. A conditional SQLite update (`WHERE status = 'pending'`) prevents a later decision from overwriting one already stored. Students continue to read only their own request rows.
- The `api` blueprint serves the three lab contracts. `app/lab_policy.py` contains the only mode-dependent authorization decisions. `create_app` reads `LAB_MODE` at startup and captures it in `app.extensions`; changing an environment variable or `app.config` after creation does not change a running instance.
- API POST requests use the existing session CSRF token from an `X-CSRF-Token` header, JSON `csrf_token` field, or form `csrf_token` field. The API accepts JSON objects and URL-encoded form bodies and returns JSON for success and errors. HTML forms and routes remain separate.
- `run.py` defaults to `127.0.0.1:5000` and disables debug and reloader. A non-loopback bind requires `CAMPUSSECURE_ENABLE_HOST_ONLY=1`, an explicit private `CAMPUSSECURE_HOST_ONLY_IP`, and `CAMPUSSECURE_HOST_ONLY_INTERFACE`; the selected IP must be assigned to that named local interface. The operator must also verify that the adapter is actually isolated Host-only. The app never chooses `0.0.0.0`.
- `LAB_MODE` accepts `secure` (default) and `vulnerable`. The latter is only for the locally controlled synthetic lab.
- `requirements-dev.txt` adds pytest for Stage 4 verification. `tests/test_security.py` checks authentication, the three API comparisons, persisted effects, reset repeatability, configuration, portal rendering and core admin review in isolated temporary databases. The earlier unittest suites remain available.
- No Redis, Docker, React, external APIs or cloud services. Flask is the only direct runtime dependency; Werkzeug and Jinja are Flask dependencies.

## Database design

| Table | Primary key | Main fields and relationships |
| --- | --- | --- |
| `users` | `id` | unique `username`, `password_hash`, `role` (`student` or `admin`) |
| `student_profiles` | `user_id` | FK to `users`, `full_name`, `email`, `phone`, `department` |
| `academic_requests` | `id` | FK `student_id` to `users`, `request_type`, `details`, `status`, `submitted_on` |
| `announcements` | `id` | FK `created_by` to `users`, `title`, `body`, `published_on` |

Fixture IDs: Alice is user 1 and owns request 101 (pending); Bob is user 2 and owns request 201 (approved); admin is user 3. Announcement IDs 1 and 2 are fixed. Dates, names, departments and request text are fictional and fixed. `seed_db` inserts missing rows without overwriting edits; `reset_db` deletes demo rows and restores the original fixture, credentials, and request statuses.

## HTTP endpoint contracts

| Method | Path | Access | Contract |
| --- | --- | --- | --- |
| GET | `/` | Any | Redirect to login or the role's dashboard. |
| GET, POST | `/login` | Any | Form fields `username`, `password`, `csrf_token`; valid credentials set a new session and redirect by role. |
| POST | `/logout` | Signed-in | Requires `csrf_token`; clears session. |
| GET | `/student/dashboard` | Student | Student summary and announcements. |
| GET, POST | `/student/profile` | Student | POST accepts `full_name`, `email`, `phone`, `csrf_token`; updates only the signed-in student's profile. Department and role are not editable. |
| GET | `/student/requests` | Student | Lists only the signed-in student's requests. |
| GET | `/student/requests/<int:request_id>` | Student | Shows the request only when owned by the signed-in student; otherwise 404. |
| GET | `/admin/dashboard` | Administrator | Counts students, requests and announcements. |
| GET | `/admin/requests` | Administrator | Lists all student requests with student name, ID, title, date and status. |
| GET | `/admin/requests/<int:request_id>` | Administrator | Shows full request details and decision forms only while pending; unknown ID is 404. |
| POST | `/admin/requests/<int:request_id>/status` | Administrator | Requires `csrf_token` and `decision=approve` or `decision=reject`; changes only a pending request to approved or rejected, then redirects to its detail page. Unknown ID is 404; invalid decision is 400; already reviewed requests keep their status. |
| GET, POST | `/admin/announcements` | Administrator | Lists announcements; POST creates one from `title`, `body`, `csrf_token`. |
| GET, POST | `/admin/announcements/<int:announcement_id>/edit` | Administrator | POST updates `title` and `body` with `csrf_token`; unknown ID is 404. |
| POST | `/admin/announcements/<int:announcement_id>/delete` | Administrator | Deletes by ID with `csrf_token`; unknown ID is 404. |
| GET | `/api/requests/<int:request_id>` | Signed-in student | Returns JSON request data. Secure: owner only, other student's record is 403. Vulnerable: any signed-in student can read another synthetic student's record by ID. Unknown ID is 404. |
| POST | `/api/admin/announcements` | Signed-in user | JSON or form `title`, `body`, and CSRF token. Secure: administrator only, student is 403. Vulnerable: a student may create an announcement. Success is 201 with the created JSON record. |
| POST | `/api/profile` | Signed-in student | JSON or form profile fields and CSRF token. Secure: only `full_name`, `email`, `phone`; any `role` field is 403 with no change. Vulnerable: `role` may also be set to `student` or `admin` for the signed-in synthetic account. Success is 200 with user and profile JSON. |

Anonymous protected HTML GETs redirect to `/login`; authenticated wrong-role HTML requests return 403. HTML form token failures return 400. API calls without a signed-in session return JSON 401; wrong role/ownership returns JSON 403; malformed input or invalid CSRF returns JSON 400. The normal HTML error pages preserve their status codes.

## Security boundaries

Student identity and role come from the user row selected by the signed session's `user_id` on every request, never from a submitted user ID. The normal student HTML queries still include `student_id`; profile HTML updates still use the signed-in ID. Administrator HTML request review and announcement routes still require the admin role. The three API mode differences are confined to `app/lab_policy.py`; the vulnerable role update changes only the signed-in synthetic user's role through fixed SQL columns, so the next request immediately uses the new database role. The secure API profile update rejects fields outside its explicit allowlist before writing anything. SQL uses bound parameters for user-supplied values. Passwords are checked using Werkzeug and never stored in plaintext. Session cookies are HTTP-only with SameSite=Lax; local HTTP does not set the Secure cookie flag. Set a stable private secret key when persistence across restarts is needed. The published demo credentials and local-only binding mean this is an educational lab, not a production identity system.

Run `python -m scripts.reset_db` before a scenario to restore Alice and Bob as students, request IDs 101 and 201 with their original statuses, and the two original announcements. The manual procedure and expected comparison are in `docs/LAB_GUIDE.md`; the automated assessment and pending evidence slots are in `docs/SECURITY_REPORT.md`. `docs/PROJECT_ARCHITECTURE.md`, `docs/PRESENTATION_OUTLINE.md`, and `docs/presentation/CampusSecure_Presentation.pptx` complete the handoff package. `python -m scripts.build_presentation` regenerates the editable deck after installing `requirements-presentation.txt`.
