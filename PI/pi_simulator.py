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
    wait_for_object()  # Wait until movement seen

    cam = cv2.VideoCapture(0) # Connect to camera  #cam = cv2.VideoCapture(0,cv2.CAP_DSHOW)
    time.sleep(1) # Let camera startup

    ret, frame = cam.read() # Capture Frame
    cam.release() 

    if not ret: #If frame is bad
        raise Exception("Failed to capture image")

    filename = f"captured_{uuid.uuid4()}.jpg"
    cv2.imwrite(filename, frame) # Save captured image
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



def wait_for_object(threshold=50000, settle_time=5):
    """
    Waits for an object to appear. Once motion is detected, 
    a countdown starts and runs to completion, regardless of 
    whether the object leaves before the timer finishes.
    """
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cam.isOpened():
        raise Exception("Camera not detected")

    print("Waiting for motion... Press 'q' to stop.")
    time.sleep(1)

    for _ in range(30):
        cam.read()
    # Read two initial frames
    ret, frame1 = cam.read()
    if not ret: return False
    
    time.sleep(1)

    ret, frame2 = cam.read()
    if not ret: return False

    # State variables
    motion_triggered = False
    start_time = 0

    while True:
        # --- 1. Core Motion Calculation ---
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        # Increased blur for better results
        blur = cv2.GaussianBlur(gray, (21, 21), 0) 
        
        # Count changed pixels
        _, thresh = cv2.threshold(blur, 40, 255, cv2.THRESH_BINARY) 
        motion_pixels = cv2.countNonZero(thresh)

        # Clone the frame for drawing text
        display_frame = frame2.copy() 
        
        
        # Check for initial motion trigger
        # CRITICAL: This is the trigger check. It only runs ONCE.
        if motion_pixels > threshold and not motion_triggered:
            print(f"Motion detected ({motion_pixels} pixels) — starting settle countdown.")
            motion_triggered = True
            start_time = time.time()
        
        # Handle the countdown phase
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

        # --- 3. Display Motion Count and Status ---
        motion_text = f"Motion Pixels: {motion_pixels}"
        
        # Draw text background and display counts/status
        cv2.rectangle(display_frame, (10, 10), (450, 100), (0, 0, 0), -1) 
        cv2.putText(display_frame, motion_text, (20, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(display_frame, countdown_text, (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if motion_triggered else (255, 255, 255), 2)


        # Show the processed frame
        cv2.imshow("Object Detection Preview", display_frame)

        # --- 4. Loop Housekeeping ---
        if cv2.waitKey(20) & 0xFF == ord('q'):
            cam.release()
            cv2.destroyAllWindows()
            raise Exception("Stopped by user")

        frame1 = frame2
        ret, frame2 = cam.read()
        if not ret:
            print("Error reading frame, exiting loop.")
            break

    cam.release()
    cv2.destroyAllWindows()
    return False



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

