from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "templates"
DEST.mkdir(exist_ok=True)

PAGES = {
    "index.html": "index.html",
    "student.html": "student.html",
    "parent.html": "parent.html",
    "warden.html": "warden.html",
    "gate-pass.html": "gate-pass.html",
    "attendance.html": "attendance.html",
    "visitor.html": "visitor.html",
    "visit-request.html": "visit-request.html",
    "complaint.html": "complaint.html",
    "qr.html": "qr.html",
    "forgot-password.html": "forgot-password.html",
    "notice-new.html": "notice-new.html",
    "students.html": "students.html",
}

HREF_MAP = [
    ("forgot-password.html", "/forgot-password"),
    ("visit-request.html", "/visit-request"),
    ("attendance.html", "/attendance"),
    ("gate-pass.html", "/gate-pass"),
    ("complaint.html", "/complaint"),
    ("notice-new.html", "/notice-new"),
    ("students.html", "/students"),
    ("visitor.html", "/visitor"),
    ("student.html", "/student"),
    ("parent.html", "/parent"),
    ("warden.html", "/warden"),
    ("index.html", "/"),
    ("qr.html", "/qr"),
]


def convert(text: str) -> str:
    for css in ("login.css", "student.css", "parent.css", "warden.css"):
        text = text.replace(
            f'href="css/{css}"',
            f"href=\"{{{{ url_for('static', filename='css/{css}') }}}}\"",
        )
        text = text.replace(
            f"href='css/{css}'",
            f"href=\"{{{{ url_for('static', filename='css/{css}') }}}}\"",
        )
    for js in ("passes.js", "store.js"):
        text = text.replace(
            f'src="js/{js}"',
            f"src=\"{{{{ url_for('static', filename='js/{js}') }}}}\"",
        )
        text = text.replace(
            f"src='js/{js}'",
            f"src=\"{{{{ url_for('static', filename='js/{js}') }}}}\"",
        )

    for old, new in HREF_MAP:
        text = text.replace(f'href="{old}', f'href="{new}')
        text = text.replace(f"href='{old}", f"href='{new}")
        text = text.replace(f'window.location.href = "{old}', f'window.location.href = "{new}')
        text = text.replace(f"window.location.href = '{old}", f"window.location.href = '{new}")

    return text


for src_name, dest_name in PAGES.items():
    src = ROOT / src_name
    if not src.exists():
        print("missing", src_name)
        continue
    dest = DEST / dest_name
    dest.write_text(convert(src.read_text(encoding="utf-8")), encoding="utf-8")
    print("wrote", dest_name)
