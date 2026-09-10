import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Database Configuration ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hostelsense.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Database Model ---
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
            "createdAt": self.created_at
        }

# --- Geofence Configuration ---
HOSTEL_LAT = 26.4499
HOSTEL_LON = 80.3319
GEOFENCE_RADIUS_METERS = 300

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- Page Routes ---

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/student")
@app.route("/student.html")
def student():
    return render_template("student.html")

@app.route("/warden")
@app.route("/warden.html")
def warden():
    return render_template("warden.html")

@app.route("/parent")
@app.route("/parent.html")
def parent():
    return render_template("parent.html")

@app.route("/gate-pass")
@app.route("/gate-pass.html")
def gate_pass():
    return render_template("gate-pass.html")

# --- Database API Endpoints ---

# 1. Fetch passes from SQLite
@app.route("/api/passes", methods=["GET"])
def get_passes():
    roll = request.args.get("roll")
    if roll:
        records = GatePass.query.filter_by(roll=str(roll)).order_by(GatePass.created_at.desc()).all()
    else:
        records = GatePass.query.order_by(GatePass.created_at.desc()).all()
    return jsonify([record.to_dict() for record in records])

# 2. Insert new pass into SQLite
@app.route("/api/passes", methods=["POST"])
def create_pass():
    data = request.get_json() or {}
    new_id = data.get("id") or f"gp-{int(datetime.utcnow().timestamp() * 1000)}"

    new_record = GatePass(
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
        created_at=data.get("createdAt") or datetime.utcnow().isoformat()
    )

    db.session.add(new_record)
    db.session.commit()
    return jsonify({"success": True, "pass": new_record.to_dict()}), 201

# 3. Update parent/warden status in SQLite
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

# --- Geofence Endpoint ---
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
    except ValueError:
        return jsonify({"error": "Invalid format"}), 400

    distance = calculate_distance_meters(HOSTEL_LAT, HOSTEL_LON, lat, lon)
    is_inside = distance <= GEOFENCE_RADIUS_METERS

    return jsonify({
        "inside": is_inside,
        "distance_meters": round(distance, 2),
        "allowed_radius": GEOFENCE_RADIUS_METERS
    })

# --- Database Initialization on App Start ---
with app.app_context():
    db.create_all()
    # Seed an initial sample pass if database is empty
    if not GatePass.query.first():
        seed_pass = GatePass(
            id="gp-101",
            student_name="Aarav Sharma",
            roll="2401641520038",
            pass_type="home",
            type_label="Home visit",
            destination="Lucknow",
            reason="Family function",
            leaving_from="2026-09-12T17:00",
            return_by="2026-09-14T20:00",
            parent_status="approved",
            warden_status="pending"
        )
        db.session.add(seed_pass)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)