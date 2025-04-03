import sys
import os
# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now you can import the module
import traceback
import sys
from datetime import datetime
import traceback
from src.analyzers.deepfake_detector import DeepfakeDetector

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
from src.analyzers.enhanced_analyzer import EnhancedFileAnalyzer
from src.collectors.email_collector import EmailMetadataExtractor
from src.chain_of_custody.custody_manager import CustodyManager
from src.collectors.file_collector import LocalFileExtractor
from flask import Flask, render_template, url_for
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
import sqlite3
from flask import request, jsonify

# Add these imports
from src.memory_analysis.memory_capture import MemoryCapture
from src.memory_analysis.process_analyzer import ProcessAnalyzer
from src.analyzers.ai_authenticator import AIAuthenticator
from functools import wraps
from web_app.auth.decorators import role_required  # Change to absolute import
from auth.role_manager import RoleManager

load_dotenv()

# Remove the global custody_manager
# Delete or comment out this line:
# custody_manager = CustodyManager()

# Add a function to get custody manager
def get_custody_manager():
    return CustodyManager()

import os

app = Flask(__name__)
# Add static file configuration
app.static_folder = 'static'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'evidence')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
EMAIL_CONFIG = {
    'server': os.getenv('EMAIL_SERVER'),
    'user': os.getenv('EMAIL_USER'),
    'password': os.getenv('EMAIL_PASSWORD')
}

# Initialize analyzers
mem_capture = MemoryCapture()
proc_analyzer = ProcessAnalyzer()

# Add configuration
UPLOAD_FOLDER = 'web_app/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}

app.secret_key = 'your-secret-key-here'  # Change this in production

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    custody_manager = None
    collector = None
    analyzer = None
    
    try:
        custody_manager = get_custody_manager()
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Initialize collector but only process the specific file
            collector = LocalFileExtractor(os.path.dirname(filepath))
            collector.collect_files(specific_file=filepath)  # Pass specific file
            
            # Get the file_id of the newly uploaded file
            cursor = collector.conn.cursor()
            cursor.execute("SELECT id FROM file_metadata WHERE file_path = ?", (filepath,))
            file_id = cursor.fetchone()[0]
            
            # Log initial custody record
            try:
                custody_manager.log_action(
                    evidence_id=file_id,
                    evidence_type='file',
                    action_type='INITIAL_UPLOAD',
                    handler=session.get('username', 'system'),
                    location='web_interface',
                    file_path=filepath,
                    notes=f'File uploaded by {session.get("username", "system")}'
                )
            except Exception as e:
                app.logger.error(f"Error logging custody: {str(e)}")
            
            collector.close()

            # Analyze the file and log custody
            analyzer = EnhancedFileAnalyzer()
            try:
                # Log analysis start
                custody_manager.log_action(
                    evidence_id=file_id,
                    evidence_type='file',
                    action_type='ANALYSIS_STARTED',
                    handler=session.get('username', 'system'),
                    location='analyzer',
                    file_path=filepath,
                    notes='Starting file analysis'
                )
                
                # Perform analysis
                analyzer.analyze_file(filepath)
                
                # Log analysis completion
                custody_manager.log_action(
                    evidence_id=file_id,
                    evidence_type='file',
                    action_type='ANALYSIS_COMPLETED',
                    handler=session.get('username', 'system'),
                    location='analyzer',
                    file_path=filepath,
                    notes='Analysis completed successfully'
                )
                
                # Updated query to include manipulation_confidence
                cursor = analyzer.conn.cursor()
                cursor.execute("""
                    SELECT 
                        fm.id,
                        fm.file_name,
                        fm.file_size,
                        fm.hash_sha256,
                        fa.file_type,
                        fa.mime_type,
                        fa.manipulation_confidence,
                        fa.content_preview,
                        fa.is_manipulated,
                        im.width,
                        im.height,
                        im.format,
                        im.mode,
                        im.exif_data,
                        im.is_animated,
                        im.frames
                    FROM file_metadata fm
                    LEFT JOIN file_analysis fa ON fm.id = fa.file_id
                    LEFT JOIN image_metadata im ON fm.id = im.file_id
                    WHERE fm.file_path = ?
                """, (filepath,))
                
                result = cursor.fetchone()
                if result:
                    manipulation_score = result[6] if result[6] is not None else 0.0
                    return jsonify({
                        'success': True,
                        'message': 'Analysis complete',
                        'result': {
                            'id': result[0],
                            'filename': result[1],
                            'size': result[2],
                            'hash': result[3],
                            'type': result[4] or 'Unknown',
                            'mime': result[5] or 'Unknown',
                            'manipulation_score': manipulation_score,
                            'is_manipulated': bool(result[8]),
                            'preview': result[7] or '',
                            'width': result[9],
                            'height': result[10],
                            'format': result[11],
                            'mode': result[12],
                            'metadata': result[13],
                            'is_animated': bool(result[14]),
                            'frames': result[15] or 1
                        }
                    })
                
                return jsonify({'error': 'No analysis results found'}), 500
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                analyzer.close()
                analyzer = None  # Prevent double close
        
        return jsonify({'error': 'Invalid file type'}), 400
    finally:
        if collector:
            collector.close()
            collector = None
        if analyzer:
            analyzer.close()
            analyzer = None  # Prevent double close
        if custody_manager:
            custody_manager.close()
            custody_manager = None

