# src/analyzers/advanced_deepfake_detector.py
import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import logging
from pathlib import Path

class AdvancedDeepfakeDetector:
    def __init__(self, model_path='src/models/cslbp/deepfake_model_final.keras'):
        self.logger = logging.getLogger(__name__)
        self.model = self._load_model(model_path)
        self.img_size = (224, 224)
        
        # Load face detector
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
    def _load_model(self, model_path):
        """Load the deepfake detection model"""
        try:
            if os.path.exists(model_path):
                self.logger.info(f"Loading deepfake detection model from {model_path}")
                return load_model(model_path, compile=False)
            else:
                self.logger.warning(f"Model not found at {model_path}. Path: {os.path.abspath(model_path)}")
                return None
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return None
    
    def _get_pixel(self, img, x1, y1, x, y):
        """Helper for CS-LBP calculation"""
        new_value = 0
        try:
            if img[x1][y1] >= img[x][y]:
                new_value = 1
        except IndexError:
            pass
        return new_value
    
    def _cs_lbp_calculated_pixel(self, img, x, y):
        """Calculate CS-LBP value for a pixel"""
        val_ar = []
        
        val_ar.append(self._get_pixel(img, x, y+1, x, y-1))
        val_ar.append(self._get_pixel(img, x+1, y+1, x-1, y - 1))
        val_ar.append(self._get_pixel(img, x+1, y, x-1, y))
        val_ar.append(self._get_pixel(img, x+1, y-1, x - 1, y + 1))
    
        power_val = [1, 2, 4, 8]
        val = 0
        for i in range(len(val_ar)):
            val += val_ar[i] * power_val[i]
        return val
    
    def _apply_cs_lbp_clahe(self, image, clip_limit=2.0, grid_size=(8, 8)):
        """Apply CS-LBP and CLAHE to the image"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = image
            
        # Apply CLAHE
        img_clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size).apply(img_gray)
        
        height, width = img_clahe.shape
        img_cs_lbp = np.zeros((height, width), np.uint8)
    
        # Calculate CS-LBP for each pixel
        for i in range(1, height-1):  # Avoid border pixels
            for j in range(1, width-1):  # Avoid border pixels
                img_cs_lbp[i, j] = self._cs_lbp_calculated_pixel(img_clahe, i, j)
    
        # Convert to 3-channel image for model input
        img_rgb = cv2.cvtColor(img_cs_lbp, cv2.COLOR_GRAY2RGB)
        return img_rgb
            
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
    
    def detect_deepfake(self, image_path):
        """Detect if the image contains deepfake faces"""
        try:
            self.logger.info(f"Analyzing image for deepfakes: {image_path}")
            
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
                self.logger.warning(f"No faces detected in {image_path}")
                return {
                    'is_deepfake': False,
                    'confidence': 0,
                    'message': 'No faces detected in the image',
                    'faces_detected': 0
                }
            
            # Apply CS-LBP and CLAHE
            processed_face = self._apply_cs_lbp_clahe(face_img)
            
            # Save preprocessed face for debugging
            debug_path = f"{image_path}_preprocessed.jpg"
            cv2.imwrite(debug_path, processed_face)
            
            # Resize for model input
            processed_face = cv2.resize(processed_face, self.img_size)
            
            # Normalize
            processed_face = processed_face.astype(np.float32) / 255.0
            
            # Add batch dimension
            processed_face = np.expand_dims(processed_face, axis=0)
            
            # Predict
            if self.model:
                prediction = self.model.predict(processed_face, verbose=0)[0][0]
                # Note: In our model, value closer to 1 means real, closer to 0 means fake
                is_fake = prediction < 0.5
                confidence = float(1.0 - prediction if is_fake else prediction)
                self.logger.info(f"Prediction: {prediction}, Is fake: {is_fake}, Confidence: {confidence:.2f}")
            else:
                self.logger.error("No model available for prediction")
                is_fake = False
                confidence = 0.5
            
            # Draw on visualization image
            if face_coords:
                x1, y1, x2, y2 = face_coords
                color = (0, 0, 255) if is_fake else (0, 255, 0)  # Red for fake, green for real
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                
                # Add label
                label = f"FAKE {(1-confidence):.0%}" if is_fake else f"REAL {confidence:.0%}" 
                cv2.putText(vis_img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Save visualization
            vis_path = f"{image_path}_deepfake_analysis.jpg"
            cv2.imwrite(vis_path, vis_img)
            
            result = {
                'is_deepfake': is_fake,
                'confidence': confidence,
                'message': f"{'Deepfake' if is_fake else 'Authentic'} face detected with {confidence:.0%} confidence",
                'faces_detected': 1 if face_coords else 0,
                'face_coords': face_coords,
                'visualization_path': vis_path
            }
            
            self.logger.info(f"Analysis complete: {result['message']}")
            return result
        
        except Exception as e:
            self.logger.error(f"Error in deepfake detection: {e}")
            return {
                'error': str(e),
                'is_deepfake': False,
                'message': f"Detection error: {str(e)}"
            }