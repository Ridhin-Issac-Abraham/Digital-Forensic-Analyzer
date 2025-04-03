import math
import os
import magic  # for file type detection
import hashlib
from PIL import Image  # for image handling
from PIL.ExifTags import TAGS
import pytesseract  # for text extraction
from datetime import datetime
import sqlite3
import mimetypes

class FileAnalyzer:
    def __init__(self, db_path="src/database/evidence.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.setup_database()

    def setup_database(self):
        """Create necessary tables for advanced file analysis"""
        cursor = self.conn.cursor()
        
        # Create table for file content analysis
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            file_type TEXT,
            mime_type TEXT,
            content_preview TEXT,
            extracted_text TEXT,
            creation_date TEXT,
            is_encrypted BOOLEAN,
            FOREIGN KEY (file_id) REFERENCES file_metadata (id)
        )""")

        # Create table for image metadata
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            width INTEGER,
            height INTEGER,
            format TEXT,
            mode TEXT,
            exif_data TEXT,
            FOREIGN KEY (file_id) REFERENCES file_metadata (id)
        )""")

        self.conn.commit()

    def analyze_file(self, file_path):
        """Analyze a single file and store its metadata"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Basic file information
        file_type = magic.from_file(file_path)
        mime_type = magic.from_file(file_path, mime=True)
        
        # Get file ID from file_metadata table
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM file_metadata WHERE file_path = ?", (file_path,))
        file_id = cursor.fetchone()[0]

        # Extract content preview and text
        content_preview = self.get_content_preview(file_path, mime_type)
        extracted_text = self.extract_text(file_path, mime_type)
        
        # Check if file is encrypted (basic check)
        is_encrypted = self.check_encryption(file_path)

        # Store basic analysis
        cursor.execute("""
        INSERT INTO file_analysis 
        (file_id, file_type, mime_type, content_preview, extracted_text, creation_date, is_encrypted)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_id, file_type, mime_type, content_preview, extracted_text, 
              datetime.now().isoformat(), is_encrypted))

        # If it's an image, analyze image metadata
        if mime_type.startswith('image/'):
            self.analyze_image(file_id, file_path)

        self.conn.commit()

    def get_content_preview(self, file_path, mime_type, max_size=1024):
        """Get a preview of file content"""
        try:
            if mime_type.startswith('text/'):
                with open(file_path, 'r', errors='ignore') as f:
                    return f.read(max_size)
            return None
        except Exception as e:
            return f"Error getting preview: {str(e)}"

    def extract_text(self, file_path, mime_type):
        """Extract text content from supported file types"""
        try:
            if mime_type.startswith('text/'):
                with open(file_path, 'r', errors='ignore') as f:
                    return f.read()
            elif mime_type.startswith('image/'):
                # Use OCR for images
                return pytesseract.image_to_string(Image.open(file_path))
            return None
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    def check_encryption(self, file_path):
        """Basic check for file encryption"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024)
                entropy = self.calculate_entropy(data)
                return entropy > 7.5  # High entropy might indicate encryption
        except Exception:
            return False

    def calculate_entropy(self, data):
        """Calculate Shannon entropy of data"""
        if not data:
            return 0
        entropy = 0
        for x in range(256):
            p_x = data.count(x) / len(data)
            if p_x > 0:
                entropy += - p_x * math.log2(p_x)
        return entropy

    def analyze_image(self, file_id, file_path):
        """Analyze image files and extract metadata"""
        try:
            with Image.open(file_path) as img:
                # Basic image info
                width, height = img.size
                format = img.format
                mode = img.mode

                # Extract EXIF data
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    for tag_id in img._getexif():
                        tag = TAGS.get(tag_id, tag_id)
                        data = img._getexif()[tag_id]
                        exif_data[tag] = str(data)

                # Store image metadata
                cursor = self.conn.cursor()
                cursor.execute("""
                INSERT INTO image_metadata 
                (file_id, width, height, format, mode, exif_data)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (file_id, width, height, format, mode, str(exif_data)))
                
                self.conn.commit()
        except Exception as e:
            print(f"Error analyzing image {file_path}: {str(e)}")

    def search_files(self, keyword):
        """Search through analyzed files"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT fm.file_name, fa.file_type, fa.extracted_text
        FROM file_metadata fm
        JOIN file_analysis fa ON fm.id = fa.file_id
        WHERE fa.extracted_text LIKE ? OR fm.file_name LIKE ?
        """, (f'%{keyword}%', f'%{keyword}%'))
        return cursor.fetchall()

    def close(self):
        """Close database connection"""
        self.conn.close()