import os
from dotenv import load_dotenv

load_dotenv()

# Model configuration
MODEL_PATH = "../model/downloaded_model/waste_classification_model.h5"
IMG_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.65
CLASS_NAMES = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']

# Database configuration
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# S3/GCS path (mock)
S3_GCS_PATH = "https://S3mockUrl"

# Image save path
IMAGE_SAVE_PATH = "RecievedPictures"