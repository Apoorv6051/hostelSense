import face_recognition
import json
import os


def register_student(roll_number, image_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        print("No face was detected in the image. Please try a different photo.")
        return

    encoding = encodings[0].tolist()

    if os.path.exists("encodings.json"):
        with open("encodings.json", "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[roll_number] = encoding

    with open("encodings.json", "w") as f:
        json.dump(data, f)

    print(f"Student {roll_number} has been registered successfully.")


if __name__ == "__main__":
    register_student("2401641520038", "known_faces/aarav.jpg")