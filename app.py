import json
import hashlib
import math
import os
import secrets
import smtplib
import requests
from email.message import EmailMessage
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
database_url = os.environ.get("DATABASE_URL", "sqlite:///hostelsense.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY must be set in the environment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
app.config["RESET_TOKEN_MINUTES"] = int(os.environ.get("RESET_TOKEN_MINUTES", "10"))
app.config["FACE_SERVICE_URL"] = os.environ.get(
    "FACE_SERVICE_URL", "http://127.0.0.1:5001"
).rstrip("/")
app.config["FACE_SERVICE_TOKEN"] = os.environ.get("FACE_SERVICE_TOKEN", "")
app.config["APP_ENV"] = os.environ.get("APP_ENV", "development").lower()
if app.config["APP_ENV"] == "production":
    if not app.config["SESSION_COOKIE_SECURE"]:
        raise RuntimeError("SESSION_COOKIE_SECURE=1 is required in production")
    if database_url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL in production")
db = SQLAlchemy(app)
migrate = Migrate(app, db)


@app.before_request
def enforce_same_origin_for_api_writes():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if not request.path.startswith("/api/") or request.path == "/api/auth/login":
        return None
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        abort(403, description="Cross-origin API writes are not allowed")
    return None

HOSTEL_LAT = 26.4499
HOSTEL_LON = 80.3319
GEOFENCE_RADIUS_METERS = 300


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=True)
    roll = db.Column(db.String(32), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email or "",
            "roll": self.roll or "",
            "role": self.role,
            "initials": "".join(part[0] for part in self.name.split()[:2]).upper(),
        }


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room = db.Column(db.String(40), nullable=False)
    floor = db.Column(db.Integer, nullable=False, default=1)
    course = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="inside")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[user_id])
    parent = db.relationship("User", foreign_keys=[parent_id])

    def to_dict(self):
        return {
            "id": f"stu-{self.user_id}",
            "name": self.student.name,
            "roll": self.student.roll or "",
            "room": self.room,
            "floor": self.floor,
            "course": self.course,
            "status": self.status,
            "parentName": self.parent.name,
            "parentEmail": self.parent.email or "",
        }


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    roll = db.Column(db.String(32), nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    attendance_type = db.Column(db.String(30), nullable=False, default="evening")
    verified = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "roll": self.roll,
            "date": self.recorded_at.date().isoformat(),
            "time": self.recorded_at.strftime("%H:%M"),
            "type": self.attendance_type,
            "verified": self.verified,
            "recordedAt": self.recorded_at.isoformat(),
        }


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def send_password_reset_email(user, reset_url):
    required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "MAIL_FROM")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing SMTP configuration: " + ", ".join(missing))

    message = EmailMessage()
    message["Subject"] = "Reset your HostelSense password"
    message["From"] = os.environ["MAIL_FROM"]
    message["To"] = user.email
    message.set_content(
        "We received a request to reset your HostelSense password.\n\n"
        f"Open this link within {app.config['RESET_TOKEN_MINUTES']} minutes:\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(
        os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"]), timeout=15
    ) as smtp:
        if os.environ.get("SMTP_USE_TLS", "1") == "1":
            smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.active:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("page_", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or not user.active:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("page_"))
            if user.role not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Insufficient permissions"}), 403
                return redirect(url_for(f"page_{user.role}"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


class GatePass(db.Model):
    __tablename__ = "gate_passes"

    id = db.Column(db.String(50), primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    roll = db.Column(db.String(20), nullable=False)
    pass_type = db.Column(db.String(50), default="outing")
    type_label = db.Column(db.String(50), default="Gate Pass")
    destination = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    leaving_from = db.Column(db.String(50), nullable=False)
    return_by = db.Column(db.String(50), nullable=False)
    parent_status = db.Column(db.String(20), default="pending")
    warden_status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.String(50), default=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "studentName": self.student_name,
            "roll": self.roll,
            "type": self.pass_type,
            "typeLabel": self.type_label,
            "destination": self.destination,
            "reason": self.reason,
            "from": self.leaving_from,
            "to": self.return_by,
            "parentStatus": self.parent_status,
            "wardenStatus": self.warden_status,
            "createdAt": self.created_at,
        }


class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    relation = db.Column(db.String(30), default="other")
    relation_label = db.Column(db.String(50), default="Visitor")
    student_name = db.Column(db.String(100), nullable=False)
    roll = db.Column(db.String(20), nullable=False)
    when = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), default="")
    status = db.Column(db.String(20), default="pending")
    created_by = db.Column(db.String(20), default="student")
    created_at = db.Column(db.String(50), default=lambda: datetime.utcnow().isoformat())
    qr_token = db.Column(db.String(160))
    qr_payload = db.Column(db.Text)
    qr_issued_at = db.Column(db.String(50))
    arrived_at = db.Column(db.String(50))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relation": self.relation,
            "relationLabel": self.relation_label,
            "studentName": self.student_name,
            "roll": self.roll,
            "when": self.when,
            "purpose": self.purpose,
            "phone": self.phone or "",
            "status": self.status,
            "createdBy": self.created_by,
            "createdAt": self.created_at,
            "qrToken": self.qr_token,
            "qrPayload": self.qr_payload,
            "qrIssuedAt": self.qr_issued_at,
            "arrivedAt": self.arrived_at,
        }


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (
        math.sin(delta_lambda / 2.0) ** 2
    )
    return radius * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


