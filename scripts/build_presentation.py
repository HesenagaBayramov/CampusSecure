"""Build the editable CampusSecure university presentation.

Install once with ``python -m pip install -r requirements-presentation.txt``.
Run from the repository root: ``python -m scripts.build_presentation``.
All diagrams and placeholders are native PowerPoint shapes; no screenshots are
embedded or claimed as evidence.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "presentation" / "CampusSecure_Presentation.pptx"
PRESENTATION_TITLE = (
    "CampusSecure — Manual Web Application Penetration Testing "
    "and Security Hardening Using Burp Suite"
)
SLIDE_W = 13.333
SLIDE_H = 7.5

NAVY = "091426"
NAVY_2 = "0E1B30"
CARD = "13243C"
CARD_2 = "172C47"
WHITE = "F4F8FF"
MUTED = "A7B8CF"
FAINT = "7087A3"
BLUE = "4A94FF"
TEAL = "35D6C2"
AMBER = "FFC276"
RED = "FF7F88"
EDGE = "2A3C56"
FONT = "Aptos"
FONT_DISPLAY = "Aptos Display"


def rgb(hex_value):
    return RGBColor.from_string(hex_value)


def add_box(slide, x, y, w, h, fill=CARD, line_color=None, radius=True,
            line_width=1.0, dash=None, name=None):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if line_color:
        shape.line.color.rgb = rgb(line_color)
        shape.line.width = Pt(line_width)
        if dash:
            shape.line.dash_style = dash
    else:
        shape.line.fill.background()
    if name:
        shape.name = name
    return shape


def add_circle(slide, x, y, d, fill, line_color=None, line_width=1.0):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if line_color:
        shape.line.color.rgb = rgb(line_color)
        shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def add_line(slide, x1, y1, x2, y2, color=EDGE, width=1.2, dash=None):
    shape = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(width)
    if dash:
        shape.line.dash_style = dash
    return shape


def add_text(slide, value, x, y, w, h, size=18, color=WHITE, bold=False,
             align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP, font=FONT,
             margin=0, name=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shape.name = name
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.vertical_anchor = valign
    frame.margin_left = Inches(margin)
    frame.margin_right = Inches(margin)
    frame.margin_top = Inches(margin)
    frame.margin_bottom = Inches(margin)
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = value
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    return shape


def add_pill(slide, value, x, y, w, fill=CARD_2, color=TEAL,
             size=10.5, h=0.35, line_color=None):
    add_box(slide, x, y, w, h, fill, line_color)
    add_text(slide, value, x + 0.09, y + 0.01, w - 0.18, h - 0.02,
             size, color, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)


def add_logo(slide):
    add_box(slide, 0.55, 0.36, 0.36, 0.36, BLUE, radius=True)
    add_text(slide, "C", 0.56, 0.37, 0.34, 0.33, 17, NAVY, True,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, FONT_DISPLAY)
    add_text(slide, "CAMPUSSECURE", 1.04, 0.38, 2.2, 0.25,
             13.5, WHITE, True, font=FONT_DISPLAY)


def add_footer(slide, number, section):
    add_line(slide, 0.55, 7.03, 12.78, 7.03, EDGE, 0.8)
    add_text(slide, "CAMPUSSECURE  /  INFORMATION SECURITY LAB", 0.58, 7.13,
             5.2, 0.18, 8.5, FAINT, True)
    add_text(slide, section.upper(), 9.3, 7.13, 2.7, 0.18,
             8.5, FAINT, True, PP_ALIGN.RIGHT)
    add_text(slide, f"{number:02d} / 07", 12.02, 7.1, 0.7, 0.2,
             9, MUTED, True, PP_ALIGN.RIGHT)


def new_slide(presentation, number, section):
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(NAVY)
    add_box(slide, 0, 0, SLIDE_W, 0.06, BLUE, radius=False)
    add_logo(slide)
    add_footer(slide, number, section)
    return slide


def header(slide, eyebrow, title, subtitle=None):
    add_text(slide, eyebrow.upper(), 0.62, 0.92, 6.0, 0.22,
             10, TEAL, True)
    add_text(slide, title, 0.6, 1.19, 12.0, 0.62,
             31, WHITE, True, font=FONT_DISPLAY)
    if subtitle:
        add_text(slide, subtitle, 0.63, 1.82, 11.8, 0.36,
                 13.5, MUTED)


def slide_one(presentation):
    slide = new_slide(presentation, 1, "Introduction")
    add_text(slide, "UNIVERSITY INFORMATION SECURITY PROJECT", 0.74, 1.11,
             6.9, 0.24, 11.2, TEAL, True)
    add_text(slide, "CampusSecure —", 0.69, 1.55, 7.6, 0.78,
             48, WHITE, True, font=FONT_DISPLAY)
    add_box(slide, 0.74, 2.49, 0.64, 0.06, TEAL, radius=False)
    add_text(slide, "Manual Web Application Penetration Testing and Security Hardening Using Burp Suite",
             0.74, 2.78, 7.1, 1.52, 26, WHITE, True, font=FONT_DISPLAY)
    add_text(slide, "A fictional university portal for three controlled authorization comparisons.",
             0.76, 4.68, 6.55, 0.6, 16, MUTED)

    # Concentric editable shapes make the lab theme visible without a bitmap.
    add_circle(slide, 8.62, 1.47, 3.83, NAVY_2, EDGE, 1.5)
    add_circle(slide, 9.05, 1.9, 2.97, CARD, BLUE, 1.9)
    add_circle(slide, 9.48, 2.33, 2.11, NAVY_2, TEAL, 1.4)
    add_text(slide, "03", 9.75, 2.77, 1.57, 0.69, 43, WHITE, True,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, FONT_DISPLAY)
    add_text(slide, "CONTROLLED\nSCENARIOS", 9.36, 3.59, 2.36, 0.56,
             10.5, MUTED, True, PP_ALIGN.CENTER)
    add_pill(slide, "SYNTHETIC DATA", 8.8, 5.66, 1.67, CARD_2, TEAL, 9.5)
    add_pill(slide, "ISOLATED LAB", 10.58, 5.66, 1.55, CARD_2, BLUE, 9.5)
    add_text(slide, "DEMONSTRATE   /   COMPARE   /   HARDEN", 0.76, 6.12,
             6.9, 0.28, 12.5, BLUE, True)
    return slide


def slide_two(presentation):
    slide = new_slide(presentation, 2, "Application overview")
    header(slide, "01  /  CampusSecure overview", "A portal with a narrow lab surface",
           "The same Flask application serves student, administrator and API workflows.")

    # Native PowerPoint component flow.
    components = [
        (0.65, 2.48, 3.18, "BROWSER", "Student + admin portal", BLUE),
        (5.05, 2.48, 3.22, "FLASK FACTORY", "4 blueprints + lab policy", TEAL),
        (9.48, 2.48, 3.18, "SQLITE", "Users, profiles, requests, news", BLUE),
    ]
    add_line(slide, 3.84, 3.13, 5.03, 3.13, BLUE, 2.4)
    add_line(slide, 8.28, 3.13, 9.46, 3.13, TEAL, 2.4)
    for x, y, w, label, detail, accent in components:
        add_box(slide, x, y, w, 1.33, CARD, EDGE)
        add_box(slide, x, y, 0.07, 1.33, accent, radius=False)
        add_text(slide, label, x + 0.23, y + 0.22, w - 0.4, 0.24,
                 11, accent, True)
        add_text(slide, detail, x + 0.23, y + 0.57, w - 0.4, 0.58,
                 15.5, WHITE, True, font=FONT_DISPLAY)

    add_box(slide, 0.65, 4.25, 5.95, 1.65, CARD, EDGE)
    add_text(slide, "STUDENT WORKSPACE", 0.93, 4.54, 4.2, 0.23,
             11, TEAL, True)
    add_text(slide, "Dashboard  ·  Profile  ·  Academic requests  ·  Announcements",
             0.93, 4.96, 5.27, 0.62, 17, WHITE, True)
    add_box(slide, 6.76, 4.25, 5.9, 1.65, CARD, EDGE)
    add_text(slide, "ADMIN WORKSPACE", 7.04, 4.54, 4.2, 0.23,
             11, BLUE, True)
    add_text(slide, "Overview  ·  Request decisions  ·  Announcement management",
             7.04, 4.96, 5.26, 0.62, 17, WHITE, True)
    add_pill(slide, "PYTHON 3", 0.67, 6.26, 1.3, NAVY_2, MUTED, 9.5)
    add_pill(slide, "FLASK", 2.06, 6.26, 1.1, NAVY_2, MUTED, 9.5)
    add_pill(slide, "SQLITE", 3.25, 6.26, 1.17, NAVY_2, MUTED, 9.5)
    add_pill(slide, "JINJA2", 4.51, 6.26, 1.23, NAVY_2, MUTED, 9.5)
    add_pill(slide, "LOCAL BOOTSTRAP 5", 5.83, 6.26, 2.23, NAVY_2, MUTED, 9.5)
    add_pill(slide, "VANILLA JS", 8.15, 6.26, 1.54, NAVY_2, MUTED, 9.5)
    return slide


def slide_three(presentation):
    slide = new_slide(presentation, 3, "Laboratory architecture")
    header(slide, "02  /  Isolated network", "Two VMs. One controlled path.",
           "Planned Host-only demonstration topology; live VM connectivity is pending verification.")
    add_line(slide, 3.99, 3.55, 4.74, 3.55, TEAL, 2.8)
    add_line(slide, 8.60, 3.55, 9.34, 3.55, TEAL, 2.8)

    add_box(slide, 0.64, 2.47, 3.36, 2.15, CARD, EDGE)
    add_circle(slide, 0.96, 2.79, 0.5, BLUE)
    add_text(slide, "K", 1.02, 2.87, 0.38, 0.26, 17, NAVY, True,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_text(slide, "KALI LINUX", 0.95, 3.43, 2.7, 0.32, 20, WHITE, True)
    add_text(slide, "Burp Suite\nProxy + Repeater", 0.95, 3.85, 2.65, 0.6, 15, MUTED)

    add_box(slide, 4.75, 2.47, 3.84, 2.15, NAVY_2, TEAL, line_width=1.6)
    add_text(slide, "HOST-ONLY", 5.02, 2.82, 3.32, 0.42,
             24, TEAL, True, PP_ALIGN.CENTER, font=FONT_DISPLAY)
    add_text(slide, "ISOLATED VIRTUAL NETWORK", 5.00, 3.46, 3.35, 0.3,
             11, WHITE, True, PP_ALIGN.CENTER)
    add_text(slide, "No public route", 5.10, 3.95, 3.14, 0.28,
             14, MUTED, False, PP_ALIGN.CENTER)

    add_box(slide, 9.34, 2.47, 3.36, 2.15, CARD, EDGE)
    add_circle(slide, 9.66, 2.79, 0.5, TEAL)
    add_text(slide, "U", 9.72, 2.87, 0.38, 0.26, 17, NAVY, True,
             PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_text(slide, "UBUNTU SERVER", 9.65, 3.43, 2.75, 0.32, 19, WHITE, True)
    add_text(slide, "Flask on :5000\nLocal SQLite database", 9.65, 3.85, 2.71, 0.6, 15, MUTED)

    add_box(slide, 0.64, 5.2, 12.06, 0.96, CARD, EDGE)
    add_text(slide, "BIND RULE", 0.91, 5.48, 1.18, 0.22, 10.5, BLUE, True)
    add_text(slide, "Loopback by default  ·  verified Host-only IP for VM access  ·  debug disabled",
             2.08, 5.44, 10.18, 0.38, 15.5, WHITE, True)
    add_pill(slide, "NETWORK EVIDENCE PENDING", 0.67, 6.42, 2.83, NAVY_2, AMBER, 9.5)
    return slide


def scenario_card(slide, x, number, short, title, endpoint, explanation, accent):
    add_box(slide, x, 2.28, 3.89, 4.05, CARD, EDGE)
    add_circle(slide, x + 0.29, 2.57, 0.51, accent)
    add_text(slide, number, x + 0.35, 2.66, 0.39, 0.22, 12.5,
             NAVY, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_text(slide, short, x + 0.98, 2.72, 2.56, 0.23,
             10.5, accent, True)
    add_text(slide, title, x + 0.29, 3.18, 3.30, 1.07,
             20.5, WHITE, True, font=FONT_DISPLAY)
    add_box(slide, x + 0.29, 4.39, 3.32, 0.6, NAVY_2, radius=False)
    add_text(slide, endpoint, x + 0.42, 4.55, 3.07, 0.29,
             11.4, BLUE, True)
    add_text(slide, explanation, x + 0.29, 5.18, 3.28, 0.9,
             15, MUTED)


def slide_four(presentation):
    slide = new_slide(presentation, 4, "Security scenarios")
    header(slide, "03  /  Authorization boundaries", "Three controlled scenarios",
           "One object, one function, one profile field — all with fictional records.")
    scenario_card(slide, 0.62, "01", "OBJECT", "Broken Object Level Authorization",
                  "GET /api/requests/201", "Alice changes the ID to read Bob's request in Vulnerable Mode.", BLUE)
    scenario_card(slide, 4.72, "02", "FUNCTION", "Broken Function Level Authorization",
                  "POST /api/admin/announcements", "Alice invokes an administrator operation in Vulnerable Mode.", TEAL)
    scenario_card(slide, 8.82, "03", "FIELD", "Mass Assignment / Improper Field Authorization",
                  "POST /api/profile", "Alice submits role=admin in an ordinary profile update.", AMBER)
    return slide


def screenshot_placeholder(slide, x, y, w, h, label, accent):
    frame = add_box(slide, x, y, w, h, NAVY_2, accent, True, 1.5,
                    MSO_LINE_DASH_STYLE.DASH,
                    f"Replaceable screenshot placeholder: {label}")
    add_box(slide, x + 0.03, y + 0.03, w - 0.06, 0.32, CARD, radius=False)
    add_circle(slide, x + 0.17, y + 0.14, 0.08, RED)
    add_circle(slide, x + 0.33, y + 0.14, 0.08, AMBER)
    add_circle(slide, x + 0.49, y + 0.14, 0.08, TEAL)
    add_text(slide, "BURP SUITE  /  REPEATER", x + 0.77, y + 0.11,
             w - 1.08, 0.18, 9, MUTED, True)
    add_line(slide, x + 0.55, y + 1.33, x + w - 0.55, y + 1.33,
             EDGE, 1.0, MSO_LINE_DASH_STYLE.DASH)
    add_text(slide, "+", x + w / 2 - 0.22, y + 0.79, 0.44, 0.42,
             32, accent, False, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    add_text(slide, label, x + 0.47, y + 1.62, w - 0.94, 0.32,
             16, WHITE, True, PP_ALIGN.CENTER)
    add_text(slide, "INSERT REAL REDACTED CAPTURE AFTER MANUAL LAB",
             x + 0.41, y + 2.03, w - 0.82, 0.25,
             10, MUTED, True, PP_ALIGN.CENTER)
    return frame


def slide_five(presentation):
    slide = new_slide(presentation, 5, "Manual testing")
    header(slide, "04  /  Burp Suite workflow", "Capture the evidence — then compare",
           "This slide contains replaceable placeholders. No manual Burp session is claimed.")
    steps = [
        (0.72, "01", "RESET"), (3.80, "02", "SIGN IN"),
        (6.88, "03", "EDIT REQUEST"), (9.96, "04", "COMPARE"),
    ]
    add_line(slide, 1.21, 2.66, 10.44, 2.66, EDGE, 2.0)
    for x, number, label in steps:
        add_circle(slide, x, 2.37, 0.58, CARD_2, TEAL, 1.1)
        add_text(slide, number, x + 0.10, 2.54, 0.38, 0.17,
                 10.5, TEAL, True, PP_ALIGN.CENTER)
        add_text(slide, label, x + 0.72, 2.51, 2.22, 0.24,
                 11.5, WHITE, True)

    screenshot_placeholder(slide, 0.66, 3.17, 5.87, 2.56,
                           "VULNERABLE MODE RESPONSE", AMBER)
    screenshot_placeholder(slide, 6.80, 3.17, 5.87, 2.56,
                           "SECURE MODE RESPONSE", TEAL)
    add_pill(slide, "MANUAL EVIDENCE PENDING", 0.69, 6.13, 2.81, NAVY_2, AMBER, 9.5)
    add_text(slide, "Reset and capture each scenario separately; redact cookies and CSRF tokens.",
             3.82, 6.17, 8.42, 0.27, 12.5, MUTED)
    return slide


def comparison_row(slide, y, number, title, endpoint, vulnerable,
                   secure, remediation):
    add_box(slide, 0.64, y, 12.05, 1.14, CARD, EDGE)
    add_circle(slide, 0.89, y + 0.30, 0.48, CARD_2, BLUE, 1.0)
    add_text(slide, number, 0.98, y + 0.46, 0.30, 0.16,
             10.5, BLUE, True, PP_ALIGN.CENTER)
    add_text(slide, title, 1.55, y + 0.16, 2.25, 0.27,
             14.5, WHITE, True)
    add_text(slide, endpoint, 1.55, y + 0.57, 2.60, 0.30,
             9.8, MUTED)
    add_pill(slide, vulnerable, 4.38, y + 0.22, 2.55, NAVY_2, AMBER, 10.5, 0.39)
    add_pill(slide, secure, 7.16, y + 0.22, 2.14, NAVY_2, TEAL, 10.5, 0.39)
    add_text(slide, remediation, 9.62, y + 0.22, 2.68, 0.68,
             12.2, WHITE, True)


def slide_six(presentation):
    slide = new_slide(presentation, 6, "Security hardening")
    header(slide, "05  /  Secure mode", "Authorization belongs on the server",
           "Automated test-client contracts: the same endpoint, a different policy decision.")
    add_text(slide, "SCENARIO", 1.55, 2.20, 2.25, 0.18, 10, FAINT, True)
    add_text(slide, "VULNERABLE", 4.41, 2.20, 2.4, 0.18, 10, AMBER, True)
    add_text(slide, "SECURE", 7.19, 2.20, 2.0, 0.18, 10, TEAL, True)
    add_text(slide, "REMEDIATION", 9.62, 2.20, 2.5, 0.18, 10, FAINT, True)
    comparison_row(slide, 2.50, "01", "Object access", "/api/requests/201",
                   "200 · Bob's record", "403 · denied", "Check request owner")
    comparison_row(slide, 3.79, "02", "Admin function", "/api/admin/announcements",
                   "201 · row saved", "403 · denied", "Require admin role")
    comparison_row(slide, 5.08, "03", "Profile field", "/api/profile role=admin",
                   "200 · role saved", "403 · denied", "Allowlist editable fields")
    add_text(slide, "Authenticated session + CSRF stay active in both modes. Reset data between comparisons.",
             0.72, 6.48, 11.82, 0.27, 12.5, MUTED)
    return slide


def metric(slide, x, number, label, detail, accent):
    add_box(slide, x, 2.35, 3.86, 2.26, CARD, EDGE)
    add_box(slide, x, 2.35, 3.86, 0.07, accent, radius=False)
    add_text(slide, number, x + 0.28, 2.68, 3.25, 0.84,
             51, accent, True, font=FONT_DISPLAY)
    add_text(slide, label, x + 0.30, 3.59, 3.19, 0.27,
             16.8, WHITE, True)
    add_text(slide, detail, x + 0.30, 4.02, 3.17, 0.24,
             11.5, MUTED)


def slide_seven(presentation):
    slide = new_slide(presentation, 7, "Results and conclusion")
    header(slide, "06  /  Verified results", "The comparison is reproducible",
           "Executed automated checks use Flask's test client and isolated temporary SQLite files.")
    metric(slide, 0.65, "44", "pytest tests passed", "+ 2 subtests passed", TEAL)
    metric(slide, 4.74, "23", "unittest tests passed", "Original regression suite", BLUE)
    metric(slide, 8.83, "0", "unresolved test failures", "Final Stage 5 execution", WHITE)

    add_box(slide, 0.65, 5.01, 7.14, 1.16, CARD_2, EDGE)
    add_text(slide, "KEY LEARNING", 0.93, 5.24, 1.65, 0.23,
             10.5, TEAL, True)
    add_text(slide, "Ownership, role and field checks must be enforced in the backend.",
             0.93, 5.50, 6.35, 0.56, 16, WHITE, True)
    add_box(slide, 8.02, 5.01, 4.64, 1.16, NAVY_2, AMBER, line_width=1.2)
    add_text(slide, "NEXT EVIDENCE", 8.27, 5.24, 2.1, 0.23,
             10.5, AMBER, True)
    add_text(slide, "Ubuntu/Kali Host-only + Burp manual capture pending",
             8.27, 5.54, 4.02, 0.52, 13, WHITE, True)
    add_text(slide, "Secure by default. Isolated by design. Synthetic data only.",
             0.68, 6.49, 11.9, 0.28, 13, MUTED)
    return slide


def build_presentation(output=OUTPUT):
    presentation = Presentation()
    presentation.slide_width = Inches(SLIDE_W)
    presentation.slide_height = Inches(SLIDE_H)
    presentation.core_properties.title = PRESENTATION_TITLE
    presentation.core_properties.subject = "Isolated university Information Security laboratory"
    presentation.core_properties.keywords = "Flask, SQLite, Burp Suite, authorization, lab"
    for build in (slide_one, slide_two, slide_three, slide_four,
                  slide_five, slide_six, slide_seven):
        build(presentation)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(output)
    validate_presentation(output)
    return output


def validate_presentation(path):
    """Reopen the OOXML package and verify count, key claims, and editability."""
    presentation = Presentation(path)
    if len(presentation.slides) != 7:
        raise AssertionError(f"Expected 7 slides, found {len(presentation.slides)}")
    if presentation.core_properties.title != PRESENTATION_TITLE:
        raise AssertionError("The presentation title is incomplete")
    if presentation.slide_width != Inches(SLIDE_W):
        raise AssertionError("Unexpected slide width")
    texts = ["\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
             for slide in presentation.slides]
    required = {
        0: ("CampusSecure", "Manual Web Application Penetration Testing"),
        1: ("FLASK FACTORY", "SQLITE"),
        2: ("KALI LINUX", "HOST-ONLY", "UBUNTU SERVER"),
        3: ("Broken Object Level Authorization", "Mass Assignment"),
        4: ("MANUAL EVIDENCE PENDING", "INSERT REAL REDACTED CAPTURE"),
        5: ("200 · Bob's record", "403 · denied"),
        6: ("44", "23", "0", "pending"),
    }
    for index, phrases in required.items():
        for phrase in phrases:
            if phrase not in texts[index]:
                raise AssertionError(f"Slide {index + 1} lacks {phrase!r}")
    for index, slide in enumerate(presentation.slides, 1):
        if len(slide.shapes) < 15:
            raise AssertionError(f"Slide {index} appears incomplete")
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                raise AssertionError(f"Slide {index} contains a noneditable picture")
            if (shape.left < 0 or shape.top < 0
                    or shape.left + shape.width > presentation.slide_width + 1500
                    or shape.top + shape.height > presentation.slide_height + 1500):
                raise AssertionError(f"Slide {index} has an off-canvas shape: {shape.name}")
    placeholders = [shape for shape in presentation.slides[4].shapes
                    if shape.name.startswith("Replaceable screenshot placeholder:")]
    if len(placeholders) != 2:
        raise AssertionError("Expected two editable manual screenshot placeholders")
    return presentation


if __name__ == "__main__":
    created = build_presentation()
    reopened = validate_presentation(created)
    print(f"Created {created}")
    print(f"Validated {len(reopened.slides)} editable slides; file reopened successfully")
