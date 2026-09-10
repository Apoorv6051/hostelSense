from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Backend store for hostel passes
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

# --- Backend API Endpoints (/api/passes) ---

# 1. Fetch all passes
@app.route("/api/passes", methods=["GET"])
def get_passes():
    roll = request.args.get("roll")
    if roll:
        filtered = [p for p in passes_data if str(p.get("roll")) == str(roll)]
        return jsonify(filtered)
    return jsonify(passes_data)

# 2. Submit a new gate pass request
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

# 3. Update status (approve / reject)
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

if __name__ == "__main__":
    app.run(debug=True)