PAGES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/student": "student.html",
    "/student.html": "student.html",
    "/parent": "parent.html",
    "/parent.html": "parent.html",
    "/warden": "warden.html",
    "/warden.html": "warden.html",
    "/gate-pass": "gate-pass.html",
    "/gate-pass.html": "gate-pass.html",
    "/attendance": "attendance.html",
    "/attendance.html": "attendance.html",
    "/mark-attendance": "mark-attendance.html",
    "/mark-attendance.html": "mark-attendance.html",
    "/visitor": "visitor.html",
    "/visitor.html": "visitor.html",
    "/visit-request": "visit-request.html",
    "/visit-request.html": "visit-request.html",
    "/complaint": "complaint.html",
    "/complaint.html": "complaint.html",
    "/qr": "qr.html",
    "/qr.html": "qr.html",
    "/forgot-password": "forgot-password.html",
    "/forgot-password.html": "forgot-password.html",
    "/reset-password": "reset-password.html",
    "/change-password": "change-password.html",
    "/parent/attendance": "parent-attendance.html",
    "/notice-new": "notice-new.html",
    "/notice-new.html": "notice-new.html",
    "/students": "students.html",
    "/students.html": "students.html",
    "/student-new": "student-new.html",
    "/student-new.html": "student-new.html",
    "/warden/approvals": "warden-approvals.html",
    "/warden/visitors": "warden-visitors.html",
    "/warden/alerts": "warden-alerts.html",
    "/warden/reports": "warden-reports.html",
    "/security-gate": "security-gate.html",
    "/security-gate.html": "security-gate.html",
}


def register_pages():
    for path, template in PAGES.items():
        endpoint = "page_" + path.strip("/").replace("-", "_").replace(".", "_") or "index"

        def view(template_name=template, page_path=path):
            if page_path == "/" or page_path == "/index.html" or page_path.startswith("/forgot-password"):
                return render_template(template_name)
            user = current_user()
            required_role = page_role(page_path)
            if required_role and user.role != required_role:
                return redirect(url_for(f"page_{user.role}"))
            return render_template(template_name, user_role=user.role)

        view.__name__ = endpoint
        if path not in (
            "/",
            "/index.html",
            "/forgot-password",
            "/forgot-password.html",
            "/reset-password",
        ):
            view = login_required(view)
        app.add_url_rule(path, endpoint, view)


