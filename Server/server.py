from fastapi import FastAPI, Request, HTTPException, status
from datetime import datetime
import psycopg2
import json
import uuid
import base64
import os
from dotenv import load_dotenv

import io
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

import hashlib
from PIL import Image

# --- 💡 NEW: Logging Setup ---
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Existing Setup ---
print(tf.__version__)
print(tf.keras.__version__)

load_dotenv()

MODEL_PATH = "../model/downloaded_model/waste_classification_model.h5" 
IMG_SIZE = (224, 224) 
CONFIDENCE_THRESHOLD = 0.65 
CLASS_NAMES = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']
s3_gcs_path = "https://S3mockUrl"
app = FastAPI()

# Load the model only ONCE when the API starts.
try:
    Model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model loaded successfully.")
except Exception as e:
    logger.error(f"❌ Error loading model: {e}")
    Model = None

# --- Postgres Connection ---
try:
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    conn.autocommit = True
    logger.info("✅ PostgreSQL connected successfully.")
except Exception as e:
    logger.error(f"❌ Error connecting to PostgreSQL: {e}")
    conn = None


def predict_single_image(image_bytes, Model):
    """Takes raw image bytes, preprocesses it, and returns the prediction."""
    if Model is None:
        return "MODEL_ERROR", 0.0, None
        
    try:
        # 1. Load, Resize, and Convert to Array (H, W, C)
        img = image.load_img(io.BytesIO(image_bytes), target_size=IMG_SIZE)
        img_array = image.img_to_array(img)

        # 2. Add Batch Dimension: (224, 224, 3) -> (1, 224, 224, 3)
        input_tensor = np.expand_dims(img_array, axis=0)

        # 3. Apply MobileNetV2 Scaling: [0, 255] -> [-1, 1]
        processed_input = preprocess_input(input_tensor)

        # 4. Predict
        raw_prediction = Model.predict(processed_input)
        
        # 5. Get results
        probabilities = raw_prediction[0]
        predicted_index = np.argmax(probabilities)
        confidence = np.max(probabilities)
        predicted_class = CLASS_NAMES[predicted_index]

        return predicted_class, confidence, probabilities
    
    except Exception as e:
        logger.error(f"Error during model prediction: {e}")
        return "PREDICTION_FAIL", 0.0, None



def get_image_metadata(image_bytes):
    """Calculates image checksum, resolution, and format."""
    try:
        # Checksum (SHA256 for integrity)
        checksum = hashlib.sha256(image_bytes).hexdigest()
        
        # Open image from bytes to get resolution and format
        img = Image.open(io.BytesIO(image_bytes))
        resolution_x, resolution_y = img.size
        
        # Format (convert to lowercase for consistency with DB schema 'jpg'/'png')
        img_format = img.format.lower() if img.format else 'unknown'
        
        return checksum, resolution_x, resolution_y, img_format
    
    except Exception as e:
        logger.error(f"Error extracting image metadata: {e}")
        return None, None, None, None






