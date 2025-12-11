import json
import logging
import uuid
import base64
from fastapi import HTTPException, Request, status
import logging
from config import MODEL_PATH, IMG_SIZE, CONFIDENCE_THRESHOLD, CLASS_NAMES, S3_GCS_PATH, IMAGE_SAVE_PATH
from mlmodel import ImageMetadataExtractor, ModelPredictor
from dbconnection import get_db_connection
import query
import numpy as np

logger = logging.getLogger(__name__)

def convert_np(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: convert_np(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_np(v) for v in obj]
    return obj

def save_image(image_bytes, image_id):
    
    image_filename = f"{image_id}.jpg"
    save_path = os.path.join(IMAGE_SAVE_PATH, image_filename)
    try:
        os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Image {image_id} saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to save image file: {e}")


async def ingest(request: Request, metadata_extractor: ImageMetadataExtractor, model_predictor: ModelPredictor,conn: any):


        logger.info("Inside api.py")

        # Read raw body (bytes)
        raw_text = await request.body()
        raw_text = raw_text.decode("utf-8", errors="replace")

        # Log raw text safely
        #logger.warning(f"Raw incoming body: {raw_body.decode('utf-8', errors='replace')}")

        #Save into rejects log table
        def log_reject(reason: str):
            try:
                with conn.cursor() as cursor:
                    payload = {
                        "reason": reason,
                        "raw_body": raw_text
                    }
                    query.insert_request_log_rejects(cursor, payload)
                    logger.warning(f"Rejected request logged: {reason}")
            except Exception as e:
                logger.error(f"Failed to insert into rejects log: {e}")

        # JSON Validation
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            log_reject("Invalid JSON format")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )

        # Payload Validation
        required_keys = ["device_id", "device_name", "device_type", "image_data"]
        for key in required_keys:
            if key not in payload:
                log_reject(f"Missing required key: {key}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required key: {key}"
                )
        # image validation to avoid duplicates 
        #if is_duplicate_image(payload["image_data"]):
        #     raise HTTPException(
        #         status_code=400,
        #         detail="Duplicate image"
        #     )

        logger.info("finished validation")


        device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, payload["device_id"])
        ingestion_id = uuid.uuid4()
        image_id = uuid.uuid4()


        image_b64 = payload["image_data"]
        device_id = payload["device_id"]
        device_name = payload["device_name"]
        device_type = payload["device_type"]
        timestamp = payload["timestamp"]
        logger.debug("Received payload: %s", image_b64)
        logger.debug("Received payload: %s", device_id)
        logger.debug("Received payload: %s", device_name)
        logger.debug("Received payload: %s", device_type)
        logger.debug("Received payload: %s", timestamp)

        # First Transformation On Image Decoding
        try:
            image_b64 = image_b64.strip().replace("\n", "")
            image_bytes = base64.b64decode(image_b64, validate=True)
            logger.info("Decoded image and back to bytes")
        except Exception as e:
            logger.error(f"Failed to decode Base64 image for ingestion {ingestion_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decode Base64 image data. Check encoding: {str(e)}"
            )
        

        #Save into device, image_data and image tables
        try:
            with conn.cursor() as cursor: 
                query.insert_device(cursor, device_id, device_name, device_type)
        except Exception as e:
            logger.error(f"Error Occured While saving to device table: {e}")

        try:
            with conn.cursor() as cursor: 
                query.insert_image_data(cursor, ingestion_id, device_id, image_bytes)
        except Exception as e:
            logger.error(f"Error Occured While saving to image_data table: {e}")
            
        logger.debug("Tried Saving first two tables")

        #save_image(image_bytes) # Assuming this saves to S3, extract url and save in db for location

        # Machine Learning Model
        if model_predictor is not None:
            predicted_class, confidence, probabilities = model_predictor.predict(image_bytes)
            logger.debug(probabilities)
        else:
            predicted_class = "MODEL_ERROR"
            confidence = 0.0
            probabilities = {}
            logger.error("model_predictor is not initialized.")

        is_high_confidence = False # Initialize variable to avoid NameError later

        if predicted_class == "MODEL_ERROR":
            process_status = "model_error" # Use snake_case for consistency/DB
            warning_message = "Model failed to load on server start."
            user_alert_message = "System Error: Model is unavailable."
        elif predicted_class == "PREDICTION_FAIL":
            process_status = "prediction_fail"
            warning_message = "Error occurred during model prediction."
            user_alert_message = "System Error: Prediction failed."
        else:
            is_high_confidence = confidence >= CONFIDENCE_THRESHOLD 
            if is_high_confidence:
                process_status = "processed" # Assuming high confidence means processing is complete
                warning_message = "NONE"
                user_alert_message = f"✅ Classified as **{predicted_class}** with {confidence:.2%} probability."
            else:
                process_status = "review_pending" # More descriptive status
                warning_message = "Low confidence prediction moved to review queue."
                user_alert_message = f"⚠️ Warning: Predicted {predicted_class} but confidence is only {confidence:.2%}. Review suggested."

        try:
            with conn.cursor() as cursor: 
                new_confidence = convert_np(confidence)
                query.insert_image_metadata(cursor, image_id, ingestion_id, "s3url", predicted_class, new_confidence, None)
        except Exception as e:
            logger.error(f"Error Occured While saving to image table: {e}")



        # Response back to device
        return {
            "status": "ok",
            "ingestion_id": str(ingestion_id),
            "device_id_uuid": str(device_uuid),
            "message": "Data processed.",
            "prediction": predicted_class,
            "confidence": float(confidence),
            "prediction_alert": user_alert_message
        }
    