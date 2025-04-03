# test_calibrated_detector.py
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

from src.analyzers.calibrated_vit_detector import CalibratedVITDeepfakeDetector

# Test images - use actual paths from your dataset
test_images = [
    "F:/MSCAIML/S6/digital_forensics/src/datasets/deepfake/dataset/test/Real/real_1.jpg",   # Real example
    "F:/MSCAIML/S6/digital_forensics/src/datasets/deepfake/dataset/test/Fake/fake_1.jpg"    # Fake example
]

# Try different thresholds
thresholds = [0.5, 0.7, 0.85, 0.9, 0.95]

for threshold in thresholds:
    print(f"\n\n==== TESTING WITH THRESHOLD {threshold} ====")
    # Initialize detector with this threshold
    detector = CalibratedVITDeepfakeDetector(threshold=threshold)
    
    # Test each image
    for img_path in test_images:
        print(f"\nAnalyzing: {img_path}")
        result = detector.detect_deepfake(img_path)
        print(f"Result: {'FAKE' if result.get('is_deepfake') else 'REAL'}")
        print(f"Fake probability: {result.get('fake_probability', 0):.4f}")
        print(f"Real probability: {result.get('real_probability', 0):.4f}")

print("\nTesting complete!")