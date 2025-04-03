import psutil
import os
from datetime import datetime
import logging
import json
import time
import hashlib
import sqlite3


class MemoryCapture:
    def __init__(self, dump_dir="dumps"):
        self.dump_dir = dump_dir
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def capture_process_memory(self, pid):
        """Capture memory of a specific process with enhanced details"""
        try:
            process = psutil.Process(pid)
            
            # Initialize CPU measurement
            process.cpu_percent()
            
            # Wait a short time to get accurate measurement
            time.sleep(0.5)
            
            # Now get CPU percent with the second measurement
            cpu_percent = process.cpu_percent()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_path = os.path.join(self.dump_dir, f"proc_{pid}_{timestamp}.dmp")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(dump_path), exist_ok=True)
            
            # Enhanced process information
            info = {
                'pid': process.pid,
                'name': process.name(),
                'exe': process.exe(),
                'created_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                'memory_usage': process.memory_info().rss // (1024 * 1024),  # Convert to MB
                'cpu_percent': round(cpu_percent, 1),  # Round to 1 decimal place
                'status': process.status(),
                'threads': len(process.threads())
            }
            
            # Attempt to get network connections
            try:
                info['connections'] = []
                for conn in process.connections():
                    conn_info = {
                        'type': conn.type,
                        'family': conn.family,
                        'status': conn.status,
                        'fd': conn.fd,
                    }
                    
                    # Format addresses as arrays for consistent access
                    if conn.laddr:
                        conn_info['laddr'] = [conn.laddr.ip, conn.laddr.port]
                    
                    if conn.raddr:
                        conn_info['raddr'] = [conn.raddr.ip, conn.raddr.port]
                        
                    info['connections'].append(conn_info)
            except (psutil.AccessDenied, AttributeError):
                info['connections'] = "Access Denied"
            
            # Save process information as JSON
            with open(f"{dump_path}.json", 'w') as f:
                json.dump(info, f, indent=2, default=str)
                
            self.logger.info(f"Captured memory info for process {pid}")
            return dump_path, info
                
        except Exception as e:
            self.logger.error(f"Error capturing process memory: {str(e)}")
            return None, None

    def capture_process_with_custody(self, pid, handler, location, notes=None):
        """Capture process memory and record in chain of custody"""
        try:
            # Create memory dump
            dump_path, info = self.capture_process_memory(pid)
            
            if dump_path and info:
                # Create a file entry first to get a numeric ID
                conn = sqlite3.connect("src/database/evidence.db")
                cursor = conn.cursor()
                
                # Calculate file hash if possible
                file_hash = ""
                file_size = 0
                if os.path.exists(dump_path):
                    with open(dump_path, 'rb') as f:
                        file_data = f.read()
                        # Add timestamp to the hash to make it unique
                        file_data += str(datetime.now().timestamp()).encode('utf-8')
                        file_hash = hashlib.sha256(file_data).hexdigest()
                    file_size = os.path.getsize(dump_path)
                
                # Generate a unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"memory_dump_{pid}_{info['name']}_{timestamp}.dmp"
                
                # Insert into file_metadata
                try:
                    cursor.execute("""
                        INSERT INTO file_metadata (file_name, file_path, file_size, hash_sha256, last_modified)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        filename,
                        dump_path, 
                        file_size,
                        file_hash,
                        datetime.now().isoformat()
                    ))
                    
                    evidence_id = cursor.lastrowid
                    conn.commit()
                    
                    # Import the custody manager
                    from src.chain_of_custody.custody_manager import CustodyManager
                    
                    custody = CustodyManager()
                    custody.log_action(
                        evidence_id=evidence_id,
                        evidence_type="memory_dump",
                        action_type="acquisition",
                        handler=handler,
                        location=location,
                        file_path=dump_path,
                        notes=f"Memory capture of process {pid} ({info['name']}). {notes or ''}"
                    )
                    
                    self.logger.info(f"Memory capture recorded in chain of custody: {evidence_id}")
                    return evidence_id, dump_path
                    
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed" in str(e):
                        # If we get a unique constraint error, create a new unique hash
                        import random
                        unique_suffix = f"{timestamp}_{random.randint(1000, 9999)}"
                        file_hash = hashlib.sha256((file_hash + unique_suffix).encode('utf-8')).hexdigest()
                        
                        cursor.execute("""
                            INSERT INTO file_metadata (file_name, file_path, file_size, hash_sha256, last_modified)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            filename,
                            dump_path, 
                            file_size,
                            file_hash,
                            datetime.now().isoformat()
                        ))
                        
                        evidence_id = cursor.lastrowid
                        conn.commit()
                        
                        # Import the custody manager
                        from src.chain_of_custody.custody_manager import CustodyManager
                        
                        custody = CustodyManager()
                        custody.log_action(
                            evidence_id=evidence_id,
                            evidence_type="memory_dump",
                            action_type="acquisition",
                            handler=handler,
                            location=location,
                            file_path=dump_path,
                            notes=f"Memory capture of process {pid} ({info['name']}). {notes or ''}"
                        )
                        
                        self.logger.info(f"Memory capture recorded in chain of custody (with unique hash): {evidence_id}")
                        return evidence_id, dump_path
                    else:
                        raise
                finally:
                    conn.close()
        except Exception as e:
            self.logger.error(f"Failed to record memory capture in chain of custody: {str(e)}")
            return None, None

    def get_system_memory_info(self):
        """Get system-wide memory statistics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total_memory': mem.total // (1024**3),  # GB
            'available_memory': mem.available // (1024**3),  # GB
            'memory_percent': mem.percent,
            'swap_used': swap.used // (1024**3),  # GB
            'swap_free': swap.free // (1024**3),  # GB
            'swap_percent': swap.percent
        }

    def analyze_memory_changes(self, pid, interval=5, duration=60):
        """Monitor memory changes of a process over time"""
        try:
            process = psutil.Process(pid)
            timeline = []
            
            self.logger.info(f"Starting memory timeline analysis for PID {pid} ({process.name()})")
            
            for i in range(0, duration, interval):
                try:
                    snapshot = {
                        'timestamp': datetime.now().isoformat(),
                        'memory_info': process.memory_info()._asdict(),
                        'num_threads': len(process.threads()),
                        'cpu_percent': process.cpu_percent(interval=0.1),
                        'status': process.status()
                    }
                    timeline.append(snapshot)
                    
                    # Record any file activity
                    try:
                        open_files = process.open_files()
                        if open_files:
                            snapshot['open_files'] = [f.path for f in open_files[:10]]  # Limit to 10 files
                    except psutil.AccessDenied:
                        snapshot['open_files'] = "Access Denied"
                    
                    self.logger.info(f"Collected snapshot {i//interval + 1}/{duration//interval}")
                    
                except psutil.NoSuchProcess:
                    self.logger.error(f"Process {pid} no longer exists")
                    break
                    
                time.sleep(interval)
                
            # Save timeline to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.dump_dir, f"timeline_{pid}_{timestamp}.json")
            
            with open(output_file, 'w') as f:
                json.dump(timeline, f, indent=2, default=str)
                
            self.logger.info(f"Memory timeline saved to {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Timeline analysis failed: {str(e)}")
            return None