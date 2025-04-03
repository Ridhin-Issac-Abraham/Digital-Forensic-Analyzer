import sqlite3
import hashlib
from datetime import datetime
import logging
import os
from contextlib import contextmanager

class CustodyManager:
    def __init__(self, db_path="src/database/evidence.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, timeout=30)  # Added timeout
        self.setup_logging()
        self.setup_database()
        
    def setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='custody_manager.log'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Initialize the custody_chain table if it doesn't exist"""
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

    def log_action(self, evidence_id, evidence_type, action_type, handler, location, file_path=None, notes=None):
        """Log an action in the chain of custody"""
        try:
            timestamp = datetime.now().isoformat()
            hash_before = self.get_latest_hash(evidence_id)  # Get previous hash
            hash_after = None

            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    hash_after = hashlib.sha256(f.read()).hexdigest()

            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO custody_chain (
                    evidence_id, evidence_type, action_type, action_timestamp,
                    handler, location, hash_before, hash_after, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(evidence_id), evidence_type, action_type, timestamp,
                handler, location, hash_before, hash_after, notes
            ))
            
            self.conn.commit()
            self.logger.info(f"Custody action logged for evidence {evidence_id}: {action_type}")
            return cursor.lastrowid
            
        except Exception as e:
            self.logger.error(f"Error logging custody action: {str(e)}")
            raise

    def get_custody_chain(self, evidence_id):
        """Get all custody records for an evidence item"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    action_type,
                    action_timestamp,
                    handler,
                    location,
                    notes,
                    hash_before,
                    hash_after
                FROM custody_chain 
                WHERE evidence_id = ?
                ORDER BY action_timestamp DESC
            """, (int(evidence_id),))
            
            records = cursor.fetchall()
            self.logger.info(f"Retrieved {len(records)} custody records for evidence {evidence_id}")
            return records
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error in get_custody_chain: {e}")
            raise

    def get_latest_hash(self, evidence_id):
        """Get the most recent hash for an evidence item"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT hash_after 
            FROM custody_chain 
            WHERE evidence_id = ? 
            ORDER BY action_timestamp DESC 
            LIMIT 1
        """, (evidence_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def verify_integrity(self, evidence_id, file_path):
        """Verify file integrity by comparing current hash with last recorded hash"""
        current_hash = None
        if file_path:
            with open(file_path, 'rb') as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
        
        last_hash = self.get_latest_hash(evidence_id)
        return current_hash == last_hash if last_hash else False

    def close(self):
        if self.conn:
            self.conn.close()