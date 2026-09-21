from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import face_recognition
import json
import os
import numpy as np

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def face_check_page():
    return send_file("test-camera.html")


def load_known_encodings():
    if not os.path.exists("encodings.json"):
        return {}
    with open("encodings.json", "r") as f:
        return json.load(f)


@app.route("/verify-face", methods=["POST"])
def verify_face():
    if "image" not in request.files:
        return jsonify({"error": "No image was provided"}), 400

    roll_number = request.form.get("roll_number")
    if not roll_number:
        return jsonify({"error": "Roll number is required"}), 400

    file = request.files["image"]
    temp_path = "temp_capture.jpg"
    file.save(temp_path)

    live_image = face_recognition.load_image_file(temp_path)
    live_encodings = face_recognition.face_encodings(live_image)

    if len(live_encodings) == 0:
        return jsonify({"matched": False, "reason": "No face was detected in the image"}), 200

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
    app.run(debug=True, port=5001)