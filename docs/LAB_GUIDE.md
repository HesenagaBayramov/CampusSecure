# CampusSecure isolated manual lab guide

## Scope and authorization

Use this guide only on a CampusSecure instance that you own or are explicitly authorized to test. The target must contain only the repository's fictional accounts and records. Keep the Ubuntu target and Kali testing VM on a deliberately isolated Host-only network. Do not route the lab to a campus, production, or public network. The three API scenarios below are the complete intended vulnerable surface; do not run automated scanners. The normal portal remains usable in either mode.

Demo credentials: `alice / Student123!`, `bob / Student123!`, `admin / Admin123!`. Never substitute real accounts or data. The `LAB_MODE` environment variable is read when Flask starts. Changing it requires stopping and restarting the server. Secure Mode is the default.

## 1. Prepare Ubuntu Server 24.04

Obtain the repository, Python packages, and Burp Suite before isolating the VM. On Ubuntu, from the project directory:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip iproute2 curl
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m scripts.seed_db
python -m pytest -q
```

`requirements-dev.txt` installs Flask and pytest; `requirements.txt` contains only the application dependency. The default SQLite file is `instance/campussecure.sqlite3`. `seed_db` adds missing fictional rows without overwriting edits. For a clean exercise, stop the server and use `python -m scripts.reset_db` instead. The reset restores Alice as a student with request **101 pending**, Bob as a student with request **201 approved**, admin as an administrator, and the two original announcements.

Before running Vulnerable Mode, disable or remove any NAT or bridged adapter on both VMs and verify that only the Host-only path remains. Keep the host firewall in place. If it blocks the chosen lab port, review the existing policy and arrange a narrowly scoped authorized rule for the Kali VM; do not disable the firewall.

## 2. Host-only network and connectivity

Use one Host-only virtual network shared by the Ubuntu server and Kali client. Example addresses below are placeholders: Ubuntu `192.168.56.10`, Kali `192.168.56.20`, both on `192.168.56.0/24`. Assign or verify them using your hypervisor and guest network configuration. Do not copy an example address unless it is actually assigned. A Host-only adapter allows communication inside the local lab segment; confirm no guest default route leads outside it. VirtualBox users can follow [Oracle's Host-only networking documentation](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/networkingdetails.html); use the equivalent isolated adapter in another hypervisor.

On **Ubuntu**, identify the adapter name and assigned address:

```bash
ip -br -4 addr
ip -4 route
```

On **Kali**, check its own address and reach the Ubuntu Host-only address:

```bash
ip -br -4 addr
ip -4 route
ping -c 2 192.168.56.10
```

The app refuses a non-loopback bind unless you explicitly set all three Host-only variables. It checks that the selected private IPv4 address belongs to the named local interface. The operator must verify that interface is truly Host-only. It never binds to `0.0.0.0`; debug and the reloader stay disabled.

For a local test entirely on Ubuntu, omit all three Host-only variables and use `http://127.0.0.1:5000/`. For two VMs, in the activated Ubuntu shell replace the values below with the verified adapter name and IP:

```bash
export CAMPUSSECURE_ENABLE_HOST_ONLY=1
export CAMPUSSECURE_HOST_ONLY_INTERFACE='enp0s8'
export CAMPUSSECURE_HOST_ONLY_IP='192.168.56.10'
```

Start **Secure Mode** in that shell:

```bash
python -m scripts.reset_db
LAB_MODE=secure python run.py
```

In another Ubuntu terminal, verify the listener and HTML page:

```bash
ss -ltnp | grep ':5000'
curl --noproxy '*' -i http://192.168.56.10:5000/login
```

On Kali, verify the same URL with `curl --noproxy '*' -i http://192.168.56.10:5000/login`. An HTTP `200` HTML login page confirms reachability. If `ping` is blocked by existing firewall policy but HTTP works, use the HTTP result. If HTTP fails, inspect the selected interface, address, routes, and existing firewall policy before proceeding.

For **Vulnerable Mode**, stop the server with `Ctrl+C`, reset the database, then restart:

```bash
python -m scripts.reset_db
LAB_MODE=vulnerable python run.py
```

Restart and reset again to return to Secure Mode. Use a new browser login after each restart; the default random session signing key invalidates previous cookies.

