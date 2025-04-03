import tensorflow as tf
import cv2
import numpy as np
from pathlib import Path
import logging

class AIAuthenticator:
    def __init__(self):
        self.model_path = Path("src/models/image_auth_model.h5")
        self.setup_logging()
        self.load_model()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def load_model(self):
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load model: {str(e)}")
            raise

    def analyze_image(self, image_path):
        try:
            # Read and preprocess image
            img = cv2.imread(str(image_path))
            img = cv2.resize(img, (224, 224))
            img = img / 255.0
            img = np.expand_dims(img, axis=0)

            # Get prediction
            prediction = self.model.predict(img)[0][0]
            
            return {
                'is_tampered': bool(prediction > 0.5),
                'confidence': float(prediction),
                'risk_level': 'High' if prediction > 0.7 else 'Medium' if prediction > 0.3 else 'Low'
            }
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            return None