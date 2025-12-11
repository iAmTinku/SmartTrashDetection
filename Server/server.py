from fastapi import FastAPI, Request, HTTPException, status
from datetime import datetime
import json
import uuid
import base64
import os
import logging
from api import ingest
from config import MODEL_PATH, IMG_SIZE, CONFIDENCE_THRESHOLD, CLASS_NAMES, S3_GCS_PATH, IMAGE_SAVE_PATH
from mlmodel import ImageMetadataExtractor, ModelPredictor
from dbconnection import get_db_connection
import query

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

metadata_extractor = ImageMetadataExtractor() 
model_predictor = ModelPredictor(MODEL_PATH, IMG_SIZE, CLASS_NAMES) 
conn = get_db_connection()

app = FastAPI()

@app.post("/ingest")
async def ingest_route(request: Request):
    logger.debug("Entered Method")
    return await ingest(request,metadata_extractor, model_predictor, conn)
