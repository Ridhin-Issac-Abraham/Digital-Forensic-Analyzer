import imaplib
import email
import sqlite3
import os
import logging
from email.header import decode_header
from datetime import datetime
from contextlib import contextmanager

# Database setup
DB_NAME = "src/database/emails.db"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailMetadataExtractor:
    def __init__(self, imap_server, email_user, email_pass, folder="INBOX"):
        self.imap_server = imap_server
        self.email_user = email_user
        self.email_pass = email_pass
        self.folder = folder
        self.mail = None
        self.conn = None
        self.setup_connections()

    def setup_connections(self):
        """Initialize IMAP and database connections"""
        try:
            # Setup IMAP
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_user, self.email_pass)
            self.mail.select(self.folder)
            logger.info("Successfully connected to IMAP server")
            
            # Setup Database
            self.conn = sqlite3.connect(DB_NAME)
            self.migrate_database()
            logger.info("Successfully connected to database")
        except Exception as e:
            self.cleanup()
            raise Exception(f"Connection setup failed: {str(e)}")

    def migrate_database(self):
        """Handle database creation and migrations."""
        cursor = self.conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='email_metadata'
        """)
        
        if not cursor.fetchone():
            # Create new table
            cursor.execute("""
            CREATE TABLE email_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                recipient TEXT,
                subject TEXT,
                date TEXT,
                message_id TEXT UNIQUE,
                headers TEXT,
                has_attachments INTEGER,
                spf_pass INTEGER,
                dkim_pass INTEGER,
                dmarc_pass INTEGER,
                fetch_timestamp TEXT
            )
            """)
            self.conn.commit()
            logger.info("Created email_metadata table")
            return

        # Check for fetch_timestamp column
        cursor.execute('PRAGMA table_info(email_metadata)')
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'fetch_timestamp' not in columns:
            cursor.execute("""
                ALTER TABLE email_metadata
                ADD COLUMN fetch_timestamp TEXT
            """)
            self.conn.commit()
            logger.info("Added fetch_timestamp column")

    def cleanup(self):
        """Clean up connections safely"""
        if hasattr(self, 'mail') and self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
            finally:
                self.mail = None

        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except:
                pass
            finally:
                self.conn = None

    def extract_email_metadata(self, msg):
        """Extract email metadata including headers, attachments, and security indicators."""
        try:
            # Basic metadata
            sender = msg.get("From", "")
            recipient = msg.get("To", "")
            
            # Handle subject decoding
            subject_header = msg.get("Subject", "")
            if subject_header:
                subject, encoding = decode_header(subject_header)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors='replace')
            else:
                subject = ""
                
            date = msg.get("Date", "")
            message_id = msg.get("Message-ID", "").strip('<>')
            headers = str(msg)

            # Check for attachments
            has_attachments = int(any(
                part.get_content_disposition() == "attachment" 
                for part in msg.walk()
            ))

            # Security checks
            spf_pass, dkim_pass, dmarc_pass = self.analyze_security(headers)

            return (
                sender, recipient, subject, date, message_id, 
                headers, has_attachments, spf_pass, dkim_pass, dmarc_pass
            )
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            raise

    def analyze_security(self, headers):
        """Enhanced security header analysis."""
        headers_lower = headers.lower()
        
        # SPF Check
        spf_pass = int(
            any(indicator in headers_lower 
                for indicator in ["spf=pass", "spf=softpass"])
        )
        
        # DKIM Check
        dkim_pass = int("dkim=pass" in headers_lower)
        
        # DMARC Check
        dmarc_pass = int("dmarc=pass" in headers_lower)
        
        return spf_pass, dkim_pass, dmarc_pass

    def store_email_metadata(self, metadata):
        """Store extracted metadata in SQLite database."""
        query = """
        INSERT INTO email_metadata (
            sender, recipient, subject, date, message_id, headers,
            has_attachments, spf_pass, dkim_pass, dmarc_pass, fetch_timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            current_time = datetime.now().isoformat()
            values = metadata + (current_time,)
            
            with self.conn:
                self.conn.execute(query, values)
            logger.info(f"✅ Stored email: {metadata[2][:50]}... from {metadata[0]}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"⚠️ Email {metadata[4]} already exists in database")
            return False
        except Exception as e:
            logger.error(f"Failed to store email: {str(e)}")
            return False

    def fetch_emails(self, limit=10):
        """Fetch and process emails."""
        try:
            if not self.mail:
                self.setup_connections()
                
            # Search for emails
            status, email_ids = self.mail.search(None, "ALL")
            if status != 'OK':
                raise Exception("Failed to search emails")

            email_ids = email_ids[0].split()[-limit:]
            new_emails_count = 0

            for e_id in email_ids:
                try:
                    status, msg_data = self.mail.fetch(e_id, "(RFC822)")
                    if status != 'OK':
                        logger.warning(f"Failed to fetch email ID {e_id}")
                        continue

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            metadata = self.extract_email_metadata(msg)
                            if self.store_email_metadata(metadata):
                                new_emails_count += 1
                except Exception as e:
                    logger.error(f"Error processing email {e_id}: {str(e)}")
                    continue

            return new_emails_count

        except Exception as e:
            logger.error(f"Email fetch failed: {str(e)}")
            raise
        finally:
            self.cleanup()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    IMAP_SERVER = os.getenv('EMAIL_SERVER', 'imap.gmail.com')
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASSWORD')

    if not all([EMAIL_USER, EMAIL_PASS]):
        print("Error: Missing email credentials in environment variables")
        exit(1)

    try:
        extractor = EmailMetadataExtractor(IMAP_SERVER, EMAIL_USER, EMAIL_PASS)
        num_fetched = extractor.fetch_emails(limit=10)
        print(f"Successfully fetched {num_fetched} new emails")
    except Exception as e:
        print(f"Error: {str(e)}")