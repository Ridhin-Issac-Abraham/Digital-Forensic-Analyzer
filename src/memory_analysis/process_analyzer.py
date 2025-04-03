import psutil
import json
from datetime import datetime
import logging
import time

class ProcessAnalyzer:
    def __init__(self):
        self.processes = {}
        self.setup_logging()
        self.process_categories = {
            'system': ['System', 'Registry', 'smss.exe', 'csrss.exe'],
            'browsers': ['chrome.exe', 'firefox.exe', 'msedge.exe'],
            'security': ['antimalware', 'defender', 'firewall']
        }

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_running_processes(self, sort_by_memory=True):
        """Get list of running processes with details"""
        processes = []
        
        # First pass to initialize CPU monitoring
        process_list = list(psutil.process_iter(['pid', 'name', 'username', 'memory_info']))
        for proc in process_list:
            try:
                proc.cpu_percent(interval=0)  # Initialize CPU monitoring
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Brief pause to collect CPU data
        time.sleep(0.1)
        
        # Second pass to get actual values
        for proc in process_list:
            try:
                # Skip system processes
                if proc.info['pid'] == 0 or proc.info['pid'] == 4:
                    continue
                
                # Get CPU percent (initialized in first pass)
                cpu_percent = proc.cpu_percent(interval=0)
                
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'username': proc.info['username'],
                    'memory_usage': proc.info['memory_info'].rss // 1024 // 1024,  # MB
                    'cpu_percent': round(cpu_percent, 1) if cpu_percent is not None else 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if sort_by_memory:
            processes.sort(key=lambda x: x['memory_usage'], reverse=True)
            
        return processes

    def analyze_process(self, pid):
        """Analyze specific process"""
        try:
            proc = psutil.Process(pid)
            
            # Basic info that doesn't require special privileges
            info = {
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'created_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                'cpu_percent': proc.cpu_percent(),
                'memory_usage': proc.memory_info().rss // 1024 // 1024,  # MB
            }
            
            # Try to get additional info with error handling
            try:
                info['threads'] = len(proc.threads())
            except (psutil.AccessDenied, psutil.ZombieProcess):
                info['threads'] = "Access Denied"
                
            try:
                info['connections'] = [conn._asdict() for conn in proc.connections()]
            except (psutil.AccessDenied, psutil.ZombieProcess):
                info['connections'] = "Access Denied"
            
            return info
            
        except psutil.NoSuchProcess:
            self.logger.error(f"Process with PID {pid} not found")
            return None
        except psutil.AccessDenied:
            self.logger.error(f"Access denied for process with PID {pid}")
            return None
        except Exception as e:
            self.logger.error(f"Error analyzing process {pid}: {str(e)}")
            return None

    def get_processes_by_category(self, category):
        """Get processes filtered by category"""
        processes = self.get_running_processes()
        if category in self.process_categories:
            return [p for p in processes if any(
                pattern in p['name'].lower() 
                for pattern in self.process_categories[category]
            )]
        return []