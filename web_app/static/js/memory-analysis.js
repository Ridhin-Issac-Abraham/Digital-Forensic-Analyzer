/**
 * Memory Analysis Dashboard
 * Handles process listing, memory dumps, and system memory visualization
 */

// Global variables
let processData = [];
let memoryCharts = {};
let refreshInterval = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize memory analysis tab
    initMemoryAnalysis();
    
    // Set up refresh button
    document.getElementById('refreshProcesses').addEventListener('click', fetchProcesses);
    
    // Set up charts when tab becomes active
    const memoryTab = document.getElementById('memoryAnalysis');
    if (memoryTab) {
        const tabElement = bootstrap.Tab.getOrCreateInstance(document.querySelector('a[href="#memoryAnalysis"]'));
        tabElement._element.addEventListener('shown.bs.tab', function() {
            initMemoryCharts();
            fetchProcesses();
        });
    }
    
    // Add event listener for memory dumps tab activation
    const memoryDumpsTab = document.querySelector('a[href="#memoryDumps"]');
    if (memoryDumpsTab) {
        memoryDumpsTab.addEventListener('shown.bs.tab', function() {
            console.log('Memory dumps tab activated');
            fetchMemoryDumps();
        });
    }
    
    // Initial load of memory dumps
    fetchMemoryDumps();
    
    // Add clear dumps button handler
    const clearDumpsBtn = document.getElementById('clearMemoryDumps');
    if (clearDumpsBtn) {
        clearDumpsBtn.addEventListener('click', clearAllMemoryDumps);
    }
});

/**
 * Initialize memory analysis components
 */
function initMemoryAnalysis() {
    // Initial process fetch
    fetchProcesses();
    
    // Set up auto-refresh (every 30 seconds)
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(fetchProcesses, 30000);
}

/**
 * Fetch running processes from the API
 */
async function fetchProcesses() {
    try {
        const button = document.getElementById('refreshProcesses');
        if (button) {
            // Show loading state
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            button.disabled = true;
        }
        
        // Change this URL to match our new endpoint
        const response = await fetch('/api/memory/system-processes');
        const data = await response.json();
        
        // Update global data
        processData = data;
        
        // Update process table
        updateProcessTable(data);
        
        // Update system memory info
        fetchSystemMemoryInfo();
        
        // Update counter
        const counter = document.getElementById('processCount');
        if (counter) {
            counter.textContent = `${data.length} processes`;
        }
        
        if (button) {
            // Reset button state
            button.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
            button.disabled = false;
        }
        
    } catch (error) {
        console.error('Failed to fetch processes:', error);
        Utils.showAlert('danger', 'Failed to fetch running processes');
        
        // Reset button state
        const button = document.getElementById('refreshProcesses');
        if (button) {
            button.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
            button.disabled = false;
        }
    }
}

/**
 * Update the process table with fetched data
 */
function updateProcessTable(processes) {
    const tableBody = document.getElementById('processTable');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Sort processes by memory usage (descending)
    processes.sort((a, b) => b.memory_usage - a.memory_usage);
    
    // Add rows to table
    processes.forEach(process => {
        const row = document.createElement('tr');
        
        // Apply classes based on process type
        if (process.name.toLowerCase().includes('system') || process.username === 'SYSTEM') {
            row.classList.add('table-light');
        }
        
        row.innerHTML = `
            <td>${process.pid}</td>
            <td>${process.name}</td>
            <td>${process.username || 'N/A'}</td>
            <td>${process.memory_usage} MB</td>
            <td>${process.cpu_percent || '0.0'}%</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-primary" onclick="captureProcess(${process.pid})">
                        <i class="fas fa-camera"></i> Capture
                    </button>
                    <button class="btn btn-info" onclick="analyzeProcess(${process.pid})">
                        <i class="fas fa-search"></i> Analyze
                    </button>
                </div>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * Capture memory for a specific process
 */
async function captureProcess(pid) {
    try {
        // Find process info
        const process = processData.find(p => p.pid === pid);
        if (!process) {
            throw new Error(`Process with PID ${pid} not found`);
        }
        
        // Show confirmation
        if (!confirm(`Capture memory for process "${process.name}" (PID: ${pid})?`)) {
            return;
        }
        
        // Show loading alert
        Utils.showAlert('info', `Capturing memory for ${process.name} (PID: ${pid})...`, 0);
        
        // Get current user (for chain of custody)
        const handler = 'Forensic Investigator'; // This should come from your auth system
        
        // Capture memory
        const response = await fetch(`/api/memory/capture/${pid}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                handler: handler,
                location: window.location.hostname,
                notes: `Memory capture initiated from dashboard by ${handler}`
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            Utils.showAlert('success', `Memory successfully captured for ${process.name}`, 5000);
            
            // Update memory dumps list
            fetchMemoryDumps();
        } else {
            throw new Error(result.message || 'Memory capture failed');
        }
        
    } catch (error) {
        console.error('Memory capture failed:', error);
        Utils.showAlert('danger', `Failed to capture memory: ${error.message}`);
    }
}

