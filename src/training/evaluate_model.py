import tensorflow as tf
import numpy as np
from pathlib import Path
import cv2
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import logging

class ModelEvaluator:
    def __init__(self):
        self.model_path = Path("src/models/image_auth_model.h5")
        self.processed_dir = Path("src/data/processed")
        self.results_dir = Path("src/results")
        self.setup_logging()
        self.load_model()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_model(self):
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load model: {str(e)}")
            raise

    def load_test_data(self, test_size=100):
        """Load a subset of images for testing"""
        X_test = []
        y_true = []
        
        # Load authentic images
        authentic_paths = list((self.processed_dir / "authentic").glob("*.jpg"))[:test_size]
        for img_path in authentic_paths:
            img = cv2.imread(str(img_path))
            img = img / 255.0
            X_test.append(img)
            y_true.append(0)
        
        # Load tampered images
        tampered_paths = list((self.processed_dir / "tampered").glob("*.jpg"))[:test_size]
        for img_path in tampered_paths:
            img = cv2.imread(str(img_path))
            img = img / 255.0
            X_test.append(img)
            y_true.append(1)
        
        return np.array(X_test), np.array(y_true)

    def evaluate_model(self):
        """Perform model evaluation"""
        try:
            # Load test data
            X_test, y_true = self.load_test_data()
            
            # Get predictions
            y_pred = self.model.predict(X_test)
            y_pred_classes = (y_pred > 0.5).astype(int)
            
            # Calculate metrics
            conf_matrix = confusion_matrix(y_true, y_pred_classes)
            class_report = classification_report(y_true, y_pred_classes)
            
            # Create visualizations
            self.plot_confusion_matrix(conf_matrix)
            self.plot_roc_curve(y_true, y_pred)
            
            # Save results
            self.save_results(class_report)
            
            return conf_matrix, class_report
            
        except Exception as e:
            self.logger.error(f"Evaluation failed: {str(e)}")
            return None, None

    def plot_confusion_matrix(self, conf_matrix):
        """Plot and save confusion matrix"""
        plt.figure(figsize=(8, 6))
        sns.heatmap(conf_matrix, annot=True, fmt='d', 
                    xticklabels=['Authentic', 'Tampered'],
                    yticklabels=['Authentic', 'Tampered'])
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        
        # Save plot
        self.results_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(self.results_dir / 'confusion_matrix.png')
        plt.close()

    def plot_roc_curve(self, y_true, y_pred):
        """Plot and save ROC curve"""
        from sklearn.metrics import roc_curve, auc
        fpr, tpr, _ = roc_curve(y_true, y_pred)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, 
                label=f'ROC curve (AUC = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver Operating Characteristic')
        plt.legend(loc="lower right")
        
        # Save plot
        plt.savefig(self.results_dir / 'roc_curve.png')
        plt.close()

    def save_results(self, class_report):
        """Save evaluation results"""
        with open(self.results_dir / 'evaluation_report.txt', 'w') as f:
            f.write(class_report)

if __name__ == "__main__":
    evaluator = ModelEvaluator()
    conf_matrix, class_report = evaluator.evaluate_model()
    print("\nClassification Report:")
    print(class_report)