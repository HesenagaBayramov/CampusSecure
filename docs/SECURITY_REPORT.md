# 1. CampusSecure: Controlled Authorization Assessment

**University Information Security project · Stage 5 report · 8 November 2026**

**Evidence status:** automated Flask test-client results are recorded below. Burp Suite and Ubuntu/Kali Host-only VM observations have **not** been collected in this workspace; designated evidence slots remain open. This report assesses a fictional educational application, not a production university system.

## 2. Executive summary

CampusSecure is a synthetic student portal with two startup modes. Secure Mode enforces request ownership, administrator role checks, and a profile field allowlist. Vulnerable Mode intentionally relaxes one decision at each of three specific JSON endpoints so students can observe Broken Object Level Authorization, Broken Function Level Authorization, and Mass Assignment / Improper Field Authorization. Authentication and CSRF checks continue to operate in both modes.

In the Stage 5 local automated run, `python -m pytest -q` reported **44 passed, 2 subtests passed, 0 failed**. The original unittest runner reported **23 passed, 0 failed**. Tests used temporary SQLite files and Flask's test client. They verify the documented status differences and database effects. No Burp screenshots or live Host-only network measurements are represented as completed evidence.

## 3. Project objectives

1. Provide a realistic, functional portal for fictional students and administrators.
2. Compare three narrow server-side authorization decisions using the same routes, interface, and database schema.
3. Explain the root causes, impact, and secure code behavior in terms a computer engineering student can reproduce.
4. Keep all activity within an authorized, isolated local laboratory and restore known data before each comparison.

## 4. Authorized scope

The target is the local CampusSecure application and its seeded SQLite database only. In-scope comparisons are `GET /api/requests/<request_id>`, `POST /api/admin/announcements`, and `POST /api/profile`. Normal HTML portal functions are checked for regression. No external hosts, campus systems, real accounts, automated scanners, data exfiltration, SQL injection, command execution, or arbitrary file operations are part of this assessment.

## 5. Laboratory environment

The intended demonstration topology is Kali Linux with Burp Suite connected over a verified Host-only virtual network to Ubuntu Server 24.04 running Flask and SQLite. The application defaults to `127.0.0.1:5000`; a non-loopback bind requires explicit Host-only variables and a private IPv4 assigned to the named interface. The operator must additionally verify the hypervisor network mode and firewall policy. The runtime uses Flask's development server with debug and reloader disabled.

The **executed Stage 5 automated checks** ran in the local Windows project virtual environment using Flask's test client. Each relevant test created a temporary SQLite database. A real Ubuntu/Kali network, Burp browser, and Repeater session were **not available for execution** here. The [lab guide](LAB_GUIDE.md) contains the planned setup and procedure.

## 6. Testing methodology

The automated method creates isolated application instances in both `LAB_MODE` values, seeds deterministic data, signs in with fictional accounts, supplies valid session CSRF tokens for POSTs, sends requests through Flask's test client, and checks HTTP status, JSON content, and SQLite state. Reset tests alter synthetic rows and verify that `reset_db` restores the original roles, request IDs/statuses, credentials, and announcements. Page rendering uses strict Jinja undefined-variable handling and checks local assets.

The **planned manual method** starts one mode at a time on the isolated Host-only interface, resets before each scenario, signs in through Burp's browser, captures a fresh post-login cookie and CSRF token, edits one request in Repeater, and records before/after responses and database state. This manual method remains pending; it is not counted among the executed results.

## 7. Tools and technologies

Python 3, Flask, Werkzeug password hashing, SQLite, Jinja2, Bootstrap 5.3.3, vanilla JavaScript, pytest, unittest, and Flask's test client are used in the repository. Burp Suite Proxy and Repeater are the specified tools for the future manual demonstration. No external API is integrated into the application. The frontend assets are served locally.

## 8. Application architecture

`app.create_app` builds the Flask instance and registers `auth`, `student`, `admin`, and `api` blueprints. `app/db.py` owns the SQLite schema and fixture operations. `app/lab_policy.py` contains the three mode-dependent authorization decisions. HTML views use Jinja templates and local static assets; API views return JSON. `run.py` selects the bind address and always disables debug mode. See [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) for the component diagram, data model, and endpoint inventory.

## 9. Authentication and authorization design