## 3. Burp browser, proxy, and session setup

Run Burp Suite on Kali. Its built-in browser is the simplest option: open **Proxy > Intercept > Open browser**, then visit `http://192.168.56.10:5000/login`. Burp's browser uses its proxy listener automatically. The default listener is normally on Kali's `127.0.0.1:8080`; keep it on loopback. If using a separate browser, configure that browser's HTTP proxy as Kali `127.0.0.1:8080` and ensure the target Host-only address is not in its proxy bypass list. No CA import is needed for this lab's plain HTTP target. See [Burp's browser](https://portswigger.net/burp/documentation/desktop/tools/burps-browser) and [proxy listener settings](https://portswigger.net/burp/documentation/desktop/settings/tools/proxy).

Set Burp's target scope to **only** `http://192.168.56.10:5000`. Use **Proxy > HTTP history** or **Proxy > Intercept** to inspect a request. Right-click a captured request and choose **Send to Repeater**, then edit and send it manually. Burp documents this flow in its [Repeater guide](https://portswigger.net/burp/documentation/desktop/tools/repeater/http-messages). Keep all Repeater targets pointed at the same Host-only IP and port.

For each scenario and mode:

1. Stop the server, run `python -m scripts.reset_db`, then start the selected `LAB_MODE` again.
2. In Burp's browser, sign in as the account named in the comparison table. Use a fresh browser session after each reset/restart.
3. After login, open `/student/profile` for Alice or `/admin/announcements` for admin. Copy the **current** hidden `csrf_token` value from the form HTML or from the corresponding request in Burp history. Login rotates the session, so the login form's old token is invalid for later POSTs.
4. Send the same browser session cookie in Repeater (`Cookie: session=<current-cookie>`). Include `X-CSRF-Token: <current-token>` on every API POST. The API also accepts a `csrf_token` JSON property or form field. Repeater can update `Content-Length` when editing a body.
5. Record the response status/body and inspect the SQLite result where specified. Reset before moving to the next scenario, especially after changing Alice's role.

The API returns JSON errors such as `{"error":"forbidden","message":"..."}`. An absent or stale session yields `401`; an invalid or missing CSRF token on an authenticated POST yields `400`. Those are setup failures, not the intended authorization comparison.

## 4. Manual scenario requests

The examples use `192.168.56.10:5000` as the verified Host-only target. Replace `<current-cookie>` and `<current-token>` with values captured **after** logging in. Do not reuse a token or cookie across a server restart.

### Scenario 1: request object authorization

Sign in as Alice. A baseline `GET /api/requests/101` returns `200` and JSON with `"id":101,"student_id":1`. In Repeater change only the ID to `201`:

```http
GET /api/requests/201 HTTP/1.1
Host: 192.168.56.10:5000
Cookie: session=<current-cookie>
```

Secure Mode returns **403** with `"error":"forbidden"`. Vulnerable Mode returns **200** with a JSON `request` containing `"id":201,"student_id":2` and Bob's fictional record. `GET /api/requests/999` returns **404** in either mode. Sign in as Bob after a reset to confirm he can read `201` in either mode. The ordinary `/student/requests/201` HTML page remains **404** for Alice in both modes.

### Scenario 2: administrator announcement operation

After a reset, sign in as Alice. Send this request in Repeater:

```http
POST /api/admin/announcements HTTP/1.1
Host: 192.168.56.10:5000
Cookie: session=<current-cookie>
X-CSRF-Token: <current-token>
Content-Type: application/json

{"title":"Stage 4 lab notice","body":"Synthetic announcement only"}
```

Secure Mode returns **403** and saves no row. Vulnerable Mode returns **201** with an `announcement` object whose `created_by` is Alice's user ID `1`; the row is saved. The admin dashboard remains hidden from Alice until any separate role change. After another reset, sign in as `admin / Admin123!` and send the same operation with the admin's cookie/token: it returns **201** in both modes, with `created_by:3`.

### Scenario 3: profile role field authorization

After a reset, sign in as Alice. First confirm an ordinary field works with `{"phone":"555 0199"}` sent to `POST /api/profile`; both modes return **200** and save the new phone. Reset again, sign back in, then send:

```http
POST /api/profile HTTP/1.1
Host: 192.168.56.10:5000
Cookie: session=<current-cookie>
X-CSRF-Token: <current-token>
Content-Type: application/json

{"role":"admin"}
```

Secure Mode returns **403**; Alice stays a student. Vulnerable Mode returns **200** with `"user":{"role":"admin",...}`; Alice's database role becomes `admin`. On the **next request using that same session**, `/admin/dashboard` returns **200** and `/student/dashboard` returns **403** because each request reloads the role from SQLite. A database reset restores Alice's student role. This operation changes only Alice's synthetic account.

## 5. Expected before/after comparison

Run each row from a fresh reset. `GET` requests do not change the database.

| Scenario | Account | Endpoint | Vulnerable response | Secure response | Database effect |
| --- | --- | --- | --- | --- | --- |
| Own request baseline | Alice | `GET /api/requests/101` | `200`, Alice record | `200`, Alice record | None |
| Object authorization | Alice | `GET /api/requests/201` | `200`, Bob record | `403`, forbidden JSON | None |
| Unknown object | Alice | `GET /api/requests/999` | `404` | `404` | None |
| Admin baseline | admin | `POST /api/admin/announcements` | `201` | `201` | One synthetic announcement, `created_by=3` |
| Admin function authorization | Alice | `POST /api/admin/announcements` | `201` | `403` | Vulnerable: one synthetic announcement, `created_by=1`; Secure: none |
| Ordinary profile update | Alice | `POST /api/profile` with `phone` | `200` | `200` | Alice's phone changes |
| Profile role authorization | Alice | `POST /api/profile` with `role=admin` | `200` | `403` | Vulnerable: Alice's role becomes admin; Secure: unchanged student |

Original state after every reset: Alice `student`, Bob `student`, admin `admin`; request `101 pending`, request `201 approved`; announcements `1` and `2` present. To inspect state from Ubuntu without a separate SQLite CLI, while the server is stopped run:

```bash
python - <<'PY'
from app import create_app
from app.db import get_db

with create_app().app_context():
    db = get_db()
    for table, columns in (
        ('users', 'id, username, role'),
        ('academic_requests', 'id, student_id, status'),
        ('announcements', 'id, title, created_by'),
    ):
        print(table, [tuple(row) for row in db.execute(f'SELECT {columns} FROM {table} ORDER BY id')])
PY
```

This inspection reads only the configured local database. If `CAMPUSSECURE_DATABASE` was set for the server, set it to the same file in this shell before inspecting.

## 6. Troubleshooting

| Observation | Check |
| --- | --- |
| Server refuses Host-only startup | Verify all three `CAMPUSSECURE_*HOST_ONLY*` variables, the private IPv4, and the interface name from `ip -br -4 addr`. The IP must be assigned to that interface. |
| Kali cannot load `/login` | Check Ubuntu `ss -ltnp`, both guests' Host-only addresses/routes, VM adapter assignment, and existing firewall policy. Never switch to `0.0.0.0`. |
| Burp history is empty | Use Burp's browser, or check the external browser HTTP proxy and bypass list. Confirm Burp's loopback listener is running. |
| Repeater returns `401` | Sign in again and copy the current `session` cookie; a restart with the default secret key invalidates old sessions. |
| Repeater returns `400` for API POST | Copy a post-login CSRF token and send it in `X-CSRF-Token`; verify JSON syntax and `Content-Type: application/json`. |
| Expected `403` or `201` differs | Check `LAB_MODE` in the server process, restart after changing it, reset fixtures, and verify the signed-in account. |
| Alice no longer sees student pages | A previous Vulnerable Mode role update promoted her. Stop, reset, restart, and sign in again. |
| Data differs from the table | Stop the server and run `python -m scripts.reset_db`. Check `CAMPUSSECURE_DATABASE` points at the file you are inspecting. |

## 7. Safe shutdown

Stop Flask with `Ctrl+C`. Close Burp's browser and Burp Suite. If the lab needs its original state, run `python -m scripts.reset_db` while the server is stopped. Verify no process listens on port 5000 (`ss -ltnp | grep ':5000'` should produce no match). Remove or disable the Host-only test adapter when the exercise is complete according to local lab policy. Leave the host firewall enabled. Do not export session cookies, captured traffic, or modified fictional databases to external services.
