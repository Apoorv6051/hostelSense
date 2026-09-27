import json
import re
import urllib.error
import urllib.request

base = "http://127.0.0.1:5000"
pages = [
    "/",
    "/index.html",
    "/student",
    "/parent",
    "/warden",
    "/gate-pass",
    "/attendance",
    "/visitor",
    "/visit-request",
    "/complaint",
    "/qr",
    "/forgot-password",
    "/notice-new",
    "/students",
]
static_files = [
    "/static/css/login.css",
    "/static/css/student.css",
    "/static/css/parent.css",
    "/static/css/warden.css",
    "/static/js/passes.js",
    "/static/js/store.js",
    "/css/student.css",
    "/js/store.js",
    "/js/passes.js",
]


def fetch(path, method="GET", data=None, headers=None):
    req = urllib.request.Request(
        base + path, data=data, method=method, headers=headers or {}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read()
            return r.status, r.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()
    except Exception as e:
        return None, "", str(e).encode()


print("=== PAGES ===")
for p in pages:
    status, ctype, body = fetch(p)
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    conflicts = text.count("<<<<<<<")
    raw_css = len(re.findall(r'href="css/', text))
    raw_js = len(re.findall(r'src="js/', text))
    unrendered = "{{ url_for" in text
    title = ""
    m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    print(
        f"{status!s:>4} {p:22} conflicts={conflicts} raw_css={raw_css} raw_js={raw_js} "
        f"unrendered_url_for={unrendered} bytes={len(text)} title={title!r}"
    )

print()
print("=== STATIC ===")
for p in static_files:
    status, ctype, body = fetch(p)
    n = len(body) if isinstance(body, bytes) else 0
    print(f"{status!s:>4} {p:30} {n} bytes")

print()
print("=== API GET /api/passes ===")
status, ctype, body = fetch("/api/passes")
print(status, body.decode()[:800] if isinstance(body, bytes) else body)

print()
print("=== API GET /api/passes?roll=2401641520038 ===")
status, ctype, body = fetch("/api/passes?roll=2401641520038")
print(status, body.decode()[:400] if isinstance(body, bytes) else body)

print()
print("=== API POST /api/passes ===")
payload = json.dumps(
    {
        "id": "gp-test-check-1",
        "studentName": "Aarav Sharma",
        "roll": "2401641520038",
        "type": "outing",
        "typeLabel": "City outing",
        "destination": "Campus cafe",
        "reason": "Prototype check",
        "from": "2026-09-15T10:00",
        "to": "2026-09-15T18:00",
        "parentStatus": "pending",
        "wardenStatus": "pending",
    }
).encode()
status, ctype, body = fetch(
    "/api/passes",
    method="POST",
    data=payload,
    headers={"Content-Type": "application/json"},
)
print(status, body.decode()[:500] if isinstance(body, bytes) else body)

print()
print("=== API PATCH /api/passes/gp-test-check-1/status ===")
patch = json.dumps({"parentStatus": "approved"}).encode()
status, ctype, body = fetch(
    "/api/passes/gp-test-check-1/status",
    method="PATCH",
    data=patch,
    headers={"Content-Type": "application/json"},
)
print(status, body.decode()[:500] if isinstance(body, bytes) else body)

print()
print("=== API PATCH missing pass ===")
status, ctype, body = fetch(
    "/api/passes/does-not-exist/status",
    method="PATCH",
    data=b'{"parentStatus":"approved"}',
    headers={"Content-Type": "application/json"},
)
print(status, body.decode()[:300] if isinstance(body, bytes) else body)

print()
print("=== API verify-location inside (Kanpur hostel coords) ===")
geo = json.dumps({"latitude": 26.4499, "longitude": 80.3319}).encode()
status, ctype, body = fetch(
    "/api/verify-location",
    method="POST",
    data=geo,
    headers={"Content-Type": "application/json"},
)
print(status, body.decode() if isinstance(body, bytes) else body)

print()
print("=== API verify-location outside (Delhi) ===")
geo = json.dumps({"latitude": 28.6139, "longitude": 77.2090}).encode()
status, ctype, body = fetch(
    "/api/verify-location",
    method="POST",
    data=geo,
    headers={"Content-Type": "application/json"},
)
print(status, body.decode() if isinstance(body, bytes) else body)

print()
print("=== API verify-location missing coords ===")
status, ctype, body = fetch(
    "/api/verify-location",
    method="POST",
    data=b"{}",
    headers={"Content-Type": "application/json"},
)
print(status, body.decode() if isinstance(body, bytes) else body)

print()
print("=== API GET after create ===")
status, ctype, body = fetch("/api/passes")
print(status, body.decode()[:1200] if isinstance(body, bytes) else body)

print()
print("=== LOGIN PAGE DEMO CREDS ===")
status, ctype, body = fetch("/")
text = body.decode("utf-8", errors="replace")
for needle in [
    "2401641520038",
    "student123",
    "suresh.parent@email.com",
    "parent123",
    "warden@college.edu",
    "warden123",
]:
    print(f"  {needle}: {needle in text}")

print()
print("=== STUDENT PAGE JS BROKEN? ===")
status, ctype, body = fetch("/student")
text = body.decode("utf-8", errors="replace")
print("  has store.js script:", "store.js" in text)
print("  has passes.js script:", "passes.js" in text)
print("  has conflict markers:", "<<<<<<<" in text)
print("  visitorsForRoll used:", "visitorsForRoll" in text)
print("  renderVisitors used:", "renderVisitors" in text)

print()
print("=== GATE PASS PAGE uses addPass vs addPassToDB ===")
status, ctype, body = fetch("/gate-pass")
text = body.decode("utf-8", errors="replace")
print("  addPass(", "addPass(" in text)
print("  addPassToDB(", "addPassToDB(" in text)
print("  checkGeofence(", "checkGeofence(" in text or "checkGeoFence(" in text)
