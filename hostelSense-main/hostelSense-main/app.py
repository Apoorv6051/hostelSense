import math
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- Geofence Configuration ---
HOSTEL_LAT = 26.4499   # Hostel latitude
HOSTEL_LON = 80.3319   # Hostel longitude
GEOFENCE_RADIUS_METERS = 300  # Permitted perimeter in meters

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two points using Haversine formula."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- In-Memory Store for Hostel Passes ---
passes_data = [
    {
        "id": "gp-1",
        "studentName": "Aarav Sharma",
        "roll": "2401641520038",
        "type": "home",
        "typeLabel": "Home visit",
        "destination": "Lucknow",
        "reason": "Family function",
        "from": "2026-09-12T17:00",
        "to": "2026-09-14T20:00",
        "parentStatus": "approved",
        "wardenStatus": "pending",
        "createdAt": "2026-09-09T18:00:00.000Z"
    }
]

# --- Frontend Page Routes ---

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

# --- API Endpoints ---

@app.route("/api/passes", methods=["GET"])
def get_passes():
    roll = request.args.get("roll")
    if roll:
        filtered = [p for p in passes_data if str(p.get("roll")) == str(roll)]
        return jsonify(filtered)
    return jsonify(passes_data)

@app.route("/api/passes", methods=["POST"])
def create_pass():
    data = request.get_json() or {}
    new_pass = {
        "id": data.get("id") or f"gp-{len(passes_data) + 1}",
        "studentName": data.get("studentName", "Student"),
        "roll": data.get("roll", ""),
        "type": data.get("type", "outing"),
        "typeLabel": data.get("typeLabel", "Gate Pass"),
        "destination": data.get("destination", ""),
        "reason": data.get("reason", ""),
        "from": data.get("from", ""),
        "to": data.get("to", ""),
        "parentStatus": data.get("parentStatus", "pending"),
        "wardenStatus": data.get("wardenStatus", "pending"),
        "createdAt": data.get("createdAt", "")
    }
    passes_data.insert(0, new_pass)
    return jsonify({"success": True, "pass": new_pass}), 201

@app.route("/api/passes/<pass_id>/status", methods=["PATCH"])
def update_status(pass_id):
    data = request.get_json() or {}
    for p in passes_data:
        if str(p["id"]) == str(pass_id):
            if "parentStatus" in data:
                p["parentStatus"] = data["parentStatus"]
            if "wardenStatus" in data:
                p["wardenStatus"] = data["wardenStatus"]
            return jsonify({"success": True, "pass": p})
            
    return jsonify({"error": "Pass not found"}), 404

# --- Geofence Endpoint ---
@app.route("/api/verify-location", methods=["POST"])
def verify_location():
    data = request.get_json() or {}
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")

    if user_lat is None or user_lon is None:
        return jsonify({"error": "Latitude and longitude required"}), 400

    try:
        lat = float(user_lat)
        lon = float(user_lon)
    except ValueError:
        return jsonify({"error": "Invalid coordinates format"}), 400

    distance = calculate_distance_meters(HOSTEL_LAT, HOSTEL_LON, lat, lon)
    is_inside = distance <= GEOFENCE_RADIUS_METERS

    return jsonify({
        "inside": is_inside,
        "distance_meters": round(distance, 2),
        "allowed_radius": GEOFENCE_RADIUS_METERS,
        "status": "Inside Hostel Perimeter" if is_inside else "Outside Hostel Perimeter"
    })

if __name__ == "__main__":
    app.run(debug=True)