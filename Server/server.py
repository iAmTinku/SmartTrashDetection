from fastapi import FastAPI, Request
from datetime import datetime
import psycopg2
import json
import uuid
import base64
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

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


    cursor = conn.cursor()
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
        "pending",
        "NONE" 
    ))

    cursor.close()

    return {
        "status": "ok",
        "ingestion_id": str(ingestion_id),
        "device_id_uuid": str(device_uuid),
        "message": "Data received, image stored, ingestion logged"
    }