def page_role(path):
    if path.startswith("/warden") or path in {
        "/notice-new",
        "/notice-new.html",
        "/students",
        "/students.html",
        "/student-new",
        "/student-new.html",
        "/security-gate",
        "/security-gate.html",
    }:
        return "warden"
    if path.startswith("/student") or path in {
        "/gate-pass",
        "/gate-pass.html",
        "/attendance",
        "/attendance.html",
        "/mark-attendance",
        "/mark-attendance.html",
        "/visitor",
        "/visitor.html",
        "/complaint",
        "/complaint.html",
        "/qr",
        "/qr.html",
    }:
        return "student"
    if path.startswith("/parent") or path in {"/visit-request", "/visit-request.html"}:
        return "parent"
    return None


register_pages()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", "")).strip().lower()
    if not identifier or not password or role not in {"student", "parent", "warden"}:
        return jsonify({"error": "Role, identifier, and password are required"}), 400

    query = User.query.filter_by(role=role, active=True)
    if role == "student":
        user = query.filter_by(roll=identifier).first()
    else:
        user = query.filter(db.func.lower(User.email) == identifier.lower()).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["user_id"] = user.id
    session.permanent = bool(data.get("remember"))
    return jsonify({"success": True, "user": user.to_dict(), "redirect": url_for(f"page_{user.role}")})


@app.post("/api/auth/request-password-reset")
def request_password_reset():
    data = request.get_json(silent=True) or request.form
    identifier = str(data.get("identifier", "")).strip()
    if not identifier:
        return jsonify({"error": "Account email or roll number is required"}), 400

    user = User.query.filter(
        db.or_(
            db.func.lower(User.email) == identifier.lower(),
            User.roll == identifier,
        )
    ).filter_by(active=True).first()
    if user and user.email:
        raw_token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.utcnow()
            + timedelta(minutes=app.config["RESET_TOKEN_MINUTES"]),
        )
        PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update(
            {"used_at": datetime.utcnow()}
        )
        db.session.add(reset_token)
        db.session.commit()
        try:
            send_password_reset_email(
                user,
                url_for("page_reset_password", token=raw_token, _external=True),
            )
        except (OSError, smtplib.SMTPException, RuntimeError):
            db.session.delete(reset_token)
            db.session.commit()
            app.logger.exception("Password reset email delivery failed")
            return jsonify({"error": "Password reset email could not be sent"}), 503

    return jsonify({"message": "If the account exists, a password reset link has been sent."})


@app.post("/api/auth/reset-password")
def reset_password():
    data = request.get_json(silent=True) or request.form
    raw_token = str(data.get("token", "")).strip()
    password = str(data.get("password", ""))
    if not raw_token or len(password) < 12:
        return jsonify(
            {"error": "A valid token and password of at least 12 characters are required"}
        ), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(
        token_hash=token_hash, used_at=None
    ).first()
    if not reset_token or reset_token.expires_at <= datetime.utcnow():
        return jsonify({"error": "This reset link is invalid or expired"}), 400

    user = db.session.get(User, reset_token.user_id)
    if not user or not user.active:
        return jsonify({"error": "This reset link is invalid or expired"}), 400
    user.password_hash = generate_password_hash(password)
    reset_token.used_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Password updated successfully"})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


@app.post("/api/auth/change-password")
@login_required
def change_password():
    data = request.get_json(silent=True) or request.form
    current_password = str(data.get("currentPassword", ""))
    new_password = str(data.get("newPassword", ""))
    user = current_user()
    if not current_password or not check_password_hash(
        user.password_hash, current_password
    ):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_password) < 12:
        return jsonify({"error": "New password must contain at least 12 characters"}), 400
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"success": True})


@app.post("/api/admin/wardens")
def create_initial_warden():
    setup_key = os.environ.get("ADMIN_SETUP_KEY")
    supplied_key = request.headers.get("X-Admin-Setup-Key")
    if not setup_key or not supplied_key or not secrets.compare_digest(
        supplied_key, setup_key
    ):
        return jsonify({"error": "Admin setup is not configured"}), 403
    if User.query.filter_by(role="warden", active=True).first():
        return jsonify({"error": "An active warden already exists"}), 409

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name or not email or not password or len(password) < 12:
        return jsonify(
            {"error": "Name, email, and a password of at least 12 characters are required"}
        ), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists"}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="warden",
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()}), 201


@app.get("/api/auth/me")
@login_required
def me():
    return jsonify({"user": current_user().to_dict()})


