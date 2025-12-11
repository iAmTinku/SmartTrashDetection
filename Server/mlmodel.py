import io
import hashlib
import logging
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

logger = logging.getLogger(__name__)




class ModelPredictor:
    def __init__(self, model_path, img_size, class_names):
        self.model = None
        self.img_size = img_size
        self.class_names = class_names
        self._load_model(model_path)

    def _load_model(self, model_path):
        try:
            # Use compile=False if you only need inference and want faster loading
            self.model = tf.keras.models.load_model(model_path, compile=False) 
            logger.info("✅ Model loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Error loading model from {model_path}: {e}")
            self.model = None

    def predict(self, image_bytes):
        if self.model is None:
            return "MODEL_ERROR", 0.0, None
            
        try:
            # 1. Load, Resize, and Convert to Array (H, W, C)
            img = image.load_img(io.BytesIO(image_bytes), target_size=self.img_size)
            img_array = image.img_to_array(img)

            # 2. Add Batch Dimension: (224, 224, 3) -> (1, 224, 224, 3)
            input_tensor = np.expand_dims(img_array, axis=0)

            # 3. Apply MobileNetV2 Scaling: [0, 255] -> [-1, 1]
            processed_input = preprocess_input(input_tensor)

            # 4. Predict
            # Added verbose=0 to silence prediction output
            raw_prediction = self.model.predict(processed_input, verbose=0) 
            
            # 5. Get results
            probabilities = raw_prediction[0]
            predicted_index = np.argmax(probabilities)
            confidence = np.max(probabilities)
            predicted_class = self.class_names[predicted_index]

            return predicted_class, confidence, probabilities
            
        except Exception as e:
            logger.error(f"Error during model prediction: {e}")
            return "PREDICTION_FAIL", 0.0, None

class ImageMetadataExtractor:
    def get_metadata(self, image_bytes):
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