Passwords are stored as Werkzeug hashes. Successful login stores a user ID in a signed Flask session; each request reloads that user's current role from SQLite. This makes a synthetic role update visible on the next request. The session also carries a CSRF token required on POST actions. Anonymous protected API calls return JSON `401`; wrong-role and ownership failures return JSON `403`. Normal student HTML queries scope requests to the signed-in student, and administrator HTML routes use a server-side role decorator in both modes.

The signed session protects integrity but does not make the published lab credentials suitable for real deployments. Local HTTP does not set a Secure cookie flag; the lab must remain isolated and contain synthetic records only.

## 10. Security scenarios

### Scenario A — Broken Object Level Authorization (IDOR)

**Endpoint:** `GET /api/requests/<request_id>`. Alice owns request 101; Bob owns request 201. Both modes require a signed-in student and look up the ID in SQLite. In Vulnerable Mode, `may_read_student_request` returns true for another student's record because the mode bypasses the owner comparison. Changing `101` to `201` therefore exposes Bob's fictional request. In Secure Mode, the function requires the signed-in student ID to equal `student_id` from the request row, so Alice receives `403` for 201. An unknown ID returns `404` in both modes. The ordinary HTML detail route retains its owner-scoped SQL query in both modes.

### Scenario B — Broken Function Level Authorization

**Endpoint:** `POST /api/admin/announcements`. In Vulnerable Mode, `may_create_announcement` treats a signed-in student as authorized for this one administrator API operation. Alice can create a synthetic announcement despite lacking the administrator role. In Secure Mode, only a database role of `admin` is accepted, so Alice receives `403` and no row is inserted. An authenticated administrator receives `201` in both modes. The HTML announcement management pages remain administrator-only.

### Scenario C — Mass Assignment / Improper Field Authorization

**Endpoint:** `POST /api/profile`. Ordinary editable fields are `full_name`, `email`, and `phone`. Vulnerable Mode additionally accepts `role`, allowing Alice to submit `{"role":"admin"}` and change her own synthetic user row. Because subsequent requests reload the role from SQLite, the same session then satisfies administrator HTML authorization. Secure Mode rejects any submitted `role` field with `403` before writing any profile value. It also rejects other fields outside the allowlist. The operation never selects another user from a client-supplied ID.

## 11. Technical root causes

The shared failure pattern is treating successful authentication as sufficient authorization for a specific object, function, or field. The mode-specific policy functions in `app/lab_policy.py` make each missing decision visible without changing routing or storage:

| Scenario | Missing decision in Vulnerable Mode | Decision enforced in Secure Mode |
| --- | --- | --- |
| Object | No comparison of signed-in student ID with the request row's `student_id` | Require owner equality for the requested object |
| Function | Student role accepted for a named administrator API action | Require database role `admin` before insert |
| Field | Submitted `role` accepted alongside ordinary profile fields | Reject `role` and every field outside the ordinary allowlist before writes |

## 12. Risk assessment

| Scenario | Qualitative severity if deployed with real data | Potential impact | Lab boundary |
| --- | --- | --- | --- |
| Object authorization | High | Disclosure of another student's request details | Only Alice and Bob's fictional records exist in the fixture |
| Function authorization | High | Unauthorized publication of content presented as a campus announcement | Only synthetic announcements in isolated SQLite |
| Profile role authorization | Critical | Self-assigned administrator role and access to administrator functions | Only the signed-in fictional account can be changed by this endpoint |

These are **conditional real-world impact ratings**, not evidence that a production system was affected. The deliberate Vulnerable Mode is unsuitable for public or real-data use.

## 13. Security impact

An object authorization failure can disclose another student's request text and status. A function authorization failure can publish an announcement under a student account, affecting the integrity of campus communications. A field authorization failure can elevate a student to administrator, changing which server-side routes that account can use. Combining a synthetic role change with later administrator access is confirmed in the test client; it is not a claim of a manually executed Burp attack. All observed data in this project is fictional.

## 14. Secure implementation and remediation

| Weak decision in Vulnerable Mode | Secure Mode control |
| --- | --- |
| Request exists, but ownership is skipped | Compare `g.user['id']` with the row's `student_id` on every API read |
| User is authenticated, but administrator role is skipped | Require the server-loaded `admin` role before inserting an announcement |
| Submitted `role` is accepted in a profile update | Allow only `full_name`, `email`, and `phone`; reject `role` and unknown fields before database writes |

The code confines these decisions to `app/lab_policy.py`; it does not duplicate the application. Bound SQL parameters, input length checks, CSRF validation, and transaction use support the narrow authorization controls. The normal HTML routes retain their own role and ownership checks. Switching to Secure Mode requires a process restart and a database reset to remove effects created during a prior vulnerable exercise.

