# HostelSense

A hostel-management web app that replaces the warden's paper register. Students request gate passes, parents and wardens approve them, visitors enter through QR codes, and evening attendance is verified with the student's face.

Built with a plain HTML/CSS/JavaScript frontend, a Flask + SQLite backend, and a separate Flask microservice for face verification.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Demo accounts](#demo-accounts)
- [Pages](#pages)
- [API reference](#api-reference)
- [Face verification service](#face-verification-service)
- [Where data is stored](#where-data-is-stored)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Team](#team)

---

## Features

**Student**
- Dashboard with gate passes, visitors, notices and issues at a glance
- Request a gate pass (outing, home visit, medical, other) with date/time validation
- Invite a visitor and track approval status
- Evening attendance using the webcam and face verification
- Attendance history for the last 14 days with present / late / absent / leave and an attendance rate
- Report room, mess or maintenance issues
- Personal ID-style QR page (printable)

**Parent**
- Approve or reject the child's gate pass requests
- Request a hostel visit
- Show the visitor QR code at the gate
- Read notices meant for parents

**Warden**
- Approve or reject gate passes (only after the parent has approved)
- Approve visitor requests, which issues a QR pass, then check visitors in and out
- Student roster with search and Inside / Out filters, and add new students
- Publish notices to all, students only, or parents only
- Reports page with a print option

**Security gate**
- Scan a visitor's QR code with the camera (or paste the token) to check them in
- A used QR code cannot be reused

**Other**
- Geofence API that checks whether a location is within 300 m of the hostel
- Auto-refresh of dashboards every 15 seconds
- Responsive layout with an off-canvas sidebar on mobile

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript (ES6+), Jinja2 templates |
| Backend | Python, Flask, Flask-SQLAlchemy |
| Database | SQLite (`instance/hostelsense.db`) |
| Face service | Flask, Flask-CORS, `face_recognition` (dlib), NumPy |
| Browser APIs | `fetch`, `getUserMedia` (camera), Geolocation, `localStorage`, `sessionStorage`, Canvas |
| Libraries (CDN) | [qrcodejs](https://github.com/davidshimjs/qrcodejs) to generate QR codes, [html5-qrcode](https://github.com/mebjas/html5-qrcode) to scan them, Google Fonts (IBM Plex Sans, Newsreader) |

---

## Architecture

```
┌──────────────────────┐        JSON / fetch         ┌───────────────────────┐
│  Browser             │ ──────────────────────────► │  Flask app  :5000     │
│  HTML + CSS + JS     │ ◄────────────────────────── │  (app.py)             │
│  localStorage cache  │                             │  SQLAlchemy + SQLite  │
└──────────┬───────────┘                             └───────────────────────┘
           │
           │ multipart image + roll number
           ▼
┌──────────────────────┐
│  Face service :5001  │   compares the live photo with the
│  (face-service/)     │   stored face encoding for that roll
└──────────────────────┘
```

The frontend calls the API and caches results in `localStorage`. If the server is unreachable, most pages fall back to the cached data so the demo keeps working.

---

## Project structure

```
hostelSense/
├── app.py                  # Flask app: models, page routes, JSON API
├── run.py                  # Loads .env and starts the app
├── seed.py                 # Resets the database and loads demo data
├── requirements.txt
├── .env.example
├── start-project.bat       # Windows: starts both servers
│
├── templates/              # Jinja2 pages
│   ├── index.html          # Login
│   ├── student.html        # Student dashboard
│   ├── parent.html         # Parent portal
│   ├── warden.html         # Warden portal
│   ├── gate-pass.html
│   ├── visitor.html
│   ├── visit-request.html
│   ├── mark-attendance.html
│   ├── attendance.html
│   ├── qr.html
│   ├── complaint.html
│   ├── notice-new.html
│   ├── students.html
│   ├── student-new.html
│   ├── security-gate.html
│   ├── forgot-password.html
│   └── warden-*.html       # approvals, visitors, alerts, reports
│
├── static/
│   ├── css/                # login.css, student.css, parent.css, warden.css
│   └── js/
│       ├── passes.js       # Gate-pass API helpers, status logic, geofence
│       └── store.js        # Visitors, complaints, notices, attendance, roster
│
└── face-service/
    ├── app.py              # POST /verify-face
    ├── register_face.py    # Registers a student's face
    ├── encodings.json      # Stored face encodings (by roll number)
    ├── known_faces/        # Enrollment photos
    ├── test-camera.html    # Standalone camera test page
    └── requirements.txt
```

---

## Getting started

### Prerequisites

- Python 3.10 or newer
- A modern browser (Chrome or Edge recommended)
- For the face service: CMake and a C++ build toolchain, because `face_recognition` depends on `dlib`

### 1. Main application

```bash
# from the project root
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env

python seed.py              # creates the database with demo data
python run.py               # starts the site
```

Open **http://127.0.0.1:5000**

> The app uses SQLite by default (`sqlite:///hostelsense.db`, created in `instance/`). The database URL in `.env.example` points to PostgreSQL but is not used by the current `app.py`.

### 2. Face verification service

```bash
cd face-service
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

python register_face.py     # registers the demo student from known_faces/aarav.jpg
python app.py               # starts on http://127.0.0.1:5001
```

Only the attendance page (`/mark-attendance`) needs this service. Everything else works without it.

### 3. Windows shortcut

`start-project.bat` opens two terminals and starts both servers. It expects a `.venv` in the project root and a `venv` inside `face-service/`.

---

## Demo accounts

| Role | Login | Password |
|---|---|---|
| Student | `2401641520038` | `student123` |
| Parent | `suresh.parent@email.com` | `parent123` |
| Warden | `warden@college.edu` | `warden123` |

The credentials are pre-filled when you pick a role on the sign-in page.

### Try the full flow

1. Log in as **Student** and request a gate pass.
2. Log in as **Parent** and approve it.
3. Log in as **Warden** and approve it. The pass now shows as *Approved*.
4. As **Student**, invite a visitor (`/visitor`).
5. As **Warden**, approve the visitor. A QR pass is issued.
6. As **Parent**, open the visitor list and click **Show QR at gate**.
7. Open `/security-gate` and scan the QR (or paste its token). The student's dashboard then shows the visitor has arrived.
8. Open `/mark-attendance`, allow camera access and verify your face (face service must be running).

---

## Pages

| URL | Description |
|---|---|
| `/` | Login |
| `/forgot-password` | Password reset (demo) |
| `/student` | Student dashboard |
| `/gate-pass` | Request a gate pass |
| `/attendance` | Attendance history |
| `/mark-attendance` | Evening attendance with face verification |
| `/visitor` | Invite a visitor |
| `/complaint` | Report an issue |
| `/qr` | Student ID QR |
| `/parent` | Parent portal |
| `/visit-request` | Parent visit request |
| `/warden` | Warden dashboard |
| `/warden/approvals` | Gate-pass approvals |
| `/warden/visitors` | Visitor desk |
| `/warden/alerts` | Notices and alerts |
| `/warden/reports` | Reports |
| `/students` | Student roster |
| `/student-new` | Add a student |
| `/notice-new` | Post a notice |
| `/security-gate` | QR scanner for the gate |

---

## API reference

Base URL: `http://127.0.0.1:5000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/passes?roll=<roll>` | List gate passes (optionally for one student) |
| `POST` | `/api/passes` | Create a gate pass |
| `PATCH` | `/api/passes/<id>/status` | Update `parentStatus` and/or `wardenStatus` |
| `GET` | `/api/visitors?roll=<roll>` | List visitors |
| `POST` | `/api/visitors` | Create a visit request |
| `PATCH` | `/api/visitors/<id>/status` | Update status, QR fields or arrival time |
| `POST` | `/api/visitors/verify-entry` | Check in a visitor by scanned QR value |
| `POST` | `/api/verify-location` | Check coordinates against the hostel geofence |

**Example: create a gate pass**

```http
POST /api/passes
Content-Type: application/json

{
  "id": "gp-1700000000000",
  "studentName": "Aarav Sharma",
  "roll": "2401641520038",
  "type": "outing",
  "typeLabel": "City outing",
  "destination": "City mall",
  "reason": "Personal shopping",
  "from": "2026-10-01T16:00",
  "to": "2026-10-01T20:30",
  "parentStatus": "pending",
  "wardenStatus": "pending"
}
```

**Response codes:** `200` OK, `201` Created, `400` Bad request, `404` Not found, `409` Conflict (visitor pass already used).

**Gate-pass status logic**

| Parent | Warden | Overall |
|---|---|---|
| any `rejected` | any `rejected` | Rejected |
| `approved` | `approved` | Approved |
| anything else | anything else | Pending |

**Visitor status flow:** `pending` → `expected` (approved, QR issued) → `checked_in` → `completed`. A visit can also be `rejected`.

**Geofence:** the hostel is centred at `26.4499, 80.3319` with a radius of `300 m`. Distance is computed with the Haversine formula. The constants are at the top of `app.py`.

---

## Face verification service

Runs separately on port **5001**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Camera test page |
| `POST` | `/verify-face` | Multipart form: `image` (file) and `roll_number` |

**Response**

```json
{ "matched": true, "distance": 0.31, "roll_number": "2401641520038" }
```

- A face is a match when the distance to the stored encoding is `<= 0.45`.
- If no face is found: `{ "matched": false, "reason": "No face was detected in the image" }`.
- If the roll is not registered: `404` with an error message.

**Registering a student:** put a clear, front-facing photo in `face-service/known_faces/`, then edit the last lines of `register_face.py` with the roll number and file path and run it. The encoding is saved in `encodings.json`.

---

## Where data is stored

| Data | Storage |
|---|---|
| Gate passes | SQLite (`gate_passes`), cached in `localStorage` |
| Visitors and QR tokens | SQLite (`visitors`), cached in `localStorage` |
| Complaints | `localStorage` |
| Notices | `localStorage` |
| Attendance records | `localStorage` |
| Student roster | `localStorage` |
| Logged-in user | `sessionStorage` |
| Face encodings | `face-service/encodings.json` |

---

## Known limitations

This is a college project / prototype. Before real use, these need attention:

- **Authentication is demo-level.** Credentials are checked in client-side JavaScript, and the API has no login or role checks.
- **Complaints, notices, attendance and the roster are stored only in the browser**, so they are not shared between users or devices.
- **The student ID QR (`/qr`) is a visual placeholder** and cannot be scanned. Visitor QR codes are real.
- **The geofence API is not yet used by any page.**
- **Evening attendance is always open** (testing mode), and face verification has no liveness check.
- **The face service URL is hard-coded** to `http://127.0.0.1:5001` in `mark-attendance.html`.
- Dashboards refresh by polling every 15 seconds instead of real-time updates.
- `requirements.txt` lists packages (PostgreSQL driver, JWT, Migrate, CORS) that the current code does not use yet.

---

## Roadmap

- [ ] Server-side authentication with hashed passwords and role-based access (JWT)
- [ ] Database models and APIs for complaints, notices, attendance and students
- [ ] Real QR codes for student IDs, with signed tokens
- [ ] Enforce the geofence during attendance
- [ ] Time-window enforcement and liveness detection for attendance
- [ ] Email / SMS / push notifications to parents
- [ ] PostgreSQL and database migrations
- [ ] Automated tests
- [ ] Move the frontend to React components
- [ ] HTTPS deployment (the camera requires a secure context outside `localhost`)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Camera does not start | Allow camera permission; use `localhost` or HTTPS |
| "Could not verify face" / network error | Make sure the face service is running on port 5001 |
| `pip install face-recognition` fails | Install CMake and a C++ build toolchain (Visual Studio Build Tools on Windows), then retry |
| Lists look empty or outdated | Run `python seed.py`, and clear the site's `localStorage` in the browser |
| Port already in use | Stop the other process or change the port in `run.py` / `face-service/app.py` |

---

## Team

Add your team members, roles and roll numbers here.

| Name | Role |
|---|---|
| _Your name_ | Frontend |
| _Teammate_ | Backend |
| _Teammate_ | Face recognition |

---

## License

Add a license (for example MIT) or state that the project is for academic use only.
