import tensorflow as tf
from tensorflow.keras import layers, models
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split
import logging
import cv2
from tqdm import tqdm

class ImageAuthenticationModel:
    def __init__(self):
        self.base_dir = Path("src/data/processed")
        self.model_save_path = Path("src/models")
        self.setup_logging()
        self.setup_model()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_model(self):
        """Create CNN model architecture"""
        self.model = models.Sequential([
            # First Convolutional Block
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            layers.MaxPooling2D((2, 2)),
            layers.BatchNormalization(),
            
            # Second Convolutional Block
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.BatchNormalization(),
            
            # Third Convolutional Block
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.BatchNormalization(),
            
            # Dense Layers
            layers.Flatten(),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
    def load_data(self):
        """Load and preprocess images"""
        X = []  # Images
        y = []  # Labels (0: authentic, 1: tampered)
        
        # Load authentic images
        authentic_paths = list((self.base_dir / "authentic").glob("*.jpg"))
        for img_path in tqdm(authentic_paths, desc="Loading authentic images"):
            img = cv2.imread(str(img_path))
            img = img / 255.0  # Normalize
            X.append(img)
            y.append(0)
            
        # Load tampered images
        tampered_paths = list((self.base_dir / "tampered").glob("*.jpg"))
        for img_path in tqdm(tampered_paths, desc="Loading tampered images"):
            img = cv2.imread(str(img_path))
            img = img / 255.0  # Normalize
            X.append(img)
            y.append(1)
            
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        return X_train, X_test, y_train, y_test
    
    def train_model(self, epochs=10, batch_size=32):
        """Train the model"""
        try:
            self.logger.info("Loading dataset...")
            X_train, X_test, y_train, y_test = self.load_data()
            
            self.logger.info("Starting training...")
            history = self.model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_test, y_test)
            )
            
            # Save the model
            self.model_save_path.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_save_path / 'image_auth_model.h5')
            self.logger.info("Model saved successfully!")
            
            return history
            
        except Exception as e:
            self.logger.error(f"Training failed: {str(e)}")
            return None

if __name__ == "__main__":
    model = ImageAuthenticationModel()
    history = model.train_model()