@app.post("/api/verify-face")
@roles_required("student")
def verify_face():
    image = request.files.get("image")
    roll_number = str(request.form.get("roll_number", "")).strip()
    if not image or not roll_number:
        return jsonify({"error": "Image and roll number are required"}), 400
    if image.mimetype not in {"image/jpeg", "image/png", "image/webp"}:
        return jsonify({"error": "Only JPEG, PNG, and WebP images are supported"}), 415
    if not app.config["FACE_SERVICE_TOKEN"]:
        return jsonify({"error": "Face verification service is not configured"}), 503
    try:
        response = requests.post(
            f"{app.config['FACE_SERVICE_URL']}/verify-face",
            headers={"Authorization": f"Bearer {app.config['FACE_SERVICE_TOKEN']}"},
            files={
                "image": (
                    image.filename or "attendance-image",
                    image.stream,
                    image.mimetype,
                )
            },
            data={"roll_number": roll_number},
            timeout=30,
        )
        result = response.json()
    except (requests.RequestException, ValueError):
        app.logger.exception("Face verification request failed")
        return jsonify({"error": "Face verification service is unavailable"}), 503
    return jsonify(result), response.status_code


@app.get("/api/attendance")
@roles_required("student")
def get_attendance():
    user = current_user()
    records = AttendanceRecord.query.filter_by(user_id=user.id).order_by(
        AttendanceRecord.recorded_at.desc()
    ).all()
    return jsonify([record.to_dict() for record in records])


@app.get("/api/parent/attendance")
@roles_required("parent")
def get_parent_attendance():
    profile = StudentProfile.query.filter_by(parent_id=current_user().id).first()
    if not profile:
        return jsonify({"error": "No student is linked to this parent account"}), 404
    records = AttendanceRecord.query.filter_by(user_id=profile.user_id).order_by(
        AttendanceRecord.recorded_at.desc()
    ).all()
    return jsonify(
        {
            "student": profile.to_dict(),
            "records": [record.to_dict() for record in records],
        }
    )


@app.get("/api/parent/child")
@roles_required("parent")
def get_parent_child():
    profile = StudentProfile.query.filter_by(parent_id=current_user().id).first()
    if not profile:
        return jsonify({"error": "No student is linked to this parent account"}), 404
    return jsonify(profile.to_dict())


@app.post("/api/attendance")
@roles_required("student")
def record_attendance():
    user = current_user()
    data = request.get_json(silent=True) or {}
    date = str(data.get("date", "")).strip()
    time = str(data.get("time", "")).strip()
    if not date or not time:
        return jsonify({"error": "Attendance date and time are required"}), 400
    try:
        recorded_at = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({"error": "Invalid attendance date or time"}), 400

    record_id = f"attendance-{user.roll}-{date}"
    existing = db.session.get(AttendanceRecord, record_id)
    if existing:
        return jsonify({"record": existing.to_dict(), "alreadyRecorded": True}), 200

    record = AttendanceRecord(
        id=record_id,
        user_id=user.id,
        roll=user.roll or "",
        recorded_at=recorded_at,
        attendance_type="evening",
        verified=True,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"record": record.to_dict()}), 201


@app.get("/api/warden/students")
@roles_required("warden")
def get_student_roster():
    profiles = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    return jsonify([profile.to_dict() for profile in profiles])


@app.get("/api/warden/headcount")
@roles_required("warden")
def get_warden_headcount():
    profiles = StudentProfile.query.all()
    floors = {}
    for profile in profiles:
        floor = str(profile.floor)
        summary = floors.setdefault(floor, {"floor": profile.floor, "inside": 0, "total": 0})
        summary["total"] += 1
        if profile.status == "inside":
            summary["inside"] += 1
    return jsonify(
        {
            "total": len(profiles),
            "inside": sum(profile.status == "inside" for profile in profiles),
            "out": sum(profile.status == "out" for profile in profiles),
            "floors": [floors[key] for key in sorted(floors, key=int)],
        }
    )


