"""Reset the SQLite database and load the demo records used by the frontend.

Run with: python seed.py
"""
from datetime import datetime, timedelta, timezone

from app import GatePass, Visitor, app, db


with app.app_context():
    db.drop_all()
    db.create_all()

    now = datetime.now(timezone.utc)
    db.session.add_all(
        [
            GatePass(
                id="gp-demo-1",
                student_name="Aarav Sharma",
                roll="2401641520038",
                pass_type="home",
                type_label="Home visit",
                destination="Home — Lucknow",
                reason="Weekend visit with family",
                leaving_from=(now + timedelta(days=1)).isoformat(),
                return_by=(now + timedelta(days=2)).isoformat(),
                parent_status="approved",
                warden_status="pending",
                created_at=now.isoformat(),
            ),
            GatePass(
                id="gp-demo-2",
                student_name="Aarav Sharma",
                roll="2401641520038",
                pass_type="outing",
                type_label="City outing",
                destination="City mall",
                reason="Personal shopping",
                leaving_from=(now - timedelta(days=7)).isoformat(),
                return_by=(now - timedelta(days=7) + timedelta(hours=4)).isoformat(),
                parent_status="approved",
                warden_status="approved",
                created_at=(now - timedelta(days=8)).isoformat(),
            ),
            Visitor(
                id="vis-demo-1",
                name="Mrs. Sharma",
                relation="parent",
                relation_label="Parent",
                student_name="Aarav Sharma",
                roll="2401641520038",
                when=(now + timedelta(days=1)).isoformat(),
                purpose="Weekend lounge visit",
                phone="9876543210",
                status="expected",
                created_by="parent",
                created_at=now.isoformat(),
            ),
        ]
    )
    db.session.commit()

print("Seed complete.")
print("  Student demo roll -> 2401641520038")