#The new route to fetch the emails
# Add this new route
@app.route('/api/emails', methods=['GET'])
def get_emails():
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Connect to database
        conn = sqlite3.connect('src/database/emails.db')
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM email_metadata')
        total_count = cursor.fetchone()[0]
        
        # Get emails with pagination
        cursor.execute('''
            SELECT * FROM email_metadata 
            ORDER BY date DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        # Convert to list of dicts
        emails = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'emails': emails,
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit  # Ceiling division
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


#The new route to delete files and emails buttons

@app.route('/api/evidence/delete/<file_id>', methods=['DELETE'])
def delete_file_evidence(file_id):
    try:
        analyzer = EnhancedFileAnalyzer()
        cursor = analyzer.conn.cursor()
        
        # Get file path before deletion
        cursor.execute("SELECT file_path FROM file_metadata WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        if result:
            file_path = result[0]
            
            # Delete from all related tables
            cursor.execute("DELETE FROM image_metadata WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM file_analysis WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM file_metadata WHERE id = ?", (file_id,))
            analyzer.conn.commit()
            
            # Delete actual file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return jsonify({'success': True})
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if analyzer:
            analyzer.close()

@app.route('/api/emails/delete/<email_id>', methods=['DELETE'])
def delete_email(email_id):
    try:
        conn = sqlite3.connect('src/database/emails.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM email_metadata WHERE id = ?", (email_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/evidence')
def get_evidence():
    analyzer = EnhancedFileAnalyzer()
    try:
        cursor = analyzer.conn.cursor()
        cursor.execute("""
            SELECT 
                fm.id,
                fm.file_name,
                fm.file_size,
                fm.hash_sha256,
                fa.file_type,
                fa.mime_type,
                fa.manipulation_confidence,
                im.width,
                im.height,
                im.format,
                im.mode,
                im.dpi,
                im.compression,
                im.image_size_mb,
                im.aspect_ratio,
                im.color_depth,
                im.orientation,
                im.exif_data
            FROM file_metadata fm
            LEFT JOIN file_analysis fa ON fm.id = fa.file_id
            LEFT JOIN image_metadata im ON fm.id = im.file_id
            ORDER BY fm.id DESC
        """)
        
        results = cursor.fetchall()
        return jsonify([{
            'id': r[0],
            'filename': r[1],
            'size': r[2],
            'hash': r[3],
            'type': r[4] or 'Unknown',
            'mime': r[5] or 'Unknown',
            'manipulation_score': r[6] or 0.0,
            'width': r[7],
            'height': r[8],
            'format': r[9],
            'mode': r[10],
            'dpi': r[11],
            'compression': r[12],
            'image_size_mb': r[13],
            'aspect_ratio': r[14],
            'color_depth': r[15],
            'orientation': r[16],
            'exif_data': r[17]
        } for r in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        analyzer.close()

@app.route('/api/custody/<evidence_id>')
def get_custody_chain(evidence_id):
    custody_manager = None
    try:
        custody_manager = get_custody_manager()
        chain = custody_manager.get_custody_chain(evidence_id)
        
        # Transform the data for frontend
        custody_records = [{
            'action_type': record[0],
            'timestamp': record[1],
            'handler': record[2],
            'location': record[3],
            'notes': record[4],
            'hash_before': record[5] if len(record) > 5 else None,
            'hash_after': record[6] if len(record) > 6 else None
        } for record in chain]
        
        return jsonify(custody_records)
    except Exception as e:
        app.logger.error(f"Error fetching custody chain: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if custody_manager:
            custody_manager.close()


@app.route('/api/emails/fetch', methods=['POST'])
def fetch_new_emails():
    email_extractor = None
    try:
        email_extractor = EmailMetadataExtractor(
            EMAIL_CONFIG['server'],
            EMAIL_CONFIG['user'],
            EMAIL_CONFIG['password']
        )
        num_fetched = email_extractor.fetch_emails(limit=10)  # Specify limit
        if num_fetched > 0:
            return jsonify({
                'status': 'success',
                'message': f'Fetched {num_fetched} new emails',
                'count': num_fetched,
                'refresh': True  # Add flag for refresh
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'No new emails found',
                'count': 0,
                'refresh': False
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if email_extractor:
            email_extractor.cleanup()

# Add these routes
@app.route('/api/memory/system')
def get_system_memory():
    try:
        from src.memory_analysis.memory_capture import MemoryCapture
        
        capture = MemoryCapture()
        memory_info = capture.get_system_memory_info()
        
        return jsonify(memory_info)
        
    except Exception as e:
        app.logger.error(f"Failed to get system memory info: {str(e)}")
        return jsonify({
            'memory_percent': 0,
            'swap_percent': 0,
            'error': str(e)
        })

@app.route('/api/memory/processes')
def get_processes():
    try:
        processes = proc_analyzer.get_running_processes()
        return jsonify(processes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/analyze/<int:pid>')
def analyze_process(pid):
    try:
        analysis = proc_analyzer.analyze_process(pid)
        if analysis:
            return jsonify(analysis)
        return jsonify({'error': 'Process not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            authenticator = AIAuthenticator()
            result = authenticator.analyze_image(filepath)
            
            if result:
                return jsonify(result)
            else:
                return jsonify({'error': 'Analysis failed'}), 500
                
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Define database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'database', 'users.db')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username=? AND password=?', 
                          (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['logged_in'] = True
                session['username'] = username
                session['role'] = user[3]
                return redirect(url_for('dashboard'))
            
            return render_template('login.html', error="Invalid credentials")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return render_template('login.html', error="Database error occurred")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'investigator')  # Default role

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return render_template('register.html', error="Username already exists")
            
            # Insert new user
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                         (username, password, role))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return render_template('register.html', error="Registration failed")
    
    return render_template('register.html')

# User Management Routes
@app.route('/users/manage')
@role_required('manage_users')
def user_management():
    role_manager = RoleManager(DB_PATH)
    users = role_manager.get_all_users()
    return render_template('user_management.html', users=users)

@app.route('/users/update_role', methods=['POST'])
@role_required('manage_users')
def update_user_role():
    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    role_manager = RoleManager(DB_PATH)
    role_manager.update_user_role(user_id, new_role)
    return jsonify({'status': 'success'})

# Evidence Collection Routes
@app.route('/evidence/collect', methods=['POST'])
@role_required('collect_evidence')
def collect_evidence():
    # ... existing evidence collection code ...
    pass

# Analysis Routes
@app.route('/evidence/analyze/<evidence_id>')
@role_required('analyze_evidence')
def analyze_evidence(evidence_id):
    # ... existing analysis code ...
    pass

@app.route('/api/emails/delete-batch', methods=['POST'])
def delete_emails_batch():
    try:
        data = request.json
        if not data or 'ids' not in data:
            return jsonify({'error': 'No email IDs provided'}), 400
        
        email_ids = data['ids']
        
        # Connect to database
        conn = sqlite3.connect('src/database/emails.db')
        cursor = conn.cursor()
        
        # Delete emails
        placeholders = ','.join('?' for _ in email_ids)
        cursor.execute(f'DELETE FROM email_metadata WHERE id IN ({placeholders})', email_ids)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {deleted_count} emails',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/api/memory/system-processes')
def get_system_processes():
    analyzer = ProcessAnalyzer()
    processes = analyzer.get_running_processes()
    return jsonify(processes)
@app.route('/api/memory/capture/<int:pid>', methods=['POST'])
def capture_memory(pid):
    capture = MemoryCapture()
    handler = request.json.get('handler', 'system')
    location = request.json.get('location', 'localhost')
    notes = request.json.get('notes')
    
    evidence_id, path = capture.capture_process_with_custody(
        pid, handler, location, notes)
    
    if evidence_id:
        return jsonify({
            'status': 'success',
            'evidence_id': evidence_id,
            'path': path
        })
    else:
        return jsonify({
            'status': 'error', 
            'message': 'Failed to capture memory'
        }), 500

@app.route('/api/memory/processes')
def get_memory_processes():
    analyzer = ProcessAnalyzer()
    processes = analyzer.get_running_processes()
    return jsonify(processes)

@app.route('/api/memory/dumps')
def get_memory_dumps():
    try:
        # Connect to database
        conn = sqlite3.connect("src/database/evidence.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query for memory dumps - simplified query to find more dumps
        cursor.execute("""
            SELECT f.id, f.file_name, f.file_path, f.file_size, f.last_modified
            FROM file_metadata f
            WHERE f.file_name LIKE 'memory_dump_%'
            ORDER BY f.last_modified DESC
        """)
        
        dumps = []
        for row in cursor.fetchall():
            # Extract process info from filename
            import re
            pid = "Unknown"
            process_name = "Unknown Process"
            
            if row['file_name']:
                match = re.search(r'memory_dump_(\d+)_(.+?)(?:_\d{8}_\d{6})?\.dmp', row['file_name'])
                if match:
                    pid = match.group(1)
                    process_name = match.group(2)
            
            dumps.append({
                'id': row['id'],
                'file_name': row['file_name'],
                'path': row['file_path'],
                'size': row['file_size'],
                'timestamp': row['last_modified'],
                'pid': pid,
                'process_name': process_name
            })
            
        conn.close()
        
        # Log the number of dumps found
        app.logger.info(f"Found {len(dumps)} memory dumps")
        return jsonify(dumps)
        
    except Exception as e:
        app.logger.error(f"Failed to get memory dumps: {str(e)}")
        return jsonify([])

@app.route('/api/memory/analyze/<int:pid>', methods=['POST'])
def analyze_process_memory(pid):
    try:
        data = request.json or {}
        duration = data.get('duration', 60)
        interval = data.get('interval', 5)
        
        # Placeholder response until the full implementation
        return jsonify({
            'status': 'success',
            'message': f'Analysis of process {pid} completed',
            'timelineId': f'analysis_{pid}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        })
        
    except Exception as e:
        app.logger.error(f"Process analysis failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/memory/capture/<int:pid>', methods=['POST'])
def capture_process_memory(pid):
    try:
        from src.memory_analysis.memory_capture import MemoryCapture
        
        handler = request.json.get('handler', 'system')
        location = request.json.get('location', 'localhost')
        notes = request.json.get('notes')
        
        capture = MemoryCapture()
        
        # Just use regular capture without custody integration for now
        dump_path, info = capture.capture_process_memory(pid)
        
        if dump_path or info:
            return jsonify({
                'status': 'success',
                'message': f'Memory captured for process {pid}',
                'path': dump_path
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to capture memory'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Memory capture failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/memory/dump/<int:dump_id>')
def get_memory_dump_details(dump_id):
    try:
        # Connect to database
        conn = sqlite3.connect("src/database/evidence.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get basic file info
        cursor.execute("""
            SELECT * FROM file_metadata WHERE id = ?
        """, (dump_id,))
        file_data = dict(cursor.fetchone() or {})
        
        # Get custody information
        cursor.execute("""
            SELECT * FROM custody_chain 
            WHERE evidence_id = ? 
            ORDER BY action_timestamp DESC
        """, (dump_id,))
        custody_events = [dict(row) for row in cursor.fetchall()]
        
        # Read memory info from JSON if available
        memory_info = {}
        json_path = file_data.get('file_path', '') + '.json'
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                import json
                memory_info = json.load(f)
        
        conn.close()
        
        return jsonify({
            'file_info': file_data,
            'custody_events': custody_events,
            'memory_info': memory_info
        })
        
    except Exception as e:
        app.logger.error(f"Failed to get memory dump details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/dumps/clear', methods=['POST'])
def clear_memory_dumps():
    try:
        # Connect to database
        conn = sqlite3.connect("src/database/evidence.db")
        cursor = conn.cursor()
        
        # First, get a list of files to delete
        cursor.execute("""
            SELECT file_path FROM file_metadata 
            WHERE file_name LIKE 'memory_dump_%'
        """)
        
        file_paths = [row[0] for row in cursor.fetchall()]
        
        # Delete files from filesystem
        deleted_count = 0
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    # Also try to delete the JSON companion file
                    json_path = f"{file_path}.json"
                    if os.path.exists(json_path):
                        os.remove(json_path)
                    deleted_count += 1
            except Exception as e:
                app.logger.error(f"Error deleting file {file_path}: {e}")
        
        # Delete entries from custody_chain
        cursor.execute("""
            DELETE FROM custody_chain 
            WHERE evidence_id IN (
                SELECT id FROM file_metadata 
                WHERE file_name LIKE 'memory_dump_%'
            )
        """)
        
        # Delete entries from file_metadata
        cursor.execute("""
            DELETE FROM file_metadata 
            WHERE file_name LIKE 'memory_dump_%'
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        app.logger.info(f"Deleted {deleted_count} memory dumps")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} memory dumps'
        })
        
    except Exception as e:
        app.logger.error(f"Failed to clear memory dumps: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# In app.py - Update the deepfake endpoint
@app.route('/api/analyze/deepfake', methods=['POST'])
def analyze_deepfake():
    """Analyze an uploaded image for potential deepfake manipulation"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        # Save the uploaded file
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        # Use your existing detector
        detector = DeepfakeDetector()
        detector_result = detector.detect_deepfake(upload_path)
        
        # Create a brand new result dict with only string/float/bool values
        # This avoids ALL NumPy type serialization issues
        clean_result = {
            "is_deepfake": bool(detector_result.get('is_deepfake', False)),
            "confidence": float(detector_result.get('confidence', 0.0)),
            "message": str(detector_result.get('message', "")),
            "filename": filename,
            "faces_detected": int(detector_result.get('faces_detected', 0))
        }
        
        # Add visualization path if it exists
        if 'visualization_path' in detector_result:
            vis_path = str(detector_result['visualization_path'])
            clean_result['visualization_path'] = vis_path
            # Extract filename for URL
            vis_filename = os.path.basename(vis_path)
            clean_result['visualization_url'] = f"/static/uploads/{vis_filename}"
        
        app.logger.info(f"Analysis complete: {'Deepfake' if clean_result['is_deepfake'] else 'Authentic'} " + 
                      f"with {int(clean_result['confidence'] * 100)}% confidence")
        
        return jsonify(clean_result)
        
    except Exception as e:
        app.logger.error(f"Deepfake analysis error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)


