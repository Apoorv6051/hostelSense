import math
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hostelsense.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

HOSTEL_LAT = 26.4499
HOSTEL_LON = 80.3319
GEOFENCE_RADIUS_METERS = 300


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

        def view(template_name=template):
            return render_template(template_name)

        view.__name__ = endpoint
        app.add_url_rule(path, endpoint, view)


register_pages()


@app.route("/api/passes", methods=["GET"])
def get_passes():
    roll = request.args.get("roll")
    query = GatePass.query
    if roll:
        query = query.filter_by(roll=str(roll))
    records = query.order_by(GatePass.created_at.desc()).all()
    return jsonify([record.to_dict() for record in records])


@app.route("/api/passes", methods=["POST"])
def create_pass():
    data = request.get_json() or {}
    new_id = data.get("id") or f"gp-{int(datetime.utcnow().timestamp() * 1000)}"
    existing = GatePass.query.filter_by(id=str(new_id)).first()
    if existing:
        return jsonify({"success": True, "pass": existing.to_dict()}), 200

    record = GatePass(
        id=new_id,
        student_name=data.get("studentName", "Student"),
        roll=data.get("roll", ""),
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
def update_status(pass_id):
    data = request.get_json() or {}
    record = GatePass.query.filter_by(id=str(pass_id)).first()
    if not record:
        return jsonify({"error": "Pass not found"}), 404
    if "parentStatus" in data:
        record.parent_status = data["parentStatus"]
    if "wardenStatus" in data:
        record.warden_status = data["wardenStatus"]
    db.session.commit()
    return jsonify({"success": True, "pass": record.to_dict()})


@app.route("/api/verify-location", methods=["POST"])
def verify_location():
    data = request.get_json() or {}
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


def seed_if_empty():
    if GatePass.query.first():
        return
    db.session.add(
        GatePass(
            id="gp-demo-1",
            student_name="Aarav Sharma",
            roll="2401641520038",
            pass_type="home",
            type_label="Home visit",
            destination="Home — Lucknow",
            reason="Weekend visit with family",
            leaving_from="2026-07-26T10:00",
            return_by="2026-07-27T20:00",
            parent_status="approved",
            warden_status="pending",
        )
    )
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_if_empty()


if __name__ == "__main__":
    app.run(debug=True)
