from fastapi import FastAPI, Request
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
# Import MobileNetV2's specific preprocessing function
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

print(tf.__version__)
print(tf.keras.__version__)


load_dotenv()

MODEL_PATH = "../model/downloaded_model/waste_classification_model.h5" 
IMG_SIZE = (224, 224) 
CONFIDENCE_THRESHOLD = 0.65 
# Define the class names in the EXACT order your model was trained
CLASS_NAMES = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']

app = FastAPI()


# Load the model only ONCE when the API starts.
try:
    Model = tf.keras.models.load_model(MODEL_PATH)
    print("✅ Model loaded successfully.")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    Model = None

# ---- Postgres Connection ----
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
conn.autocommit = True





@app.post("/ingest")
async def ingest(request: Request):

    payload = await request.json()

    # Convert incoming device name → deterministic UUID
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, payload["device_id"])

    # True random ingestion UUID
    ingestion_id = uuid.uuid4()

    image_b64 = payload["image_data"]
    try:
        image_b64 = image_b64.strip().replace("\n", "")
        image_bytes = base64.b64decode(image_b64, validate=True)
    except Exception as e:
        return {"error": f"Failed to decode Base64 image: {str(e)}"}

    image_filename = f"{payload['image_id']}.jpg"

    save_path = os.path.join("RecievedPictures", image_filename)
    os.makedirs("RecievedPictures", exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(image_bytes)



    predicted_class, confidence, _ = predict_single_image(image_bytes, Model)

    is_high_confidence = confidence >= CONFIDENCE_THRESHOLD
    
    # --- Decision Logic and Message based on confidence (as previously discussed) ---
    if Model is None:
        process_status = "model_error"
        warning_message = "Model failed to load on server start."
        user_alert_message = "System Error: Model is unavailable."
    elif is_high_confidence:
        process_status = "classified"
        warning_message = "NONE"
        user_alert_message = f"✅ Classified as **{predicted_class}** with {confidence:.2%} probability."
    else:
        # Low confidence prediction
        process_status = "review_needed"
        warning_message = "Low confidence prediction moved to review queue."
        user_alert_message = f"⚠️ Warning: Predicted {predicted_class} but confidence is only {confidence:.2%}. Review suggested."
        # Note: You still need to implement the separate 'review_queue' table insertion here.


    cursor = conn.cursor()
    #Add prediciton and confidence
    cursor.execute("""
        INSERT INTO ingestion_log (
            ingestion_id,
            device_id,
            raw_json,
            received_at,
            process_status,
            error_message,
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        str(ingestion_id),
        str(device_uuid),
        json.dumps(payload),
        datetime.utcnow(),
        "pending",
        "NONE" 
    ))

    cursor.close()

    return {
        "status": "ok",
        "ingestion_id": str(ingestion_id),
        "device_id_uuid": str(device_uuid),
        "message": "Data received, image stored, ingestion logged",
        "prediction": predicted_class,
        "confidence": float(confidence),
        "prediction_alert": user_alert_message
    }


def predict_single_image(image_bytes, Model):
    """Takes raw image bytes, preprocesses it, and returns the prediction."""
    if Model is None:
        return "MODEL_ERROR", 0.0, "Model failed to load"
        
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