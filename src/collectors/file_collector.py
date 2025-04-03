import os
import hashlib
import sqlite3
from datetime import datetime

class LocalFileExtractor:
    def __init__(self, base_path):
        self.base_path = base_path
        self.db_name = "src/database/evidence.db"
        self.conn = sqlite3.connect(self.db_name)
        self.setup_database()

    def setup_database(self):
        """Create table for storing local file metadata."""
        query = """
        CREATE TABLE IF NOT EXISTS file_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            file_path TEXT UNIQUE,
            file_size INTEGER,
            hash_sha256 TEXT UNIQUE,
            last_modified TEXT
        )
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()

    def get_file_hash(self, file_path):
        """Generate SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()

    def collect_files(self, specific_file=None):
        """Collect metadata for files"""
        try:
            cursor = self.conn.cursor()
            
            if specific_file:
                # Only process the specific file
                if os.path.exists(specific_file):
                    self._process_file(specific_file, cursor)
            else:
                # Original directory scanning logic
                for root, _, files in os.walk(self.base_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        self._process_file(file_path, cursor)
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise e

    def _process_file(self, file_path, cursor):
        """Process a single file and store its metadata."""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_hash = self.get_file_hash(file_path)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

        self.store_metadata(file_name, file_path, file_size, file_hash, last_modified, cursor)

    def store_metadata(self, file_name, file_path, file_size, file_hash, last_modified, cursor):
        """Store file metadata in SQLite database."""
        query = """
        INSERT INTO file_metadata (file_name, file_path, file_size, hash_sha256, last_modified)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            cursor.execute(query, (file_name, file_path, file_size, file_hash, last_modified))
            print(f"✅ Stored: {file_name} ({file_size} bytes)")
        except sqlite3.IntegrityError:
            print(f"⚠️ File {file_name} already exists in the database.")

    def close(self):
        """Close database connection."""
        self.conn.close()

# Example usage
if __name__ == "__main__":
    directory_to_scan = "C:\\Users\\ridhi\\Documents\\JustmyForensics"
    extractor = LocalFileExtractor(directory_to_scan)
    extractor.collect_files()
    extractor.close()
