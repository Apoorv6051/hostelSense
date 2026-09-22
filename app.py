import json
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


@app.route("/api/visitors", methods=["GET"])
def get_visitors():
    roll = request.args.get("roll")
    query = Visitor.query
    if roll:
        query = query.filter_by(roll=str(roll))
    records = query.order_by(Visitor.created_at.desc()).all()
    return jsonify([record.to_dict() for record in records])


@app.route("/api/visitors", methods=["POST"])
def create_visitor():
    data = request.get_json() or {}
    visitor_id = str(data.get("id") or f"vis-{int(datetime.utcnow().timestamp() * 1000)}")
    record = Visitor.query.filter_by(id=visitor_id).first()
    if record:
        return jsonify({"success": True, "visitor": record.to_dict()}), 200
    record = Visitor(
        id=visitor_id,
        name=data.get("name", ""),
        relation=data.get("relation", "other"),
        relation_label=data.get("relationLabel", "Visitor"),
        student_name=data.get("studentName", ""),
        roll=str(data.get("roll", "")),
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
def update_visitor(visitor_id):
    data = request.get_json() or {}
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
def verify_visitor_entry():
    data = request.get_json() or {}
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
