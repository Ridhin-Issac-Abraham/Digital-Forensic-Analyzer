# src/analyzers/deepfake_detector.py
import logging
from src.analyzers.calibrated_vit_detector import CalibratedVITDeepfakeDetector

class DeepfakeDetector:
    def __init__(self, model_path='src/models/vit/deepfake_vit_model'):
        self.logger = logging.getLogger(__name__)
        # Use the calibrated detector with optimal threshold
        self.detector = CalibratedVITDeepfakeDetector(model_path=model_path, threshold=0.95)
        
    def detect_deepfake(self, image_path):
        """Detect if the image contains deepfakes"""
        self.logger.info(f"Analyzing image for deepfakes: {image_path}")
        return self.detector.detect_deepfake(image_path)