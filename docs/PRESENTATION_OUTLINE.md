# CampusSecure — seven-slide university presentation outline

Use only evidence collected from the authorized isolated lab. Screenshots listed below are **recommendations, not existing artifacts**. Redact session cookies and CSRF tokens before placing captures on slides. The automated figures come from the Stage 5 local test run; replace or supplement them only with actual later results.

## Slide 1 — Title and objectives

**Key talking points**

- CampusSecure: a fictional university student portal for manual authorization testing.
- Objective: compare three narrow server-side decisions in Secure and Vulnerable modes.
- All accounts and records are synthetic; use is limited to the authorized local lab.

**Recommended visual:** portal login page screenshot, captured from the local instance during the presentation setup. **Placeholder — capture pending.**

**Presenter notes:** Introduce the academic scope and state that this is an educational comparison, not a test of a real university system.

## Slide 2 — Application architecture

**Key talking points**

- Flask factory and four blueprints: authentication, student, administrator, and JSON API.
- SQLite stores users, profiles, academic requests, and announcements.
- `LAB_MODE` changes three API authorization decisions without changing routes or schema.

**Recommended visual:** adapt the Mermaid component/network diagram from [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md). This diagram can be used without a screenshot.

**Presenter notes:** Explain that session identity and current role come from the database on each request. Point to the small policy module where mode behavior is selected.

## Slide 3 — Laboratory setup and tools

**Key talking points**

- Kali Linux with Burp Suite Proxy/Repeater connects to Ubuntu Server 24.04 over an isolated Host-only network.
- The application binds to loopback by default; an explicit verified Host-only adapter is required for VM access.
- Reset restores Alice, Bob, admin, request 101 pending, and request 201 approved.

**Recommended visual:** Host-only topology diagram; optionally add actual hypervisor adapter and IP/route screenshots after collection. **Screenshot placeholder — capture pending.**

**Presenter notes:** Describe the operator's responsibility to verify isolation and keep the firewall active. Mention that package installation is completed before the vulnerable lab is isolated.

## Slide 4 — Scenarios and testing method

**Key talking points**

| Scenario | Alice's modified request | Expected Secure / Vulnerable |
| --- | --- | --- |
| Object authorization | `GET /api/requests/201` | `403` / `200` |
| Function authorization | `POST /api/admin/announcements` | `403` / `201` |
| Profile field authorization | `POST /api/profile` with `role=admin` | `403` / `200` |

- Authenticate first, use the fresh session cookie and CSRF token, reset before each scenario, and inspect both response and SQLite state.

**Recommended visual:** compact comparison table from [SECURITY_REPORT.md](SECURITY_REPORT.md); no screenshot needed.

**Presenter notes:** Distinguish authentication from authorization. Explain why changing an object ID, invoking an admin function, and adding a role field each test a different boundary.

## Slide 5 — Manual Burp demonstrations

**Key talking points**

- Show the same request in Burp Repeater against each restarted mode.
- Record response status and relevant JSON fields; for POSTs, verify the database effect.
- Reset and sign in again between demonstrations, especially after Alice's role changes.

**Recommended visual:** paired, redacted Repeater captures for each scenario and a small before/after database table. **All manual screenshots and observations pending; do not label this slide “observed” until collected.**

**Presenter notes:** If the live VM/Burp session is unavailable, present this as a planned demonstration and use the automated result table on Slide 7. Never fabricate captures or claim a manual run occurred.

## Slide 6 — Secure Mode and remediation

**Key talking points**

- Request API checks `student_id` against the signed-in student.
- Announcement API requires the database role `admin`.
- Profile API rejects `role` and other fields outside the ordinary allowlist before writing.
- CSRF protection, bound SQL parameters, and HTML route checks remain active in both modes.

**Recommended visual:** a simple three-row “weak decision → secure decision” table from the report, or a short code excerpt from `app/lab_policy.py`.

**Presenter notes:** Explain that the fix belongs on the server. The sidebar's hidden administrator links are presentation behavior, not an access control.

## Slide 7 — Results and conclusion

**Key talking points**

- Stage 5 automated run: **44 pytest tests passed, 2 subtests passed; 23 unittest tests passed; 0 failures**.
- Tests checked response codes, SQLite persistence/reset, authentication, CSRF, page rendering, and the unchanged HTML authorization paths.
- Manual Ubuntu/Kali Host-only and Burp evidence is **pending** until performed and captured.
- Conclusion: the portal supports a repeatable, bounded educational comparison; Secure Mode enforces the three checks.

**Recommended visual:** an automated-results table plus a separate “manual evidence pending” label. Add genuine manual screenshots only after the lab exercise.

**Presenter notes:** State exactly what was tested with Flask's test client and what remains unverified. Close with the importance of server-side ownership, role, and field authorization in web applications.
