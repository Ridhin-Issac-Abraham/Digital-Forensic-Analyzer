import os
import kaggle
from pathlib import Path
import logging
from tqdm import tqdm
import shutil

class DatasetDownloader:
    def __init__(self):
        self.base_dir = Path("src/data")
        self.download_dir = self.base_dir / "downloads"
        self.processed_dir = self.base_dir / "processed"
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dataset_download.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_directories(self):
        """Create necessary directories"""
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        (self.processed_dir / "authentic").mkdir(exist_ok=True)
        (self.processed_dir / "tampered").mkdir(exist_ok=True)

    def download_casia_dataset(self):
        """Download CASIA v2.0 dataset from Kaggle"""
        try:
            self.logger.info("Starting CASIA dataset download...")
            kaggle.api.dataset_download_files(
                "sophatvathana/casia-dataset",
                path=self.download_dir,
                unzip=True
            )
            self.logger.info(f"Dataset downloaded to {self.download_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            return False

if __name__ == "__main__":
    downloader = DatasetDownloader()
    downloader.setup_directories()
    if downloader.download_casia_dataset():
        print("Dataset downloaded successfully!")