@app.post("/ingest")
async def ingest(request: Request):
    
    # 1. --- Payload Reading (Handles Invalid JSON) ---
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        logger.error("Client sent invalid JSON payload.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload sent in request body."
        )

    # 2. --- Payload Validation ---
    if "device_id" not in payload or "image_data" not in payload or "image_id" not in payload:
        logger.error(f"Missing keys in payload: {payload.keys()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required keys ('device_id', 'image_id', 'image_data') in payload."
        )
    
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, payload["device_id"])
    ingestion_id = uuid.uuid4()
    image_b64 = payload["image_data"]
    
    # 3. --- Base64 Decoding and Validation ---
    try:
        image_b64 = image_b64.strip().replace("\n", "")
        image_bytes = base64.b64decode(image_b64, validate=True)
    except Exception as e:
        logger.error(f"Failed to decode Base64 image for ingestion {ingestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode Base64 image data. Check encoding: {str(e)}"
        )

    # 4. --- Image Saving ---
    checksum, res_x, res_y, img_format = get_image_metadata(image_bytes)

    image_filename = f"{payload['image_id']}.jpg"
    save_path = os.path.join("RecievedPictures", image_filename)
    try:
        os.makedirs("RecievedPictures", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Image {payload['image_id']} saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to save image file: {e}")
        # Not critical enough to fail the whole request, but log it.
        pass

    # 5. --- Prediction ---
    predicted_class, confidence, probabilities = predict_single_image(image_bytes, Model)

    if predicted_class == "MODEL_ERROR":
        process_status = "pending"
        warning_message = "Model failed to load on server start."
        user_alert_message = "System Error: Model is unavailable."
    elif predicted_class == "PREDICTION_FAIL":
        process_status = "pending"
        warning_message = "Error occurred during model prediction."
        user_alert_message = "System Error: Prediction failed."
    else:
        is_high_confidence = confidence >= CONFIDENCE_THRESHOLD
        if is_high_confidence:
            process_status = "pending"
            warning_message = "NONE"
            user_alert_message = f"✅ Classified as **{predicted_class}** with {confidence:.2%} probability."
        else:
            process_status = "pending"
            warning_message = "Low confidence prediction moved to review queue."
            user_alert_message = f"⚠️ Warning: Predicted {predicted_class} but confidence is only {confidence:.2%}. Review suggested."
            # Implement separate review_queue table insertion here if needed

    # 6. --- Database Logging ---
    if conn is None:
        logger.error("Skipping DB log: Connection is not available.")
        # ...
    else:
        # Check if we have valid metadata before proceeding with image insertion
        if not all([checksum, res_x, res_y, img_format]):
            logger.warning(f"Skipping IMAGE table insert for {ingestion_id}: Missing image metadata.")
            # Set a failure status for ingestion_log, if it wasn't already an ML error
            if process_status not in ["model_error", "prediction_fail"]:
                 process_status = "metadata_fail"
                 warning_message = "Image metadata (checksum/resolution) extraction failed."
        try:
            cursor = conn.cursor()
            
            # Note: I've updated the SQL to match the parameters being passed below.
            cursor.execute("""
                INSERT INTO ingestion_log (
                    ingestion_id,
                    device_id,
                    raw_json,
                    received_at,
                    process_status,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                str(ingestion_id),
                str(device_uuid),
                json.dumps(payload),
                datetime.utcnow(),
                process_status,
                warning_message
            ))
            
            if all([checksum, res_x, res_y, img_format]):
                # You can use the image_id from the payload or generate a new UUID. 
                # Assuming the image_id from the payload is the one you want to use as primary key.
                image_db_id = uuid.uuid5(uuid.NAMESPACE_DNS, payload["image_id"]) 
                
                # Determine the confirmed_class based on high confidence
                confirmed_class = predicted_class if is_high_confidence else None
                
                cursor.execute("""
                    INSERT INTO image (
                        image_id,
                        ingestion_id,
                        capture_timestamp,
                        image_path,
                        resolution_x,
                        resolution_y,
                        checksum,
                        format,
                        confirmed_class
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (checksum) DO NOTHING; -- Prevents re-insertion of identical images
                """, (
                    str(image_db_id), # Use image_id derived from payload as PK
                    str(ingestion_id),
                    datetime.utcnow(), # Use current time as capture_timestamp (or parse from payload if available)
                    s3_gcs_path, # Path where the image is stored (mock URL)
                    res_x,
                    res_y,
                    checksum,
                    img_format,
                    confirmed_class
                ))
                logger.info(f"Image {image_db_id} inserted into IMAGE table.")


            cursor.close()
            logger.info(f"Ingestion {ingestion_id} logged to DB with status: {process_status}")

        except psycopg2.Error as db_error:
            # Catch specific DB errors
            logger.error(f"PostgreSQL INSERT error for {ingestion_id}: {db_error}")
            # You might choose to raise a 500 here if DB logging is critical
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database logging failed.")


    # 7. --- Final Response ---
    return {
        "status": "ok",
        "ingestion_id": str(ingestion_id),
        "device_id_uuid": str(device_uuid),
        "message": "Data processed.",
        "prediction": predicted_class,
        "confidence": float(confidence),
        "prediction_alert": user_alert_message
    }