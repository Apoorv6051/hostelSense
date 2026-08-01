"""Reset the database and load demo data that mirrors the HostelSense frontend's
hardcoded demo credentials (index.html) so the two plug together immediately.

Run with:  python seed.py
"""
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent
from app.models.warden import Warden
from app.models.gate_pass import GatePass
from app.models.notice import Notice

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    # --- Warden ---------------------------------------------------------
    warden_user = User(role="warden", name="R. Verma", email="warden@college.edu", initials="RV")
    warden_user.set_password("warden123")
    db.session.add(warden_user)
    db.session.flush()

    warden = Warden(user_id=warden_user.id, block_assigned="C")
    db.session.add(warden)
    db.session.flush()

    # --- Parent ----------------------------------------------------------
    parent_user = User(
        role="parent", name="Suresh Parent", email="suresh.parent@email.com", initials="SP"
    )
    parent_user.set_password("parent123")
    db.session.add(parent_user)
    db.session.flush()

    parent = Parent(user_id=parent_user.id)
    db.session.add(parent)
    db.session.flush()

    # --- Student -----------------------------------------------------------
    student_user = User(
        role="student", name="Aarav Sharma", email="aarav.sharma@college.edu", initials="AS"
    )
    student_user.set_password("student123")
    db.session.add(student_user)
    db.session.flush()

    student = Student(
        user_id=student_user.id,
        roll_number="2401641520038",
        room_number="C-214",
        block="C",
        course="B.Tech CSE",
        year=2,
        warden_id=warden.id,
        parent_id=parent.id,
    )
    db.session.add(student)
    db.session.flush()

    # --- Sample gate passes (matches the demo data in js/passes.js) -----
    db.session.add_all(
        [
            GatePass(
                student_id=student.id,
                type="home",
                destination="Home — Lucknow",
                reason="Weekend visit with family",
                from_datetime=datetime.utcnow() + timedelta(days=1),
                to_datetime=datetime.utcnow() + timedelta(days=2),
                parent_status="approved",
                warden_status="pending",
            ),
            GatePass(
                student_id=student.id,
                type="outing",
                destination="City mall",
                reason="Personal shopping",
                from_datetime=datetime.utcnow() - timedelta(days=7),
                to_datetime=datetime.utcnow() - timedelta(days=7) + timedelta(hours=4),
                parent_status="approved",
                warden_status="approved",
            ),
        ]
    )

    # --- Sample notice ----------------------------------------------------
    db.session.add(
        Notice(
            title="Evening headcount at 9:00 PM",
            body="All Block C residents must be inside by 9:00 PM tonight.",
            audience="all",
            priority="amber",
            author_id=warden_user.id,
        )
    )

    db.session.commit()

    print("Seed complete. Demo logins:")
    print("  Student -> 2401641520038 / student123")
    print("  Parent  -> suresh.parent@email.com / parent123")
    print("  Warden  -> warden@college.edu / warden123")
