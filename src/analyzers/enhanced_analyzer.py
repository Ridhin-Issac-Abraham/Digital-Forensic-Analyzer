import os
import hashlib
import magic
import sqlite3
import json
from datetime import datetime
from PIL import Image
import numpy as np
from PIL import ImageChops
import exifread
import PyPDF2
import struct
import logging
from pathlib import Path
from src.chain_of_custody.custody_manager import CustodyManager
from PIL.ExifTags import TAGS


class EnhancedFileAnalyzer:
    def __init__(self, db_path="src/database/evidence.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.setup_logging()  # Call setup_logging before setup_database
        self.logger = logging.getLogger(__name__)
        self.db_initialized = False  # Add flag
        self.setup_database()
        self.magic_instance = magic.Magic(mime=True)

    def setup_logging(self):
        """Setup logging configuration"""
        log_file = 'forensics_analysis.log'
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.info("Enhanced File Analyzer initialized")

    def setup_database(self):
        if not self.db_initialized:  # Check flag
            """Create necessary tables for analysis"""
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                file_type TEXT,
                mime_type TEXT,
                file_size INTEGER,
                created_date TEXT,
                modified_date TEXT,
                accessed_date TEXT,
                is_manipulated BOOLEAN,
                manipulation_confidence FLOAT,
                risk_factors TEXT,           -- New column
                risk_breakdown TEXT,         -- New column
                content_preview TEXT,
                extracted_text TEXT,
                analysis_timestamp TEXT,
                FOREIGN KEY (file_id) REFERENCES file_metadata (id)
            )""")

            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS image_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                exif_data TEXT,
                color_profile TEXT,
                manipulation_indicators TEXT,
                ai_confidence_score FLOAT,
                FOREIGN KEY (file_id) REFERENCES file_metadata (id)
            )""")

            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS custody_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER,
                evidence_type TEXT,
                action_type TEXT,
                action_timestamp TEXT,
                handler TEXT,
                location TEXT,
                hash_before TEXT,
                hash_after TEXT,
                notes TEXT,
                FOREIGN KEY (evidence_id) REFERENCES file_metadata(id)
            )""")

            self.conn.commit()
            logging.info("Database tables created/verified")
            self.db_initialized = True  # Set flag

    def extract_basic_metadata(self, file_path):
        """Extract basic metadata from file"""
        try:
            # Use magic_instance instead of magic.from_file
            mime_type = self.magic_instance.from_file(file_path)
            file_type = mime_type.split('/')[0]
            
            file_size = os.path.getsize(file_path)
            
            metadata = {
                'mime_type': mime_type,
                'file_type': file_type,
                'file_size': file_size
            }
            
            self.logger.info(f"Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting basic metadata from {file_path}: {str(e)}")
            raise

    def analyze_file(self, file_path):
        try:
            self.logger.info(f"Starting analysis of {file_path}")
            metadata = self.extract_basic_metadata(file_path)
            
            # Get file_id
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM file_metadata WHERE file_path = ?", (file_path,))
            file_id = cursor.fetchone()[0]

            # Initialize analysis data
            analysis_data = {
                'file_type': metadata['file_type'],
                'mime_type': metadata['mime_type'],
                'file_size': metadata['file_size'],
                'manipulation_confidence': 0.0
            }

            # Perform type-specific analysis
            if metadata['file_type'] == 'image':
                result = self.analyze_image(file_path, file_id)
                # Extract manipulation_confidence from result dict
                if isinstance(result, dict):
                    analysis_data['manipulation_confidence'] = result.get('manipulation_confidence', 0.0)
                else:
                    analysis_data['manipulation_confidence'] = float(result or 0.0)
            
            # Update database
            cursor.execute("""
                INSERT OR REPLACE INTO file_analysis (
                    file_id, file_type, mime_type, file_size,
                    manipulation_confidence
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                file_id,
                analysis_data['file_type'],
                analysis_data['mime_type'],
                analysis_data['file_size'],
                analysis_data['manipulation_confidence']
            ))
            
            self.conn.commit()
            return analysis_data

        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {str(e)}")
            raise

    def extract_image_metadata(self, file_path):
        """Extract comprehensive image metadata"""
        try:
            with Image.open(file_path) as img:
                # Basic image info
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'is_animated': getattr(img, 'is_animated', False),
                    'frames': getattr(img, 'n_frames', 1),
                    'dpi': img.info.get('dpi', 'N/A'),
                    'compression': img.info.get('compression', 'N/A'),
                    'image_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                    'aspect_ratio': round(img.width / img.height, 2),
                    'color_depth': self.get_color_depth(img.mode),
                    'orientation': img.info.get('orientation', 'Normal')
                }

                # Extract EXIF data
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    for tag_id, value in img._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except:
                                value = str(value)
                        exif_data[tag] = str(value)

                    # Add specific EXIF details
                    if 'DateTimeOriginal' in exif_data:
                        metadata['capture_date'] = exif_data['DateTimeOriginal']
                    if 'Make' in exif_data:
                        metadata['camera_make'] = exif_data['Make']
                    if 'Model' in exif_data:
                        metadata['camera_model'] = exif_data['Model']
                    if 'FocalLength' in exif_data:
                        metadata['focal_length'] = exif_data['FocalLength']
                    if 'ExposureTime' in exif_data:
                        metadata['exposure'] = exif_data['ExposureTime']
                    if 'ISOSpeedRatings' in exif_data:
                        metadata['iso'] = exif_data['ISOSpeedRatings']
                    if 'FNumber' in exif_data:
                        metadata['f_stop'] = exif_data['FNumber']

                metadata['exif_data'] = json.dumps(exif_data)
                self.logger.info(f"Extracted image metadata: {metadata}")
                return metadata

        except Exception as e:
            self.logger.error(f"Error extracting image metadata: {str(e)}")
            return {}

    def get_color_depth(self, mode):
        """Get color depth based on image mode"""
        mode_depths = {
            '1': '1-bit binary',
            'L': '8-bit grayscale',
            'P': '8-bit color',
            'RGB': '24-bit color',
            'RGBA': '32-bit color',
            'CMYK': '32-bit color',
            'YCbCr': '24-bit color',
            'LAB': '24-bit color',
            'HSV': '24-bit color'
        }
        return mode_depths.get(mode, 'Unknown')

    def store_image_metadata(self, file_path, metadata):
        """Store comprehensive image metadata in the database"""
        try:
            cursor = self.conn.cursor()
            
            # Get file_id for the image
            cursor.execute("SELECT id FROM file_metadata WHERE file_path = ?", (file_path,))
            file_id = cursor.fetchone()[0]
            
            # Convert DPI tuple to string if it exists
            dpi_value = str(metadata.get('dpi', 'N/A'))
            if isinstance(metadata.get('dpi'), tuple):
                dpi_value = f"{metadata['dpi'][0]}, {metadata['dpi'][1]}"

            cursor.execute("""
                INSERT OR REPLACE INTO image_metadata (
                    file_id,
                    width,
                    height,
                    format,
                    mode,
                    dpi,
                    compression,
                    image_size_mb,
                    aspect_ratio,
                    color_depth,
                    orientation,
                    is_animated,
                    frames,
                    exif_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                metadata.get('width'),
                metadata.get('height'),
                metadata.get('format'),
                metadata.get('mode'),
                dpi_value,
                metadata.get('compression'),
                metadata.get('image_size_mb'),
                metadata.get('aspect_ratio'),
                metadata.get('color_depth'),
                metadata.get('orientation'),
                metadata.get('is_animated', False),
                metadata.get('frames', 1),
                json.dumps(metadata.get('exif_data', {}))
            ))
            
            self.conn.commit()
            self.logger.info("Image metadata stored successfully")
            
        except Exception as e:
            self.logger.error(f"Error storing image metadata: {str(e)}")
            raise

    def analyze_image(self, file_path, file_id):
        """Analyze image files for manipulation and extract metadata"""
        try:
            with Image.open(file_path) as img:
                # Extract metadata and perform analysis
                metadata = self.extract_image_metadata(file_path)
                ela_score = self.perform_ela(img)
                
                # Calculate risk score
                risk_score = self.calculate_risk_score({
                    'ela_score': float(ela_score),
                    'metadata_missing': len(metadata.get('exif_data', {})) == 0,
                    'metadata_modified': False,  # Set default value
                    'software_edited': False     # Set default value
                })

                # Store results
                self.store_image_metadata(file_path, metadata)
                self.store_image_analysis(file_id, metadata.get('exif_data', {}), ela_score, risk_score)
                
                # Return combined result
                return {
                    'metadata': metadata,
                    'manipulation_confidence': risk_score,
                    'ela_score': ela_score
                }

        except Exception as e:
            self.logger.error(f"Image analysis error for {file_path}: {str(e)}")
            return {'manipulation_confidence': 0.0, 'metadata': {}, 'ela_score': 0.0}

    def calculate_risk_score(self, indicators):
        """Calculate weighted risk score from various indicators"""
        try:
            weights = {
                'ela_score': 0.4,
                'metadata_missing': 0.2,
                'metadata_modified': 0.25,
                'software_edited': 0.15
            }
            
            score = 0.0
            for indicator, weight in weights.items():
                if indicator == 'ela_score':
                    score += float(indicators.get(indicator, 0)) * weight
                else:
                    score += float(indicators.get(indicator, False)) * weight
            
            return min(1.0, max(0.0, score))  # Ensure score is between 0 and 1
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 0.0

    def check_metadata_consistency(self, exif_data):
        """Check for inconsistencies in metadata"""
        if not exif_data:
            return False
            
        suspicious_patterns = [
            # Check for mismatched dates
            self.check_date_consistency(exif_data),
            # Check for missing critical tags
            not all(tag in exif_data for tag in ['Make', 'Model', 'DateTimeOriginal']),
            # Check for software manipulation indicators
            any(tag for tag in exif_data if 'photoshop' in str(tag).lower() or 'adobe' in str(tag).lower())
        ]
        
        return any(suspicious_patterns)

    def check_editing_software(self, exif_data):
        """Check if image has been edited with known software"""
        editing_software_keywords = [
            'photoshop', 'lightroom', 'gimp', 'adobe', 
            'corel', 'paint', 'editor', 'edited'
        ]
        
        if not exif_data:
            return False
            
        software_info = str(exif_data.get('Software', '')).lower()
        processing_info = str(exif_data.get('ProcessingSoftware', '')).lower()
        
        return any(keyword in software_info or processing_info 
                  for keyword in editing_software_keywords)

    def check_date_consistency(self, exif_data):
        """Check for suspicious date patterns in metadata"""
        dates = [
            exif_data.get('DateTimeOriginal', ''),
            exif_data.get('CreateDate', ''),
            exif_data.get('ModifyDate', '')
        ]
        
        # Remove empty dates
        dates = [d for d in dates if d]
        
        if len(dates) < 2:
            return False
            
        # Convert dates to timestamps for comparison
        try:
            timestamps = [datetime.strptime(str(d), '%Y:%m:%d %H:%M:%S') for d in dates]
            time_diffs = [(t2 - t1).total_seconds() for t1, t2 in zip(timestamps, timestamps[1:])]
            
            # Check for suspicious time differences (e.g., future dates, large gaps)
            return any(diff > 86400 or diff < 0 for diff in time_diffs)  # 86400 seconds = 1 day
        except:
            return True  # If date parsing fails, consider it suspicious

    def perform_ela(self, img):
        """Perform Error Level Analysis on image"""
        try:
            # Save image with known quality
            temp_path = "temp_ela.jpg"
            img.save(temp_path, quality=90)
            
            # Load compressed image
            compressed = Image.open(temp_path)
            
            # Calculate difference
            diff = ImageChops.difference(img, compressed)
            
            # Calculate ELA score
            ela_score = np.mean(np.array(diff)) / 255.0
            
            # Cleanup
            os.remove(temp_path)
            
            return ela_score
            
        except Exception as e:
            logging.error(f"ELA analysis error: {str(e)}")
            return 0.0

    def extract_exif(self, file_path):
        """Extract EXIF data from image"""
        exif_data = {}
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
                for tag, value in tags.items():
                    exif_data[tag] = str(value)
                    
            # Add additional metadata checks
            exif_data['analysis_timestamp'] = datetime.now().isoformat()
            
        except Exception as e:
            logging.error(f"EXIF extraction error: {str(e)}")
            
        return exif_data

    def analyze_pdf(self, file_path, file_id):
        """Analyze PDF files for manipulation and metadata"""
        try:
            with open(file_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = pdf.metadata if pdf.metadata else {}
                
                # Calculate risk score based on PDF analysis
                risk_indicators = {
                    'metadata_missing': len(metadata) == 0,
                    'modified_recently': self.check_pdf_modified_recently(metadata),
                    'software_modified': self.check_pdf_software(metadata),
                    'structure_issues': self.check_pdf_structure(pdf)
                }
                
                manipulation_confidence = self.calculate_pdf_risk_score(risk_indicators)

                # Update file analysis with PDF-specific info
                self.conn.execute("""
                    UPDATE file_analysis 
                    SET content_preview = ?,
                        manipulation_confidence = ?
                    WHERE file_id = ?
                """, (str(metadata), manipulation_confidence, file_id))
                self.conn.commit()

                logging.info(f"PDF analysis completed for {file_path}")
                return manipulation_confidence

        except Exception as e:
            logging.error(f"PDF analysis error for {file_path}: {str(e)}")
            return 0.0

    def calculate_pdf_risk_score(self, indicators):
        """Calculate risk score for PDF files"""
        weights = {
            'metadata_missing': 0.3,
            'modified_recently': 0.2,
            'software_modified': 0.25,
            'structure_issues': 0.25
        }
        
        score = 0.0
        for indicator, weight in weights.items():
            score += float(indicators[indicator]) * weight
        
        return min(1.0, score)

    def analyze_text(self, file_path, file_id):
        """Analyze text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                preview = content[:1000] if len(content) > 1000 else content
                
                self.conn.execute("""
                    UPDATE file_analysis 
                    SET content_preview = ?,
                        extracted_text = ?,
                        manipulation_confidence = 0.0
                    WHERE file_id = ?
                """, (preview, content, file_id))
                self.conn.commit()
                
                logging.info(f"Text analysis completed for {file_path}")
                
        except Exception as e:
            logging.error(f"Text analysis error for {file_path}: {str(e)}")

    def store_basic_analysis(self, file_id, metadata):
        """Store basic file analysis results"""
        query = """
        INSERT INTO file_analysis 
        (file_id, file_type, mime_type, file_size, created_date, 
         modified_date, accessed_date, analysis_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.conn.execute(query, (
            file_id,
            metadata['file_type'],
            metadata['mime_type'],
            metadata['file_size'],
            metadata['created_date'],
            metadata['modified_date'],
            metadata['accessed_date'],
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def store_image_analysis(self, file_id, exif_data, ela_score, manipulation_confidence, risk_data=None):
        """Store image analysis results"""
        try:
            if not risk_data:
                risk_data = {
                    'factors': [],
                    'breakdown': {},
                    'score': manipulation_confidence
                }

            self.conn.execute("""
                UPDATE image_metadata 
                SET exif_data = ?,
                    manipulation_indicators = ?,
                    ai_confidence_score = ?
                WHERE file_id = ?
            """, (
                json.dumps(exif_data),
                json.dumps(risk_data['breakdown']),
                manipulation_confidence,
                file_id
            ))
            
            self.conn.commit()
            self.logger.info(f"Analysis results stored for file_id: {file_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing analysis results: {str(e)}")
            raise

    def get_file_id(self, file_path):
        """Get file_id from file_metadata table"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM file_metadata WHERE file_path = ?", 
            (file_path,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def close(self):
        """Close database connection"""
        self.conn.close()
        logging.info("Enhanced File Analyzer closed")