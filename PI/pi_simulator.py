import json
import requests
from datetime import datetime
import uuid
import time
import base64 #For decoding image
import cv2 #For Sensor
import logging


logging.basicConfig(
    level=logging.DEBUG,                           # Minimum log level
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("client.log"),         # Log to file
        logging.StreamHandler()                    # Log to console
    ]
)

log = logging.getLogger()


SERVER_URL = "http://127.0.0.1:8000/ingest"


def encode_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        log.error(f"Failed to encode image: {e}")
        raise
    

def capture_image():
    log.info("Waiting for object before capturing image...")
    

    isSucces = wait_for_object()
    if not isSucces:
        log.error("Camera is failing")
        raise Exception("Camera is failing")

    log.info("Opening camera for capture...")
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # MAKE SURE TO INCLUDE CAP_DSHOW ANY TIME YOU SET UP CAMERA(COST ME 3 HOURS)
    time.sleep(1)

    ret, frame = cam.read()
    cam.release()
    log.info("Released camera")


    if not ret:
        log.error("Failed to capture image from camera")
        raise Exception("Failed to capture image")

    filename = f"captured_{uuid.uuid4()}.jpg"
    cv2.imwrite(filename, frame)

    log.info(f"Image captured successfully: {filename}")
    return filename


def send_image_to_server(image_path):
    image_b64 = encode_image_base64(image_path)
    log.info("Encoded Image and starting API request to server...")

    payload = {
        "device_id": "test-device-001",
        "device_name": "video_sensor",
        "device_type": "raspberrypi",
        "timestamp": datetime.utcnow().isoformat(),
        "image_data": image_b64
    }

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=10)

        log.debug(f"Response status: {response.status_code}")
        log.debug(f"Response headers: {response.headers}")
        log.debug(f"Response text: {response.text}")

        response.raise_for_status()

    except requests.exceptions.HTTPError as http_err:
        log.error(f"HTTP error occurred: {http_err}")
        log.error(f"Server returned body: {response.text}")

    except requests.exceptions.Timeout:
        log.error(f"Request timed out contacting {SERVER_URL}")

    except requests.exceptions.RequestException as e:
        log.error(f"General Request exception: {e}")


def wait_for_object(threshold=50000, settle_time=2):

    log.info("Opening camera for motion detection...")
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cam.isOpened():
        log.error("Camera not detected")
        raise Exception("Camera not detected")

    log.info("Waiting for motion... Press Control C on terminal pad to stop or click q")
    time.sleep(1)

    for _ in range(30):             #Get first couple frames out of the way
        cam.read()

    ret, frame1 = cam.read()
    if not ret:
        log.error("Failed reading initial frame1")
        return False

    time.sleep(1)
    ret, frame2 = cam.read()
    if not ret:
        log.error("Failed reading initial frame2")
        return False

    motion_triggered = False
    start_time = 0


    while True:

        # Motion detection logic
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (21, 21), 0)
        _, thresh_frame = cv2.threshold(blur, 40, 255, cv2.THRESH_BINARY)
        motion_pixels = cv2.countNonZero(thresh_frame)

        display_frame = frame2.copy()

        if motion_pixels > threshold and not motion_triggered:
            log.info(f"Motion detected ({motion_pixels} px). Starting settle timer...")
            motion_triggered = True
            start_time = time.time()

        if motion_triggered:
            elapsed_time = time.time() - start_time
            remaining_time = max(0, settle_time - elapsed_time)
            
            # Draw a GREEN rectangle to signal "settle/countdown" mode
            cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], display_frame.shape[0]), (0, 255, 0), 20)
            countdown_text = f"SETTLING: {remaining_time:.1f}s"
            
            # Check if the object has settled (timer finished)
            if remaining_time <= 0:
                print("Timer finished. Capture complete.")
                cam.release()
                cv2.destroyAllWindows()
                return True
            
        else:
            # Not triggered: Display current motion count and 'Waiting' status
            countdown_text = f"WAITING... Threshold: {threshold}"

        # display motion count
        motion_text = f"Motion Pixels: {motion_pixels}"
        
        # Draw text background and display counts/status
        cv2.rectangle(display_frame, (10, 10), (450, 100), (0, 0, 0), -1) 
        cv2.putText(display_frame, motion_text, (20, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(display_frame, countdown_text, (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if motion_triggered else (255, 255, 255), 2)


        # Show the processed frame
        cv2.imshow("Object Detection Preview", display_frame)

        # Exit on q
        if cv2.waitKey(20) & 0xFF == ord('q'):
            log.warning("User stopped the program manually")
            cam.release()
            cv2.destroyAllWindows()
            raise Exception("Stopped by user")

        frame1 = frame2
        ret, frame2 = cam.read()

        if not ret:
            log.error("Camera stopped returning frames! Exiting motion loop.")
            break

    cam.release()
    cv2.destroyAllWindows()
    log.error("Since Camera is not working Closed Camera")

    return False



if __name__ == "__main__":
    counter = 1
    while counter > 0:
        try:
            img_path = capture_image()
            send_image_to_server(img_path)
            log.info("Image processing cycle completed successfully")
            counter -= 1
        except Exception as e:
            log.error(f"Error occurred: {e}")