/**
 * Analyze a specific process (timeline analysis)
 */
async function analyzeProcess(pid) {
    try {
        // Find process info
        const process = processData.find(p => p.pid === pid);
        if (!process) {
            throw new Error(`Process with PID ${pid} not found`);
        }
        
        // Ask for analysis duration
        const duration = prompt(`Enter analysis duration in seconds for "${process.name}" (Max: 300):`, "60");
        if (!duration) {
            return;
        }
        
        // Convert to number and validate
        const durationNum = parseInt(duration);
        if (isNaN(durationNum) || durationNum < 5 || durationNum > 300) {
            alert('Please enter a valid duration between 5 and 300 seconds.');
            return;
        }
        
        // Show loading alert
        Utils.showAlert('info', `Analyzing ${process.name} for ${durationNum} seconds...`, 0);
        
        // Start analysis
        const response = await fetch(`/api/memory/analyze/${pid}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                duration: durationNum,
                interval: 5  // Take snapshots every 5 seconds
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            Utils.showAlert('success', `Analysis complete for ${process.name}. Timeline saved.`, 5000);
            
            // Option to view results
            setTimeout(() => {
                if (confirm('Analysis complete. View results now?')) {
                    // Open results viewer
                    openTimelineViewer(result.timelineId);
                }
            }, 500);
        } else {
            throw new Error(result.message || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Process analysis failed:', error);
        Utils.showAlert('danger', `Failed to analyze process: ${error.message}`);
    }
}

/**
 * Fetch and display memory dumps list
 */
async function fetchMemoryDumps() {
    try {
        console.log('Fetching memory dumps...');
        
        // Show loading indicator
        const loadingEl = document.getElementById('memoryDumpsLoading');
        const emptyEl = document.getElementById('memoryDumpsEmpty');
        const dumpsListEl = document.getElementById('memoryDumpsList');
        
        if (loadingEl) loadingEl.classList.remove('d-none');
        if (emptyEl) emptyEl.classList.add('d-none');
        if (dumpsListEl) dumpsListEl.innerHTML = '';
        
        // Fetch memory dumps
        const response = await fetch('/api/memory/dumps');
        console.log('Memory dumps response:', response);
        
        const data = await response.json();
        console.log('Memory dumps data:', data);
        
        // Hide loading indicator
        if (loadingEl) loadingEl.classList.add('d-none');
        
        // Update UI
        if (!dumpsListEl) {
            console.error('Memory dumps list element not found');
            return;
        }
        
        if (!data || data.length === 0) {
            console.log('No memory dumps found');
            if (emptyEl) emptyEl.classList.remove('d-none');
            return;
        }
        
        // Sort by date (newest first)
        data.sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
        
        let html = '<div class="list-group">';
        data.forEach(dump => {
            const date = dump.timestamp ? new Date(dump.timestamp).toLocaleString() : 'Unknown';
            html += `
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${dump.process_name || 'Unknown'} (PID: ${dump.pid || 'N/A'})</h6>
                        <small class="text-muted">Captured: ${date}</small>
                        <div>Size: ${formatFileSize(dump.size || 0)}</div>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-primary" onclick="viewDump(${dump.id})">
                            <i class="fas fa-eye"></i> View Details
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        dumpsListEl.innerHTML = html;
        console.log('Memory dumps rendered');
        
    } catch (error) {
        console.error('Failed to fetch memory dumps:', error);
        const dumpsListEl = document.getElementById('memoryDumpsList');
        if (dumpsListEl) {
            dumpsListEl.innerHTML = `
                <div class="alert alert-danger">
                    Failed to load memory dumps: ${error.message}
                </div>
            `;
        }
        
        // Hide loading indicator
        const loadingEl = document.getElementById('memoryDumpsLoading');
        if (loadingEl) loadingEl.classList.add('d-none');
    }
}

/**
 * View memory dump details
 */
async function viewDump(id) {
    try {
        // Show loading state
        document.getElementById('memoryDumpModalBody').innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Loading memory dump details...</p></div>';
        document.getElementById('memoryDumpModalTitle').textContent = 'Memory Dump Details';
        
        // Show modal
        const memoryDumpModal = new bootstrap.Modal(document.getElementById('memoryDumpModal'));
        memoryDumpModal.show();
        
        // Fetch dump details
        const response = await fetch(`/api/memory/dump/${id}`);
        const data = await response.json();
        
        if (response.ok) {
            // Format dates
            const fileDate = data.file_info.last_modified ? new Date(data.file_info.last_modified).toLocaleString() : 'Unknown';
            
            // Prepare process information
            let processInfo = '';
            if (data.memory_info) {
                // Handle different property names for the same data
                const pid = data.memory_info.pid || 'N/A';
                const name = data.memory_info.name || data.memory_info.process_name || 'Unknown';
                const status = data.memory_info.status || 'Unknown';
                const memoryUsage = data.memory_info.memory_usage || 
                                   (data.memory_info.memory_info?.rss ? 
                                    Math.round(data.memory_info.memory_info.rss / (1024 * 1024)) : 
                                    'N/A');
                const cpuUsage = data.memory_info.cpu_percent || data.memory_info.cpu_usage || 'N/A';
                const createdTime = data.memory_info.create_time || data.memory_info.created_time || 'Unknown';
                
                processInfo = `
                    <div class="card mb-3">
                        <div class="card-header bg-primary text-white">Process Information</div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>PID:</strong> ${pid}</p>
                                    <p><strong>Name:</strong> ${name}</p>
                                    <p><strong>Created:</strong> ${createdTime ? (typeof createdTime === 'string' ? createdTime : new Date(createdTime).toLocaleString()) : 'Unknown'}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Status:</strong> ${status}</p>
                                    <p><strong>Memory Usage:</strong> ${typeof memoryUsage === 'number' ? `${memoryUsage} MB` : memoryUsage}</p>
                                    <p><strong>CPU Usage:</strong> ${cpuUsage !== 'N/A' ? `${cpuUsage}%` : 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add connections if available
                if (data.memory_info.connections && data.memory_info.connections !== "Access Denied" && 
                    (Array.isArray(data.memory_info.connections) || typeof data.memory_info.connections === 'object')) {
                    
                    processInfo += `
                        <div class="card mb-3">
                            <div class="card-header bg-info text-white">Network Connections</div>
                            <div class="card-body p-0">
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped mb-0">
                                        <thead>
                                            <tr>
                                                <th>Type</th>
                                                <th>Local Address</th>
                                                <th>Remote Address</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                    `;
                    
                    data.memory_info.connections.forEach(conn => {
                        // Format local address based on data structure
                        let localAddress = 'N/A';
                        if (conn.laddr) {
                            if (Array.isArray(conn.laddr)) {
                                localAddress = `${conn.laddr[0] || ''}:${conn.laddr[1] || ''}`;
                            } else {
                                localAddress = `${conn.laddr.ip || ''}:${conn.laddr.port || ''}`;
                            }
                        }
                        
                        // Format remote address based on data structure
                        let remoteAddress = 'N/A';
                        if (conn.raddr) {
                            if (Array.isArray(conn.raddr)) {
                                remoteAddress = `${conn.raddr[0] || ''}:${conn.raddr[1] || ''}`;
                            } else {
                                remoteAddress = `${conn.raddr.ip || ''}:${conn.raddr.port || ''}`;
                            }
                        }
                        
                        // Map connection type to readable format
                        let connectionType = 'Unknown';
                        switch(conn.type) {
                            case 1: connectionType = 'TCP'; break;
                            case 2: connectionType = 'UDP'; break;
                            default: connectionType = `Type ${conn.type}`;
                        }
                        
                        processInfo += `
                            <tr>
                                <td>${connectionType}</td>
                                <td>${localAddress}</td>
                                <td>${remoteAddress}</td>
                                <td>${conn.status || 'N/A'}</td>
                            </tr>
                        `;
                    });
                    
                    processInfo += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>`;
                } else if (data.memory_info.connections === "Access Denied") {
                    processInfo += `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle"></i> Access Denied for network connections
                        </div>
                    `;
                }
            }
            
            // Prepare chain of custody information
            let custodyHtml = '';
            if (data.custody_events && data.custody_events.length > 0) {
                custodyHtml = `
                    <div class="card mb-3">
                        <div class="card-header bg-secondary text-white">Chain of Custody</div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-sm table-striped mb-0">
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Action</th>
                                            <th>Handler</th>
                                            <th>Notes</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                `;
                
                data.custody_events.forEach(event => {
                    const eventTime = event.action_timestamp ? new Date(event.action_timestamp).toLocaleString() : 'Unknown';
                    custodyHtml += `
                        <tr>
                            <td>${eventTime}</td>
                            <td>${event.action_type || 'N/A'}</td>
                            <td>${event.handler || 'System'}</td>
                            <td>${event.notes || 'No notes'}</td>
                        </tr>
                    `;
                });
                
                custodyHtml += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>`;
            }
            
            // Update modal title
            document.getElementById('memoryDumpModalTitle').textContent = 
                `Memory Dump: ${data.file_info.file_name || `ID ${id}`}`;
            
            // Update modal content
            document.getElementById('memoryDumpModalBody').innerHTML = `
                <div class="mb-3">
                    <strong>File:</strong> ${data.file_info.file_name || 'Unknown'}
                    <br>
                    <strong>Size:</strong> ${formatFileSize(data.file_info.file_size || 0)}
                    <br>
                    <strong>Captured:</strong> ${fileDate}
                    <br>
                    <strong>Hash:</strong> <span class="text-monospace">${data.file_info.hash_sha256 || 'Not available'}</span>
                </div>
                
                ${processInfo}
                ${custodyHtml}
            `;
        } else {
            throw new Error(data.error || 'Failed to load memory dump details');
        }
    } catch (error) {
        console.error('Error viewing memory dump:', error);
        document.getElementById('memoryDumpModalBody').innerHTML = `
            <div class="alert alert-danger">
                Error loading memory dump details: ${error.message}
            </div>
        `;
    }
}

/**
 * Download memory dump file
 */
function downloadDump(id) {
    window.location.href = `/api/memory/download/${id}`;
}

/**
 * Initialize memory usage charts
 */
function initMemoryCharts() {
    // Physical memory chart
    const physicalCtx = document.getElementById('physicalMemoryChart');
    if (physicalCtx && !memoryCharts.physical) {
        memoryCharts.physical = new Chart(physicalCtx, {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Available'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#dc3545', '#28a745']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Swap memory chart
    const swapCtx = document.getElementById('swapMemoryChart');
    if (swapCtx && !memoryCharts.swap) {
        memoryCharts.swap = new Chart(swapCtx, {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Free'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#fd7e14', '#20c997']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Fetch initial data
    fetchSystemMemoryInfo();
}

/**
 * Fetch system memory information and update charts
 */
async function fetchSystemMemoryInfo() {
    try {
        const response = await fetch('/api/memory/system');
        const data = await response.json();
        
        // Update physical memory chart
        if (memoryCharts.physical) {
            memoryCharts.physical.data.datasets[0].data = [
                data.memory_percent,
                100 - data.memory_percent
            ];
            memoryCharts.physical.update();
        }
        
        // Update swap memory chart
        if (memoryCharts.swap) {
            memoryCharts.swap.data.datasets[0].data = [
                data.swap_percent,
                100 - data.swap_percent
            ];
            memoryCharts.swap.update();
        }
        
    } catch (error) {
        console.error('Failed to fetch system memory info:', error);
    }
}

/**
 * Format file size in bytes to human-readable format
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(2) + ' MB';
    else return (bytes / 1073741824).toFixed(2) + ' GB';
}

/**
 * Open timeline viewer for process analysis
 */
function openTimelineViewer(timelineId) {
    window.open(`/memory/timeline/${timelineId}`, '_blank');
}

/**
 * Clean up when leaving the page
 */
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

/**
 * Clear all memory dumps
 */
async function clearAllMemoryDumps() {
    // Confirm deletion
    if (!confirm('Are you sure you want to delete ALL memory dumps? This cannot be undone.')) {
        return;
    }
    
    try {
        // Show loading state
        const button = document.getElementById('clearMemoryDumps');
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        }
        
        // Call API to delete dumps
        const response = await fetch('/api/memory/dumps/clear', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            Utils.showAlert('success', `Successfully deleted ${result.deleted_count} memory dumps`);
            // Refresh the dumps list
            fetchMemoryDumps();
        } else {
            throw new Error(result.error || 'Failed to delete memory dumps');
        }
    } catch (error) {
        console.error('Failed to clear memory dumps:', error);
        Utils.showAlert('danger', `Error: ${error.message}`);
    } finally {
        // Reset button state
        const button = document.getElementById('clearMemoryDumps');
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-trash"></i> Clear All Dumps';
        }
    }
}