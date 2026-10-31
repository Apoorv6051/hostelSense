from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import face_recognition
import json
import os
import numpy as np
import secrets
import tempfile
from pathlib import Path

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
allowed_origins = [origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS(app, origins=allowed_origins or [])


@app.route("/", methods=["GET"])
def face_check_page():
    return send_file("test-camera.html")


def load_known_encodings():
    if not os.path.exists("encodings.json"):
        return {}
    with open("encodings.json", "r") as f:
        return json.load(f)


def authorized_request():
    expected = os.environ.get("FACE_SERVICE_TOKEN")
    supplied = request.headers.get("Authorization", "")
    return bool(expected and secrets.compare_digest(supplied, f"Bearer {expected}"))


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})


@app.route("/verify-face", methods=["POST"])
def verify_face():
    if not authorized_request():
        return jsonify({"error": "Unauthorized"}), 401
    if "image" not in request.files:
        return jsonify({"error": "No image was provided"}), 400

    roll_number = request.form.get("roll_number")
    if not roll_number:
        return jsonify({"error": "Roll number is required"}), 400

    file = request.files["image"]
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return jsonify({"error": "Unsupported image format"}), 415

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
        file.save(temp_path)
        live_image = face_recognition.load_image_file(temp_path)
        live_encodings = face_recognition.face_encodings(live_image)
    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    if len(live_encodings) == 0:
        return jsonify({"matched": False, "reason": "No face was detected in the image"}), 200
    if len(live_encodings) > 1:
        return jsonify({"matched": False, "reason": "Only one face may be present"}), 200

    live_encoding = live_encodings[0]

    known_data = load_known_encodings()
    if roll_number not in known_data:
        return jsonify({"error": "This student is not registered"}), 404

    known_encoding = np.array(known_data[roll_number])

    distance = face_recognition.face_distance([known_encoding], live_encoding)[0]
    matched = distance <= 0.45

    return jsonify({
        "matched": bool(matched),
        "distance": float(distance),
        "roll_number": roll_number
    })


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )