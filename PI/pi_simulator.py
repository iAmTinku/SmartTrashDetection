#For decoding image
import base64
import json
import requests
from datetime import datetime
import uuid

#For Pictures
import cv2
import time

SERVER_URL = "http://127.0.0.1:8000/ingest"  # FastAPI or Flask endpoint

def encode_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def capture_image():
    wait_for_object()  # Wait until something moves in front of camera

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW fixes Windows freezes

    if not cam.isOpened():
        raise Exception("Camera not detected")

    time.sleep(0.5)  # allow camera to warm up

    # read a few frames to stabilize exposure
    for _ in range(5):
        ret, frame = cam.read()

    cam.release()

    if not ret:
        raise Exception("Failed to capture image")

    filename = f"captured_{uuid.uuid4()}.jpg"
    cv2.imwrite(filename, frame)
    return filename

def send_image_to_server(image_path):

    image_b64 = encode_image_base64(image_path)
    
    payload = {
        "device_id": "test-device-001",
        "image_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "resolution_x": 640,
            "resolution_y": 480,
            "format": "jpg"
        },
        "image_data": image_b64
    }

    response = requests.post(SERVER_URL, json=payload)
    print("Status:", response.status_code)
    print("Raw Response:", response.text)   

def wait_for_object(threshold=30):
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cam.isOpened():
        raise Exception("Camera not detected")

    # Warm-up
    time.sleep(0.5)

    ret, frame1 = cam.read()
    ret, frame2 = cam.read()

    while True:
        diff = cv2.absdiff(frame1, frame2)  
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        movement = cv2.countNonZero(thresh)

        if movement > threshold:  
            cam.release()
            return True  # Object entered scene

        frame1 = frame2
        ret, frame2 = cam.read()


if __name__ == "__main__":
    counter = 2
    while counter > 0:
        try:
            img_path = capture_image()
            send_image_to_server(img_path)
            counter -= 1
        except Exception as e:
            print("Error:", e)

        #time.sleep(5)

