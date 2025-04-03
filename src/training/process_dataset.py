import cv2
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
import logging
from tqdm import tqdm
import shutil

class DatasetProcessor:
    def __init__(self):
        self.base_dir = Path("src/data")
        self.download_dir = self.base_dir / "downloads" / "CASIA2"
        self.processed_dir = self.base_dir / "processed"
        self.setup_logging()

    def setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dataset_processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def cleanup_downloads(self):
        """Clean up redundant dataset folders"""
        try:
            redundant_paths = [
                self.base_dir / "downloads" / "casia",
                self.base_dir / "downloads" / "CASIA1"
            ]
            
            for path in redundant_paths:
                if path.exists():
                    self.logger.info(f"Removing redundant folder: {path}")
                    shutil.rmtree(path)
            
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def process_images(self):
        """Process and organize downloaded images"""
        try:
            # Ensure directories exist
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            (self.processed_dir / "authentic").mkdir(exist_ok=True)
            (self.processed_dir / "tampered").mkdir(exist_ok=True)

            # Get image paths
            authentic_images = list((self.download_dir / "Au").glob("*.jpg"))
            tampered_images = list((self.download_dir / "Tp").glob("*.jpg"))

            self.logger.info(f"Found {len(authentic_images)} authentic and {len(tampered_images)} tampered images")

            # Process authentic images
            self.logger.info("Processing authentic images...")
            for img_path in tqdm(authentic_images):
                self._process_single_image(img_path, "authentic")

            # Process tampered images
            self.logger.info("Processing tampered images...")
            for img_path in tqdm(tampered_images):
                self._process_single_image(img_path, "tampered")

            self.logger.info("Dataset processing completed!")
            return True

        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            return False

    def _process_single_image(self, img_path, category):
        """Process a single image"""
        try:
            # Read and resize image
            img = cv2.imread(str(img_path))
            if img is not None:
                img = cv2.resize(img, (224, 224))  # Standard size for many CNN models
                
                # Save processed image
                output_path = self.processed_dir / category / img_path.name
                cv2.imwrite(str(output_path), img)
            else:
                self.logger.warning(f"Could not read image: {img_path}")

        except Exception as e:
            self.logger.error(f"Error processing {img_path}: {str(e)}")

if __name__ == "__main__":
    processor = DatasetProcessor()
    processor.cleanup_downloads()
    processor.process_images()