@app.post("/api/warden/students")
@roles_required("warden")
def create_student_accounts():
    data = request.get_json(silent=True) or {}
    student_name = str(data.get("studentName", "")).strip()
    roll = str(data.get("roll", "")).strip()
    student_password = str(data.get("studentPassword", ""))
    parent_name = str(data.get("parentName", "")).strip()
    parent_email = str(data.get("parentEmail", "")).strip().lower()
    parent_password = str(data.get("parentPassword", ""))
    room = str(data.get("room", "")).strip()
    course = str(data.get("course", "")).strip()
    try:
        floor = int(data.get("floor", 1))
    except (TypeError, ValueError):
        floor = 0
    status = str(data.get("status", "inside")).strip()

    if not student_name or not roll or not room or not course or not parent_name or not parent_email:
        return jsonify(
            {"error": "Student, room, course, and parent details are required"}
        ), 400
    if floor not in {1, 2, 3, 4} or status not in {"inside", "out"}:
        return jsonify({"error": "Invalid floor or student status"}), 400
    if len(student_password) < 12 or len(parent_password) < 12:
        return jsonify({"error": "Both passwords must contain at least 12 characters"}), 400
    if User.query.filter_by(roll=roll).first():
        return jsonify({"error": "An account with that roll number already exists"}), 409
    if User.query.filter_by(email=parent_email).first():
        return jsonify({"error": "An account with that parent email already exists"}), 409

    parent = User(
        name=parent_name,
        email=parent_email,
        password_hash=generate_password_hash(parent_password),
        role="parent",
    )
    student = User(
        name=student_name,
        roll=roll,
        password_hash=generate_password_hash(student_password),
        role="student",
    )
    db.session.add_all((parent, student))
    db.session.commit()
    profile = StudentProfile(
        user_id=student.id,
        parent_id=parent.id,
        room=room,
        floor=floor,
        course=course,
        status=status,
    )
    db.session.add(profile)
    db.session.commit()
    return jsonify(
        {
            "success": True,
            "student": student.to_dict(),
            "parent": parent.to_dict(),
            "roster": profile.to_dict(),
        }
    ), 201


@app.route("/api/passes", methods=["GET"])
@login_required
def get_passes():
    roll = request.args.get("roll")
    user = current_user()
    if user.role == "student":
        roll = user.roll
    query = GatePass.query
    if roll:
        query = query.filter_by(roll=str(roll))
    records = query.order_by(GatePass.created_at.desc()).all()
    return jsonify([record.to_dict() for record in records])


@app.route("/api/passes", methods=["POST"])
@roles_required("student")
def create_pass():
    data = request.get_json(silent=True) or {}
    user = current_user()
    new_id = data.get("id") or f"gp-{int(datetime.utcnow().timestamp() * 1000)}"
    existing = GatePass.query.filter_by(id=str(new_id)).first()
    if existing:
        return jsonify({"success": True, "pass": existing.to_dict()}), 200

    record = GatePass(
        id=new_id,
        student_name=user.name,
        roll=user.roll or "",
        pass_type=data.get("type", "outing"),
        type_label=data.get("typeLabel", "Gate Pass"),
        destination=data.get("destination", ""),
        reason=data.get("reason", ""),
        leaving_from=data.get("from", ""),
        return_by=data.get("to", ""),
        parent_status=data.get("parentStatus", "pending"),
        warden_status=data.get("wardenStatus", "pending"),
        created_at=data.get("createdAt") or datetime.utcnow().isoformat(),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"success": True, "pass": record.to_dict()}), 201


@app.route("/api/passes/<pass_id>/status", methods=["PATCH"])
@roles_required("parent", "warden")
def update_status(pass_id):
    data = request.get_json(silent=True) or {}
    record = GatePass.query.filter_by(id=str(pass_id)).first()
    if not record:
        return jsonify({"error": "Pass not found"}), 404
    if "parentStatus" in data:
        record.parent_status = data["parentStatus"]
    if "wardenStatus" in data:
        record.warden_status = data["wardenStatus"]
    db.session.commit()
    return jsonify({"success": True, "pass": record.to_dict()})


