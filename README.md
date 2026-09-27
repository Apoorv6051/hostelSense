# HostelSense

Flask application for the HostelSense hostel dashboard. The current implementation
serves the HTML frontend and persists gate passes and visitor records in SQLite.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

Open `http://127.0.0.1:5000`. The database is created at
`instance/hostelsense.db`; `seed.py` resets it and loads demo gate-pass and visitor
records.

## Implemented routes

Pages are available at `/`, `/student`, `/parent`, `/warden`, `/gate-pass`,
`/attendance`, `/mark-attendance`, `/visitor`, `/visit-request`, `/complaint`,
`/qr`, `/notice-new`, `/students`, `/security-gate`, and the warden sub-pages.

The JSON API is:

| Method | Route | Purpose |
| --- | --- | --- |
| GET/POST | `/api/passes` | List or create gate passes |
| PATCH | `/api/passes/<id>/status` | Update parent/warden pass status |
| GET/POST | `/api/visitors` | List or create visitor records |
| PATCH | `/api/visitors/<id>/status` | Update visitor status or QR fields |
| POST | `/api/visitors/verify-entry` | Check in an expected visitor by QR value |
| POST | `/api/verify-location` | Check coordinates against the hostel geofence |

The frontend uses the API when available and keeps localStorage as a client-side
fallback for demo/offline use. Face verification is provided separately by the
`face-service` project and is expected on port `5001`.