## 15. Before/after results

The following statuses and database effects were **observed by automated Flask test-client assertions** in Stage 5. They are also the **expected outcomes** for the pending manual Burp procedure when the fixture is reset before each row.

| Scenario and account | Endpoint | Vulnerable Mode | Secure Mode | Database effect |
| --- | --- | --- | --- | --- |
| Alice reads own request | `GET /api/requests/101` | `200` | `200` | None |
| Alice reads Bob's request | `GET /api/requests/201` | `200`, Bob record | `403` | None |
| Alice requests unknown ID | `GET /api/requests/999` | `404` | `404` | None |
| Admin creates announcement | `POST /api/admin/announcements` | `201` | `201` | Row with `created_by=3` |
| Alice creates announcement | `POST /api/admin/announcements` | `201` | `403` | Vulnerable: row with `created_by=1`; Secure: no row |
| Alice edits ordinary profile field | `POST /api/profile` with `phone` | `200` | `200` | Alice's phone changes |
| Alice submits `role=admin` | `POST /api/profile` | `200` | `403` | Vulnerable: Alice becomes admin; Secure: role remains student |

The test suite also confirmed that the secure mixed-field profile request makes no partial write, missing CSRF tokens receive `400`, invalid credentials do not authenticate, logout ends access, and reset restores request 101 as pending and 201 as approved.

## 16. Automated verification record

**Execution environment:** local Windows project workspace and its `.venv`; no live Host-only VM traffic. Commands executed from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Observed outputs: pytest **44 passed, 2 subtests passed**; unittest **23 tests, OK**; `pip check` reported **No broken requirements found**. All commands exited with code 0. These results are from this Stage 5 audit and do not substitute for the pending manual VM/Burp evidence. The tests use isolated temporary SQLite databases, not `instance/campussecure.sqlite3`.

## 17. Manual verification evidence placeholders — not yet collected

Use [LAB_GUIDE.md](LAB_GUIDE.md) to collect each item on the authorized isolated VMs. Keep screenshots and request/response exports local, redact session cookies and CSRF tokens before including them in a submission, and label the selected mode and reset state. **No evidence file is present or claimed here.**

| Evidence ID | Required artifact | Status |
| --- | --- | --- |
| M1 | Hypervisor Host-only adapter settings and Ubuntu/Kali IP/routes; demonstrate no public route | **PENDING — insert screenshot and date** |
| M2 | Ubuntu listener showing the selected Host-only IP, port 5000, and debug off | **PENDING — insert screenshot and date** |
| M3 | Burp Repeater: Alice requests 201 in Vulnerable Mode (`200`) and Secure Mode (`403`) | **PENDING — insert paired screenshots and date** |
| M4 | Burp Repeater: Alice posts an announcement in both modes; SQLite before/after row check | **PENDING — insert paired screenshots and date** |
| M5 | Burp Repeater: Alice submits `role=admin` in both modes; SQLite role before/after check | **PENDING — insert paired screenshots and date** |
| M6 | Reset confirmation showing Alice/Bob roles, requests 101/201, and original announcements | **PENDING — insert screenshot and date** |

Suggested local evidence directory after collection: `docs/evidence/` (create it only when evidence exists). Keep raw captures outside public repositories unless your university's submission rules explicitly permit them.

## 18. Limitations

- No Burp Suite session, Kali-to-Ubuntu connection, real Host-only adapter inspection, or browser visual review was executed in this Stage 5 environment.
- Host-only bind logic was covered by automated tests, including mocked interface address checks. The program cannot verify the hypervisor's adapter type or external firewall state.
- Flask's built-in server, published demo credentials, and HTTP transport are acceptable only for the isolated synthetic exercise; this is not a production security certification.
- The assessment concentrates on three specified authorization scenarios and regression behavior. It is not a comprehensive penetration test of every possible web weakness.
- Automated results show local behavior at the tested revision. Manual evidence must be gathered after a reset on the actual demonstration VMs.

## 19. Conclusion

The implemented application provides a repeatable comparison of three common authorization failures while preserving normal portal functionality. Stage 5 automated verification passed for both modes and for reset, authentication, page rendering, and database effects. The remaining delivery activity is to perform the authorized Host-only Ubuntu/Kali Burp walkthrough, insert genuine evidence into the marked slots, and present the observed comparison. Until that occurs, manual results remain **unverified**.
