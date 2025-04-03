import os
import sys
from dotenv import load_dotenv
from src.collectors.email_collector import EmailMetadataExtractor
from src.collectors.file_collector import LocalFileExtractor
from src.dashboard.dashboard import ForensicsDashboard
# Add this import at the top
from src.analyzers.enhanced_analyzer import EnhancedFileAnalyzer
from src.analyzers.file_analyzer import FileAnalyzer
import tkinter as tk

load_dotenv()

def setup_database_directory():
    """Ensure database directory exists"""
    os.makedirs('src/database', exist_ok=True)

def collect_evidence(email_settings, directory_to_scan):
    """Collect evidence from both email and local files"""
    # Email collection
    email_extractor = EmailMetadataExtractor(
        email_settings['server'],
        email_settings['user'],
        email_settings['password']
    )
    email_extractor.fetch_emails(limit=10)
   
    # Local file collection
    file_extractor = LocalFileExtractor(directory_to_scan)
    file_extractor.collect_files()
    file_extractor.close()
   
    # Use enhanced analyzer instead of the old FileAnalyzer
    analyzer = EnhancedFileAnalyzer()
    cursor = analyzer.conn.cursor()
    cursor.execute("SELECT file_path FROM file_metadata")
   
    print("\n🔍 Starting enhanced file analysis...")
    for (file_path,) in cursor.fetchall():
        try:
            analyzer.analyze_file(file_path)
            print(f"✅ Enhanced analysis completed: {file_path}")
        except Exception as e:
            print(f"❌ Error during enhanced analysis of {file_path}: {str(e)}")
   
    analyzer.close()
def main():
    # Setup directories
    setup_database_directory()
    
    # Email settings (replace with your details)
    email_settings = {
        'server': os.getenv('EMAIL_SERVER'),
        'user': os.getenv('EMAIL_USER'),
        'password': os.getenv('EMAIL_PASSWORD')
    }
    
    # Directory to scan (replace with your directory)
    directory_to_scan = os.getenv('EVIDENCE_DIR')
    
    # Create evidence directory if it doesn't exist
    os.makedirs(directory_to_scan, exist_ok=True)
    
    # Collect evidence
    try:
        collect_evidence(email_settings, directory_to_scan)
        print("Evidence collection completed successfully!")
    except Exception as e:
        print(f"Error during evidence collection: {str(e)}")
        return
    
    # Launch dashboard
    root = tk.Tk()
    app = ForensicsDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()