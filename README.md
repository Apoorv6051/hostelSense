# HostelSense Backend

Flask + PostgreSQL backend for the HostelSense frontend (login, student/parent/warden
dashboards, gate passes, attendance, notices, visitors).

## Stack

- Flask 3 (app factory + blueprints)
- Flask-SQLAlchemy (models) + Flask-Migrate (Alembic migrations)
- Flask-JWT-Extended (auth)
- PostgreSQL (via `DATABASE_URL`)

## 1. Set up PostgreSQL

```bash
# Using the postgres CLI (adjust to your OS/setup)
createuser hostelsense --pwprompt      # set password to "hostelsense" or your own
createdb hostelsense -O hostelsense
```

Or with plain SQL:

```sql
CREATE USER hostelsense WITH PASSWORD 'hostelsense';
CREATE DATABASE hostelsense OWNER hostelsense;
```

## 2. Configure environment

```bash
cp .env.example .env
# edit .env if your DB user/password/host differ
```

`.env`:
```
DATABASE_URL=postgresql://hostelsense:hostelsense@localhost:5432/hostelsense
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
```

## 3. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Create tables + demo data

The quickest path (drops and recreates all tables, then seeds demo data):

```bash
python seed.py
```

This creates the same accounts your frontend's login page already has hardcoded:

| Role    | Identifier                  | Password    |
|---------|------------------------------|-------------|
| Student | `2401641520038`               | `student123`|
| Parent  | `suresh.parent@email.com`     | `parent123` |
| Warden  | `warden@college.edu`          | `warden123` |

It also seeds two gate passes and one notice so the dashboards aren't empty.

If you'd rather use proper migrations instead of `seed.py`'s drop/recreate:

```bash
flask --app run.py db init      # first time only
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade
```

## 5. Run the server

```bash
python run.py
# -> http://127.0.0.1:5000
```

For production, use gunicorn instead: `gunicorn -w 4 -b 0.0.0.0:8000 run:app`

## API overview

All routes below are prefixed with `/api`. Authenticated routes expect
`Authorization: Bearer <token>`.

### Auth
| Method | Route          | Who      | Notes                                      |
|--------|----------------|----------|---------------------------------------------|
| POST   | `/auth/login`  | anyone   | `{ identifier, password, role? }`. Students use roll number, parents/wardens use email. Returns `{ token, user }`. |
| GET    | `/auth/me`     | any user | Returns the logged-in user's basic profile. |

### Students
| Method | Route                  | Who              |
|--------|-------------------------|------------------|
| GET    | `/students/me`          | student          |
| GET    | `/students`             | warden, admin    |
| GET    | `/students/<id>`        | warden, admin, parent (only their own child) |

### Gate passes
| Method | Route                                  | Who     | Notes |
|--------|------------------------------------------|---------|-------|
| POST   | `/gate-passes`                          | student | `{ type, destination, reason, from, to }` (ISO datetimes) |
| GET    | `/gate-passes/me`                       | student | own passes |
| GET    | `/gate-passes/child`                    | parent  | passes for their child(ren) |
| GET    | `/gate-passes`                          | warden, admin | all passes |
| PATCH  | `/gate-passes/<id>/parent-decision`     | parent  | `{ decision: "approved" \| "rejected" }` |
| PATCH  | `/gate-passes/<id>/warden-decision`     | warden, admin | `{ decision: "approved" \| "rejected" }` |

A pass is `approved` overall only once both parent and warden approve; a rejection
from either side rejects the whole pass (same rule as the frontend's `passes.js`).

### Attendance
| Method | Route                | Who           | Notes |
|--------|------------------------|---------------|-------|
| POST   | `/attendance`          | warden, admin | `{ studentId, eventType, method, location, verified }` — called by gate/mess scan hardware or a warden |
| GET    | `/attendance/me`       | student       | last 50 of own records |
| GET    | `/attendance/today`    | warden, admin | today's records for headcount |

### Notices
| Method | Route      | Who           | Notes |
|--------|------------|---------------|-------|
| POST   | `/notices` | warden, admin | `{ title, body, audience?, priority? }` |
| GET    | `/notices` | any user      | filtered to the caller's role + "all" |

### Visitors
| Method | Route              | Who           | Notes |
|--------|--------------------|---------------|-------|
| POST   | `/visitors`        | any user      | student invites a guest, or parent requests a visit |
| GET    | `/visitors`         | warden, admin | full visitor desk list |
| PATCH  | `/visitors/<id>`    | warden, admin | `{ status: "expected" \| "checked_in" \| "completed" }` |

## Connecting the existing frontend

The uploaded frontend currently stores everything in `localStorage`/`sessionStorage`
(see `js/passes.js` and the inline scripts in each HTML page) and never calls a
server. To wire it up to this backend you'd replace:

- The login form's demo-credential check → `POST /api/auth/login`, store the
  returned `token` (e.g. in `sessionStorage`) instead of the whole user object.
- `loadPasses()` / `addPass()` / `updatePass()` in `js/passes.js` → `fetch()` calls
  to the `/api/gate-passes` endpoints above, sending `Authorization: Bearer <token>`.
- The hardcoded dashboard stats/timeline in `student.html`, `warden.html`,
  `parent.html` → calls to `/api/students/me`, `/api/attendance/*`, `/api/notices`,
  `/api/visitors`.

Happy to do that wiring next if you'd like — just say the word.
