# CampusSecure web presentation

Open [index.html](index.html) directly in a modern browser. The presentation is a standalone local file: it needs no server, internet connection, build tool, package installation, or Flask process. For a classroom display, use a 16:9 screen or projector when possible.

## Presenting

| Action | Control |
| --- | --- |
| Next / previous slide | Right / Left arrow, or the on-screen arrow buttons |
| Next slide | Space when focus is outside an interactive button |
| First / last slide | Home / End |
| Jump to a slide | Select one of the seven progress dots |
| Full screen | Full-screen button or `F`; use `Esc` to exit |
| Touch display | Swipe left or right on the slide background |

Slide 4's scenario cards reveal further details without leaving the slide. Slide 6's **Vulnerable / Secure** switch changes an illustrative policy comparison; it does **not** contact or control the Flask application. Motion is reduced automatically when the operating system requests reduced motion. If JavaScript is unavailable, all seven slides remain readable in document order.

## Burp screenshot placeholders

Slide 5 deliberately contains **no real screenshot or manual test result**. After completing the authorized Host-only lab, redact session cookies and CSRF tokens from genuine captures.

- For a temporary preview during a presentation, select **Insert local capture** in each slot. The image stays in this browser tab and is not uploaded or saved by the presentation.
- To include captures permanently in the local presentation, copy redacted PNG, JPG, or WebP files into `assets/screenshots/`. In [index.html](index.html), add `data-src="./assets/screenshots/your-file.png"` to the corresponding `<img class="capture-image">`. Reload the page. The script only loads local paths under `assets/screenshots/`.
- Keep the placeholder until evidence exists. Do not label expected or automated results as a completed Burp observation.

`assets/images/` and `assets/icons/` are reserved for optional locally stored artwork. Current diagrams and icons are editable HTML/CSS and inline SVG, so the presentation has no runtime asset downloads.

## Customizing content

Edit slide text and markup in [index.html](index.html). Update the matching scenario-detail and illustrative mode descriptions in [script.js](script.js) if those slide labels change. Colors, typography, layout, and motion are in [style.css](style.css). Keep the presentation's seven-slide structure and verify every technical claim against the repository's `docs/SECURITY_REPORT.md`, `PROJECT_SPEC.md`, and actual test output.

The displayed 44 pytest tests, 2 subtests, and 23 unittest tests come from previously recorded successful runs; the two test runners overlap and must not be added as independent tests. Ubuntu/Kali connectivity and Burp screenshots remain pending manual verification.
