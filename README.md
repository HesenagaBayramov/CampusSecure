# CampusSecure — University Web Security Laboratory

CampusSecure is a fictional university student portal for an authorized, isolated Information Security laboratory. Students can sign in, view a dashboard, edit contact details, follow academic requests, and read announcements. Administrators can review requests and manage announcements. The same Flask application supports three controlled API authorization scenarios for manual comparison with Burp Suite.

**Academic purpose:** demonstrate how server-side ownership, role, and field authorization affect HTTP responses and database state. `LAB_MODE=secure` is the default. `LAB_MODE=vulnerable` changes only the three documented API decisions for this synthetic lab. The interface, routes, and schema are the same in both modes. No real people, university systems, external APIs, cloud services, or public targets are involved.

## Technology and features

| Area | Implementation |
| --- | --- |
| Backend | Python 3, Flask application factory and blueprints |
| Data | SQLite with bound SQL parameters and repeatable fictional fixtures |
| Identity | Werkzeug password hashes, Flask signed cookie sessions, server-side role checks |
| Browser protection | Session CSRF token on POST forms and API POST requests |
| Frontend | Jinja2, HTML5, CSS3, Bootstrap 5.3.3 served locally, vanilla JavaScript |
| Verification | pytest and unittest with temporary SQLite databases |

The portal includes login/logout; student dashboard, profile, request list and detail pages; administrator dashboard, request approval/rejection, and announcement create/edit/delete; responsive navigation and error pages. The lab API offers request retrieval, announcement creation, and profile updates. Academic request IDs are stable: Alice owns **101 (pending)** and Bob owns **201 (approved)** after every reset.

## Repository layout

```text
CampusSecure/
├── app/
│   ├── __init__.py              # Flask factory, session loading, CSRF, errors
│   ├── auth.py                  # Login, logout, HTML role decorator
│   ├── student.py               # Student HTML routes
│   ├── admin.py                 # Administrator HTML routes
│   ├── api.py                   # Three JSON lab endpoints
│   ├── lab_policy.py            # Mode-specific authorization decisions
│   ├── db.py                    # SQLite schema, seed and reset functions
│   ├── templates/              # Base, login, student, admin and error pages
│   └── static/                 # Portal CSS/JS, SVG icons, local Bootstrap
├── scripts/
│   ├── seed_db.py
│   └── reset_db.py
├── tests/
│   ├── test_app.py
│   ├── test_lab_modes.py
│   └── test_security.py
├── docs/
│   ├── LAB_GUIDE.md
│   ├── SECURITY_REPORT.md
│   ├── PROJECT_ARCHITECTURE.md
│   └── PRESENTATION_OUTLINE.md
├── run.py
├── requirements.txt
├── requirements-dev.txt
└── PROJECT_SPEC.md
```

SQLite data is created at `instance/campussecure.sqlite3` by default. The `instance/` directory, databases, and virtual environment are local artifacts excluded by `.gitignore`.

## Ubuntu Server 24.04 setup

Use a local checkout of this repository. Obtain Python packages and tools before disconnecting any temporary installation network. In the repository root:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip iproute2 curl
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.seed_db
```

`seed_db` creates the SQLite schema and inserts missing demo rows. It is idempotent and keeps existing edits. To restore all original roles, passwords, requests, statuses, profiles, and announcements, stop the server and run:

```bash
python -m scripts.reset_db
```

For testing tools, install the separate development requirements:

```bash
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains only Flask; `requirements-dev.txt` adds pytest. No runtime download is needed for the frontend assets.

### Fictional demo accounts

| Username | Password | Role |
| --- | --- | --- |
| `alice` | `Student123!` | Student |
| `bob` | `Student123!` | Student |
| `admin` | `Admin123!` | Administrator |

These published credentials are for the isolated lab only. Passwords are stored as Werkzeug hashes, never plaintext.

## Start a local instance

From an activated Ubuntu virtual environment, reset before a comparison and start **Secure Mode**:

```bash
python -m scripts.reset_db
LAB_MODE=secure python run.py
```

Open `http://127.0.0.1:5000/login` on the same machine. Omitting `LAB_MODE` also selects Secure Mode. Stop with `Ctrl+C` before changing modes. To start **Vulnerable Mode**:

```bash
python -m scripts.reset_db
LAB_MODE=vulnerable python run.py
```

Changing `LAB_MODE` requires an application restart; there is no website switch. Use a fresh login after a restart. `run.py` binds to `127.0.0.1:5000` by default, with Flask debug and the reloader disabled. An unsupported mode fails at startup.

### Explicit Host-only VM interface

