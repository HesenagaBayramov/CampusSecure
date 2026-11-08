# CampusSecure presentation — speaker notes

The PowerPoint is an editable seven-slide deck. All current visual elements are native PowerPoint text and shapes. Slide 5 contains labeled screenshot placeholders because manual Burp testing has not yet been performed. Do not describe those placeholders as evidence. After the authorized lab, replace them with genuine redacted captures and update the report's evidence table.

## Slide 1 — Introduction & Objectives

Introduce CampusSecure as a fictional university portal built for an isolated Information Security exercise. Explain the three learning goals: demonstrate authorization failures, compare mode behavior, and show the secure server-side checks. All users and records are synthetic.

## Slide 2 — CampusSecure Overview

Walk from browser to Flask to SQLite. Mention the four blueprints: authentication, student pages, administrator pages, and the three-endpoint lab API. The portal supports profiles, academic requests, announcements, and administrator review. Local Bootstrap and vanilla JavaScript provide the offline interface.

## Slide 3 — Laboratory Architecture

Describe the **planned** Kali/Burp → isolated Host-only network → Ubuntu/Flask/SQLite topology. The application binds to loopback by default and needs an explicitly selected private Host-only interface for VM access. Say that actual VM connectivity and isolation have **not yet been manually verified** in this project workspace.

## Slide 4 — Security Scenarios

The three cases test different authorization boundaries: Alice changes a request ID to read Bob's fictional request; Alice calls an administrator announcement endpoint; Alice adds `role=admin` to her own profile update. Both modes use the same endpoint names and database schema. Reset before each case.

## Slide 5 — Manual Penetration Testing

Explain the intended Burp workflow: reset, sign in, capture a fresh cookie and CSRF token, edit one request in Repeater, and compare responses plus SQLite state. The paired frames are **replaceable placeholders**, not screenshots. When real captures are available, redact session cookies and tokens, label mode and date, and insert the images over the placeholder frames.

## Slide 6 — Security Hardening

Use the three rows to explain cause and remediation. Secure Mode checks request ownership, requires the database administrator role, and rejects unauthorized profile fields before writing. The displayed HTTP statuses were asserted by automated Flask test-client tests; they are not yet manual Burp observations. Authentication and CSRF remain active in both modes.

## Slide 7 — Results & Conclusion

Report the executed Stage 5 automated results: **44 pytest tests passed, 2 subtests passed, 23 unittest tests passed, 0 unresolved failures**. These tests used temporary SQLite databases. Close by distinguishing the still-pending Ubuntu/Kali Host-only and Burp manual evidence from the verified automated results.
