# CampusSecure — Stages 1–4

CampusSecure is a fictional university portal for a local Information Security lab. It provides a working backend, SQLite fixtures, session authentication, a responsive portal, and three controlled API authorization scenarios. All accounts and records are synthetic.

## Requirements

- Python 3 with `venv` and `pip` (Ubuntu Server 24.04: `sudo apt install python3 python3-venv python3-pip`); `iproute2` is also needed when selecting a Host-only interface on Linux
- A local terminal; no external services

## Ubuntu setup and startup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.seed_db
python run.py
```

Open `http://127.0.0.1:5000/` in the same machine. The default database is `instance/campussecure.sqlite3`. Run `python -m scripts.seed_db` again safely; it inserts missing fictional records without overwriting edits. To restore the original demo accounts, passwords and records, stop the server and run `python -m scripts.reset_db`.

On Windows PowerShell, use `python -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.\.venv\Scripts\python.exe -m scripts.seed_db`, and `.\.venv\Scripts\python.exe run.py` from the repository root.

## Demo accounts

| Username | Password | Role |
| --- | --- | --- |
| `alice` | `Student123!` | Student |
| `bob` | `Student123!` | Student |
| `admin` | `Admin123!` | Administrator |

These are published lab credentials. Do not use this application or database for real people or real university data.

## Tests

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m unittest discover -s tests -v
```

The pytest command runs the new Stage 4 security tests and the existing unittest suite. The unittest command runs the original suite separately. Tests create temporary SQLite databases and do not change the demo database. See [docs/LAB_GUIDE.md](docs/LAB_GUIDE.md) for the authorized manual verification procedure, expected responses, VM network setup, and reset steps.

## Interface and offline assets

The portal uses Jinja2 templates, Bootstrap 5.3.3, local CSS, and vanilla JavaScript. Bootstrap CSS, JavaScript, source maps, and its MIT license are stored under `app/static/vendor/bootstrap/`; no runtime CDN or internet connection is needed. The desktop sidebar becomes a collapsible menu on smaller screens. Student pages include profile editing, request search and status filtering, request details, and campus announcements. Administrator pages include an activity overview, academic request review, and announcement create, edit, and delete forms. Search and filter controls operate on records already authorized and rendered by the server; server-side ownership and role checks remain in force.

Administrators can open **Academic requests** from the sidebar or overview, inspect any student's request, and approve or reject a pending request. Decisions are saved in SQLite and appear on the student's request pages. A reviewed request cannot be changed again through the portal. The decision forms require the same session CSRF token as other state-changing forms.

## Local configuration

- `LAB_MODE=secure` is the default. `LAB_MODE=vulnerable` enables the three API lab variants described below. Set the variable before starting `python run.py`; stop and restart the application to change modes. There is no mode control in the website.
- `CAMPUSSECURE_DATABASE` selects a SQLite file. Its parent directory must exist.
- `CAMPUSSECURE_SECRET_KEY` can hold a stable, private session signing key. Without it, a new random key is created at startup, invalidating sessions after a restart.
- `run.py` binds to `127.0.0.1:5000` by default and always runs with debug disabled. For an isolated Host-only VM lab, set `CAMPUSSECURE_ENABLE_HOST_ONLY=1`, `CAMPUSSECURE_HOST_ONLY_IP` to the adapter's private IPv4 address, and `CAMPUSSECURE_HOST_ONLY_INTERFACE` to its local interface name. Startup checks that the IP is assigned to the named interface. You must also verify that the adapter is actually Host-only and isolated. The application never selects `0.0.0.0` automatically.

After verifying a VM adapter is Host-only, an Ubuntu non-loopback launch uses your actual interface name and address:

```bash
export CAMPUSSECURE_ENABLE_HOST_ONLY=1
export CAMPUSSECURE_HOST_ONLY_INTERFACE='<verified-interface-name>'
export CAMPUSSECURE_HOST_ONLY_IP='<verified-private-IPv4>'
LAB_MODE=vulnerable python run.py
```

On Ubuntu, start each mode from the activated virtual environment with a freshly restored fictional database:

```bash
python -m scripts.reset_db
LAB_MODE=secure python run.py
```

Stop the server before changing modes, reset again, then start the other mode:

```bash
python -m scripts.reset_db
LAB_MODE=vulnerable python run.py
```

On Windows PowerShell, use `$env:LAB_MODE = 'secure'` or `$env:LAB_MODE = 'vulnerable'` before `.\.venv\Scripts\python.exe run.py`. Restart after changing the variable.

## Stage 3 controlled API lab

The normal HTML portal keeps its existing ownership and role checks in both modes. Only these three JSON endpoints differ:

| Endpoint | Secure Mode | Vulnerable Mode |
| --- | --- | --- |
| `GET /api/requests/201` as Alice | 403 | 200, Bob's fictional request |
| `POST /api/admin/announcements` as Alice | 403 | 201, announcement created |
| `POST /api/profile` with `role=admin` as Alice | 403, role unchanged | 200, Alice's fictional role becomes admin |

Sign in through `/login` first. The API uses the same session cookie. For API POST requests, send the current session's CSRF token in the `X-CSRF-Token` header, a JSON `csrf_token` property, or a URL-encoded `csrf_token` form field. After login, load a portal page to obtain the current token from its hidden form field; login creates a new session and token. Send JSON or URL-encoded form fields. The API returns JSON success and error bodies. Use Burp Suite Proxy or Repeater only against the authorized isolated instance. Reset the database before each scenario, especially after changing a synthetic role.

## Current routes

HTML routes: `/login`, `/logout` (POST), `/student/dashboard`, `/student/profile`, `/student/requests`, `/student/requests/<id>`, `/admin/dashboard`, `/admin/requests`, `/admin/requests/<id>`, `/admin/requests/<id>/status` (POST), `/admin/announcements`, `/admin/announcements/<id>/edit`, and `/admin/announcements/<id>/delete` (POST). The three additional API contracts are `/api/requests/<id>`, `/api/admin/announcements` (POST), and `/api/profile` (POST). See [PROJECT_SPEC.md](PROJECT_SPEC.md) for full status codes and field rules.

The original fixture has Alice's request **#101 pending** and Bob's request **#201 approved**. `python -m scripts.reset_db` restores both statuses along with the other fictional data.

See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full staged plan and endpoint contracts.