@app.route("/api/visitors", methods=["GET"])
@login_required
def get_visitors():
    roll = request.args.get("roll")
    user = current_user()
    if user.role == "student":
        roll = user.roll
    query = Visitor.query
    if roll:
        query = query.filter_by(roll=str(roll))
    records = query.order_by(Visitor.created_at.desc()).all()
    return jsonify([record.to_dict() for record in records])


@app.route("/api/visitors", methods=["POST"])
@roles_required("student", "parent")
def create_visitor():
    data = request.get_json(silent=True) or {}
    user = current_user()
    visitor_id = str(data.get("id") or f"vis-{int(datetime.utcnow().timestamp() * 1000)}")
    record = Visitor.query.filter_by(id=visitor_id).first()
    if record:
        return jsonify({"success": True, "visitor": record.to_dict()}), 200
    record = Visitor(
        id=visitor_id,
        name=data.get("name", ""),
        relation=data.get("relation", "other"),
        relation_label=data.get("relationLabel", "Visitor"),
        student_name=data.get("studentName", user.name),
        roll=str(data.get("roll", user.roll or "")),
        when=data.get("when", ""),
        purpose=data.get("purpose", ""),
        phone=data.get("phone", ""),
        status=data.get("status", "pending"),
        created_by=data.get("createdBy", "student"),
        created_at=data.get("createdAt") or datetime.utcnow().isoformat(),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"success": True, "visitor": record.to_dict()}), 201


@app.route("/api/visitors/<visitor_id>/status", methods=["PATCH"])
@roles_required("parent", "warden")
def update_visitor(visitor_id):
    data = request.get_json(silent=True) or {}
    record = Visitor.query.filter_by(id=str(visitor_id)).first()
    if not record:
        return jsonify({"error": "Visitor not found"}), 404
    for key, field in (
        ("status", "status"),
        ("qrToken", "qr_token"),
        ("qrPayload", "qr_payload"),
        ("qrIssuedAt", "qr_issued_at"),
        ("arrivedAt", "arrived_at"),
    ):
        if key in data:
            setattr(record, field, data[key])
    db.session.commit()
    return jsonify({"success": True, "visitor": record.to_dict()})


@app.route("/api/visitors/verify-entry", methods=["POST"])
@roles_required("warden")
def verify_visitor_entry():
    data = request.get_json(silent=True) or {}
    scan_value = str(data.get("value") or "").strip()
    if not scan_value:
        return jsonify({"error": "QR value required"}), 400

    token = scan_value
    try:
        payload = json.loads(scan_value)
        if isinstance(payload, dict):
            token = str(payload.get("token") or "").strip()
    except (TypeError, ValueError, AttributeError):
        token = scan_value

    record = Visitor.query.filter_by(qr_token=token).first()
    if not record:
        record = Visitor.query.filter_by(qr_payload=scan_value).first()
    if not record:
        return jsonify({"error": "Visitor QR not found"}), 404
    if record.status != "expected":
        return jsonify({"error": f"Visitor pass is already {record.status.replace('_', ' ')}"}), 409

    record.status = "checked_in"
    record.arrived_at = datetime.utcnow().isoformat()
    db.session.commit()
    return jsonify({"success": True, "visitor": record.to_dict()})


@app.route("/api/verify-location", methods=["POST"])
@login_required
def verify_location():
    data = request.get_json(silent=True) or {}
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")
    if user_lat is None or user_lon is None:
        return jsonify({"error": "Coordinates required"}), 400
    try:
        lat = float(user_lat)
        lon = float(user_lon)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid format"}), 400

    distance = calculate_distance_meters(HOSTEL_LAT, HOSTEL_LON, lat, lon)
    return jsonify(
        {
            "inside": distance <= GEOFENCE_RADIUS_METERS,
            "distance_meters": round(distance, 2),
            "allowed_radius": GEOFENCE_RADIUS_METERS,
        }
    )


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/readyz")
def readyz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        app.logger.exception("Readiness database check failed")
        return jsonify({"status": "not_ready", "dependency": "database"}), 503
    return jsonify({"status": "ready"})


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
