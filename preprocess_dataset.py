# preprocess_dataset.py
import os
import cv2
import numpy as np
from pathlib import Path
import argparse
from tqdm import tqdm
import shutil

# Parse command line arguments
parser = argparse.ArgumentParser(description='Preprocess images for deepfake detection')
parser.add_argument('--dataset', type=str, default='F:/MSCAIML/S6/digital_forensics/src/datasets/deepfake/dataset',
                    help='Path to the dataset directory')
parser.add_argument('--output', type=str, default='src/processed_dataset',
                    help='Output directory for preprocessed images')
args = parser.parse_args()

# Create output directories
os.makedirs(os.path.join(args.output, 'train', 'real'), exist_ok=True)
os.makedirs(os.path.join(args.output, 'train', 'fake'), exist_ok=True)
os.makedirs(os.path.join(args.output, 'test', 'real'), exist_ok=True)
os.makedirs(os.path.join(args.output, 'test', 'fake'), exist_ok=True)

# Load the cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
print("Loaded OpenCV face detector")

# CS-LBP Calculation Functions
def get_pixel(img, x1, y1, x, y):
    """Get pixel comparison result for CS-LBP"""
    new_value = 0
    try:
        if img[x1][y1] >= img[x][y]:
            new_value = 1
    except IndexError:
        pass
    return new_value

def cs_lbp_calculated_pixel(img, x, y):
    """Calculate CS-LBP value for a pixel"""
    val_ar = []
    
    val_ar.append(get_pixel(img, x, y+1, x, y-1))
    val_ar.append(get_pixel(img, x+1, y+1, x-1, y - 1))
    val_ar.append(get_pixel(img, x+1, y, x-1, y))
    val_ar.append(get_pixel(img, x+1, y-1, x - 1, y + 1))

    power_val = [1, 2, 4, 8]
    val = 0
    for i in range(len(val_ar)):
        val += val_ar[i] * power_val[i]
    return val

def apply_cs_lbp_clahe(image, clip_limit=2.0, grid_size=(8, 8)):
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
            img_cs_lbp[i, j] = cs_lbp_calculated_pixel(img_clahe, i, j)

    # Convert to 3-channel image for visualization and model input
    img_rgb = cv2.cvtColor(img_cs_lbp, cv2.COLOR_GRAY2RGB)
    return img_rgb

def extract_face(image_path, size=(224, 224)):
    """Extract face ROI from image using OpenCV's Haar Cascade"""
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Warning: Could not read image {image_path}")
        return None
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
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
        x2 = min(img.shape[1], x + w + margin_x)
        y2 = min(img.shape[0], y + h + margin_y)
        
        # Crop face region
        roi = img[y1:y2, x1:x2]
        
        # Apply CS-LBP and CLAHE
        processed = apply_cs_lbp_clahe(roi)
        
        # Resize to the target size
        processed = cv2.resize(processed, size)
        
        return processed
    else:
        print(f"Warning: No face detected in {image_path}")
        return None

def process_directory(input_dir, output_dir, label):
    """Process all images in a directory"""
    print(f"Processing {label} images in {input_dir}...")
    
    if not os.path.exists(input_dir):
        print(f"Warning: Directory {input_dir} does not exist")
        return 0
        
    images = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    processed_count = 0
    for img_file in tqdm(images):
        img_path = os.path.join(input_dir, img_file)
        processed = extract_face(img_path)
        if processed is not None:
            output_file = os.path.join(output_dir, img_file)
            cv2.imwrite(output_file, processed)
            processed_count += 1
            
    return processed_count

def process_dataset(dataset_path, output_path):
    """Process the entire dataset with train/test/validation structure"""
    # Define directories - using correct case as in your structure
    train_path = os.path.join(dataset_path, 'train')
    test_path = os.path.join(dataset_path, 'test')
    validation_path = os.path.join(dataset_path, 'validation')
    
    # Process training data with correct case
    train_real_count = process_directory(
        os.path.join(train_path, 'Real'),
        os.path.join(output_path, 'train', 'real'),
        'training real'
    )
    
    train_fake_count = process_directory(
        os.path.join(train_path, 'Fake'),
        os.path.join(output_path, 'train', 'fake'),
        'training fake'
    )
    
    # Process testing data with correct case
    test_real_count = process_directory(
        os.path.join(test_path, 'Real'),
        os.path.join(output_path, 'test', 'real'),
        'testing real'
    )
    
    test_fake_count = process_directory(
        os.path.join(test_path, 'Fake'),
        os.path.join(output_path, 'test', 'fake'),
        'testing fake'
    )
        
    # Process validation data with correct case
    validation_real_count = process_directory(
        os.path.join(validation_path, 'Real'),
        os.path.join(output_path, 'test', 'real'),  # Adding to test folder
        'validation real'
    )
    
    validation_fake_count = process_directory(
        os.path.join(validation_path, 'Fake'),
        os.path.join(output_path, 'test', 'fake'),  # Adding to test folder
        'validation fake'
    )
    
    print("\nPreprocessing complete!")
    print(f"Training set: {train_real_count} real, {train_fake_count} fake images")
    print(f"Testing set: {test_real_count + validation_real_count} real, {test_fake_count + validation_fake_count} fake images")
    print(f"(Testing set includes {validation_real_count} real and {validation_fake_count} fake images from validation)")

if __name__ == "__main__":
    print(f"Processing dataset from {args.dataset}")
    process_dataset(args.dataset, args.output)