For the authorized Ubuntu/Kali demonstration, place both VMs on the same **isolated Host-only** network. Verify the Ubuntu adapter's real name and private IPv4 address with `ip -br -4 addr`; replace the placeholders below with those values. Disconnect NAT and bridged adapters before running Vulnerable Mode, and confirm the lab has no public route. Leave host firewall protections enabled.

```bash
export CAMPUSSECURE_ENABLE_HOST_ONLY=1
export CAMPUSSECURE_HOST_ONLY_INTERFACE='<verified-interface-name>'
export CAMPUSSECURE_HOST_ONLY_IP='<verified-private-IPv4>'
python -m scripts.reset_db
LAB_MODE=secure python run.py
```

For Vulnerable Mode, stop the server, reset again, and run `LAB_MODE=vulnerable python run.py` with the same verified Host-only variables. Startup rejects incomplete settings, unspecified addresses such as `0.0.0.0`, and an address not assigned to the named interface. The program cannot prove a hypervisor adapter is Host-only; the operator must verify that network property. See [the lab guide](docs/LAB_GUIDE.md) for VM connectivity, Burp Proxy/Repeater setup, request examples, and shutdown.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `LAB_MODE` | `secure` | `secure` or `vulnerable`; read once at startup |
| `CAMPUSSECURE_DATABASE` | `instance/campussecure.sqlite3` | Alternate SQLite file; its parent directory must exist |
| `CAMPUSSECURE_SECRET_KEY` | Random key at startup | Stable private session key when sessions must survive a restart |
| `CAMPUSSECURE_ENABLE_HOST_ONLY` | Unset | Must be `1` for a non-loopback bind |
| `CAMPUSSECURE_HOST_ONLY_INTERFACE` | Unset | Explicit named local Host-only adapter |
| `CAMPUSSECURE_HOST_ONLY_IP` | Unset | Private IPv4 assigned to that adapter |

The development entry point is for this local lab, not deployment on a public interface. Do not use the published credentials or the HTTP session configuration for real data.

## Controlled security comparison

Sign in through `/login`; API calls use the same session cookie. For API POST requests, send the **post-login** CSRF token in `X-CSRF-Token`, a JSON `csrf_token` field, or a form `csrf_token` field. Obtain it from a portal form after login because login rotates the session. Reset the database before each scenario.

| Scenario as Alice | Endpoint | Vulnerable Mode | Secure Mode |
| --- | --- | --- | --- |
| Read Bob's request | `GET /api/requests/201` | `200`, Bob's fictional record | `403` |
| Create an administrator announcement | `POST /api/admin/announcements` | `201`, row saved | `403`, no row saved |
| Submit `role=admin` in profile update | `POST /api/profile` | `200`, Alice's role saved as admin | `403`, role unchanged |

Normal authentication, CSRF checks, and ordinary HTML role/ownership checks remain active in both modes. The complete endpoint contracts are in [PROJECT_SPEC.md](PROJECT_SPEC.md). The [lab guide](docs/LAB_GUIDE.md) gives the manual procedure and expected database effects.

## Automated tests

After installing `requirements-dev.txt`, run all tests from the repository root:

```bash
python -m pytest -q
```

The original unittest suite can also be run separately:

```bash
python -m unittest discover -s tests -v
```

Both suites use temporary SQLite databases and do not mutate the default demonstration database. Stage 5 verification results and distinctions between automated and pending manual evidence are recorded in [the security report](docs/SECURITY_REPORT.md).

## Troubleshooting and safety

| Symptom | Check |
| --- | --- |
| `ModuleNotFoundError` | Activate `.venv`; install `requirements.txt` or `requirements-dev.txt` for tests. |
| `no such table: users` | From the repository root, run `python -m scripts.seed_db` or `python -m scripts.reset_db`. |
| Login redirects unexpectedly after restart | The default secret key changes on restart; sign in again. |
| API POST returns `400` | Use a fresh CSRF token from a page loaded after login and a valid JSON/form body. |
| API returns `401` | Sign in again; check the session cookie. |
| An expected mode result differs | Check the server's `LAB_MODE`, restart it, reset data, and use the correct demo account. |
| Host-only startup fails | Verify all three Host-only settings and the selected adapter's assigned private IPv4. |
| Kali cannot connect | Check the two VM adapters, IP routes, Flask listener, and existing firewall policy. Do not bind to `0.0.0.0` or disable the firewall. |

Use only the fictional seed data and an explicitly authorized, isolated target. Do not run automated scanners or connect the vulnerable instance to a public or university network. Finish by stopping Flask, closing Burp, and resetting the database if the demo should return to its original state.

Additional documents: [architecture](docs/PROJECT_ARCHITECTURE.md), [security report](docs/SECURITY_REPORT.md), and [seven-slide presentation outline](docs/PRESENTATION_OUTLINE.md).
