import os
import tempfile
import unittest

os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.gettempdir(), "hostelsense-test.db"
)

from app import StudentProfile, User, app, db  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


class ApplicationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_context = app.app_context()
        cls.app_context.push()
        db.drop_all()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.drop_all()
        cls.app_context.pop()

    def setUp(self):
        db.session.query(StudentProfile).delete()
        db.session.query(User).delete()
        db.session.commit()
        self.client = app.test_client()

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/readyz").status_code, 200)

    def test_warden_creates_linked_student_and_parent(self):
        warden = User(
            name="Warden",
            email="warden@test.example",
            password_hash=generate_password_hash("warden-password-12"),
            role="warden",
        )
        db.session.add(warden)
        db.session.commit()
        login = self.client.post(
            "/api/auth/login",
            json={
                "identifier": "warden@test.example",
                "password": "warden-password-12",
                "role": "warden",
            },
        )
        self.assertEqual(login.status_code, 200)
        created = self.client.post(
            "/api/warden/students",
            json={
                "studentName": "Student",
                "roll": "1234567890123",
                "studentPassword": "student-password-12",
                "parentName": "Parent",
                "parentEmail": "parent@test.example",
                "parentPassword": "parent-password-12",
                "room": "C-214",
                "floor": 2,
                "course": "B.Tech CSE",
                "status": "inside",
            },
        )
        self.assertEqual(created.status_code, 201)
        headcount = self.client.get("/api/warden/headcount").get_json()
        self.assertEqual(headcount["total"], 1)
        self.assertEqual(headcount["inside"], 1)

    def test_student_attendance_is_visible_to_parent(self):
        parent = User(
            name="Parent",
            email="parent@test.example",
            password_hash=generate_password_hash("parent-password-12"),
            role="parent",
        )
        student = User(
            name="Student",
            roll="1234567890123",
            password_hash=generate_password_hash("student-password-12"),
            role="student",
        )
        db.session.add_all((parent, student))
        db.session.commit()
        db.session.add(
            StudentProfile(
                user_id=student.id,
                parent_id=parent.id,
                room="C-214",
                floor=2,
                course="B.Tech CSE",
                status="inside",
            )
        )
        db.session.commit()
        self.client.post(
            "/api/auth/login",
            json={
                "identifier": "1234567890123",
                "password": "student-password-12",
                "role": "student",
            },
        )
        self.assertEqual(
            self.client.post(
                "/api/attendance",
                json={"date": "2026-10-29", "time": "19:30"},
            ).status_code,
            201,
        )
        self.client.post("/api/auth/logout")
        self.client.post(
            "/api/auth/login",
            json={
                "identifier": "parent@test.example",
                "password": "parent-password-12",
                "role": "parent",
            },
        )
        result = self.client.get("/api/parent/attendance")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.get_json()["records"]), 1)


if __name__ == "__main__":
    unittest.main()
