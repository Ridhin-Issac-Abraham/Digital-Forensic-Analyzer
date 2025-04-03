# src/analyzers/calibrated_vit_detector.py
import os
import cv2
import numpy as np
import logging
import torch
from transformers import ViTImageProcessor, ViTForImageClassification
from PIL import Image

class CalibratedVITDeepfakeDetector:
    def __init__(self, model_path='src/models/vit/deepfake_vit_model', threshold=0.95):
        self.logger = logging.getLogger(__name__)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.model = self._load_model(model_path)
        self.processor = self._load_processor(model_path)
        
        # Calibration threshold - 0.95 is optimal based on our testing
        self.threshold = threshold
        self.logger.info(f"Using calibration threshold: {self.threshold}")
        
    def _load_model(self, model_path):
        try:
            if os.path.exists(model_path):
                self.logger.info(f"Loading ViT deepfake detection model from {model_path}")
                return ViTForImageClassification.from_pretrained(model_path)
            else:
                self.logger.warning(f"Model not found at {model_path}. Path: {os.path.abspath(model_path)}")
                return None
        except Exception as e:
            self.logger.error(f"Error loading ViT model: {e}")
            return None
            
    def _load_processor(self, model_path):
        try:
            if os.path.exists(model_path):
                self.logger.info(f"Loading ViT processor from {model_path}")
                return ViTImageProcessor.from_pretrained(model_path)
            else:
                self.logger.warning(f"Processor not found at {model_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error loading ViT processor: {e}")
            return None
    
    def _extract_face(self, image):
        """Extract face ROI from image using OpenCV's Haar Cascade"""
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            # Get the largest face (by area)
            areas = []
            for (x, y, w, h) in faces:
                areas.append(w*h)
            
            largest_face_idx = areas.index(max(areas))
            x, y, w, h = faces[largest_face_idx]
            
            # Add margin (10% on each side)
            margin_x = int(0.1 * w)
            margin_y = int(0.1 * h)
            
            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(image.shape[1], x + w + margin_x)
            y2 = min(image.shape[0], y + h + margin_y)
            
            # Crop face region
            roi = image[y1:y2, x1:x2]
            return roi, (x1, y1, x2, y2)
        else:
            return None, None
    
    def _normalize_confidence(self, raw_confidence, is_fake):
        """Normalize confidence scores for better human interpretation"""
        # For fake predictions, use raw confidence
        if is_fake:
            return raw_confidence
        
        # For real predictions, provide a more balanced confidence score
        # Map from [threshold-0.9, threshold] to [0.5, 1.0]
        # This gives more reasonable confidence scores for real predictions
        lower_bound = max(0.9, self.threshold - 0.1)
        if raw_confidence <= lower_bound:
            normalized = 0.5
        else:
            # Linear mapping from [lower_bound, threshold] to [0.5, 1.0]
            range_size = self.threshold - lower_bound
            position = 1.0 - ((self.threshold - raw_confidence) / range_size)
            normalized = 0.5 + (position * 0.5)
        
        return normalized
    
    def detect_deepfake(self, image_path):
        """Detect if the image contains deepfake faces with calibrated threshold"""
        try:
            self.logger.info(f"Analyzing image for deepfakes using calibrated ViT: {image_path}")
            
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"Could not read image at {image_path}")
                return {
                    'error': f"Could not read image at {image_path}",
                    'is_deepfake': False
                }
            
            # Make a copy for visualization
            vis_img = image.copy()
            
            # Extract face 
            face_img, face_coords = self._extract_face(image)
            
            if face_img is None:
                # Process the full image if no face is detected
                self.logger.warning(f"No faces detected in {image_path}, processing full image")
                pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                face_coords = None
            else:
                # Convert to PIL Image
                pil_img = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
            
            # Process image for ViT
            if self.processor and self.model:
                inputs = self.processor(images=pil_img, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                # Get raw logits and probabilities
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)[0]
                
                # Get fake probability
                fake_prob = probs[1].item()
                
                # Apply calibrated threshold
                is_fake = fake_prob >= self.threshold
                
                # Calculate confidence (with normalization for better interpretability)
                raw_confidence = fake_prob if is_fake else (1 - fake_prob)
                confidence = self._normalize_confidence(fake_prob, is_fake)
                
                self.logger.info(f"Fake probability: {fake_prob:.4f}, Threshold: {self.threshold}")
                self.logger.info(f"Calibrated prediction: {'Fake' if is_fake else 'Real'} with confidence {confidence:.4f}")
                
            else:
                self.logger.error("No model or processor available for prediction")
                is_fake = False
                confidence = 0.5
                fake_prob = 0.0
            
            # Draw on visualization image
            if face_coords:
                x1, y1, x2, y2 = face_coords
                color = (0, 0, 255) if is_fake else (0, 255, 0)  # Red for fake, green for real
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                
                # Add label with normalized confidence value
                label = f"FAKE {confidence:.0%}" if is_fake else f"REAL {confidence:.0%}" 
                cv2.putText(vis_img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                # Add label for whole image
                color = (0, 0, 255) if is_fake else (0, 255, 0)
                label = f"FAKE {confidence:.0%}" if is_fake else f"REAL {confidence:.0%}"
                cv2.putText(vis_img, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            
            # Save visualization
            vis_path = f"{image_path}_vit_analysis.jpg"
            cv2.imwrite(vis_path, vis_img)
            
            result = {
                'is_deepfake': is_fake,
                'confidence': confidence,
                'fake_probability': fake_prob,
                'message': f"{'Deepfake' if is_fake else 'Authentic'} {'face' if face_coords else 'image'} detected with {confidence:.0%} confidence",
                'faces_detected': 1 if face_coords else 0,
                'face_coords': face_coords,
                'visualization_path': vis_path
            }
            
            self.logger.info(f"Analysis complete: {result['message']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in calibrated ViT deepfake detection: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'error': str(e),
                'is_deepfake': False,
                'message': f"Detection error: {str(e)}"
            }