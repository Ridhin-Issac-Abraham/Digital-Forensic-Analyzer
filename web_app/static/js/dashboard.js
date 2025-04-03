// Global variables
let analysisCount = 0;
const modal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));

// Add these variables at the top of dashboard.js
let currentEmailPage = 1;
const emailsPerPage = 10; // Configurable
let totalEmails = 0;

// Utility Object
const Utils = {
    showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Find the active tab content
        const activeTabContent = document.querySelector('.tab-pane.active');
        if (activeTabContent) {
            // Insert at beginning of active tab
            activeTabContent.insertBefore(alertDiv, activeTabContent.firstChild);
        } else {
            // Fallback to file analysis tab if no active tab found
            const fileTab = document.getElementById('fileAnalysis');
            fileTab.insertBefore(alertDiv, fileTab.firstChild);
        }
        
        setTimeout(() => alertDiv.remove(), 5000);
    },

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    getBadgeClass(score) {
        if (!score) return 'bg-secondary';
        if (score < 0.3) return 'bg-success';
        if (score < 0.7) return 'bg-warning';
        return 'bg-danger';
    },

    getStatus(score) {
        if (score === 0) return 'Original';
        if (score < 0.3) return 'Low Risk';
        if (score < 0.7) return 'Medium Risk';
        return 'High Risk';
    },

    getActionBadgeClass(action) {
        const classes = {
            'COLLECT': 'bg-success',
            'ANALYZE': 'bg-primary',
            'VIEW': 'bg-info',
            'MODIFY': 'bg-warning'
        };
        return classes[action] || 'bg-secondary';
    },

    getActionIcon(action) {
        const icons = {
            'COLLECT': 'fas fa-plus',
            'ANALYZE': 'fas fa-microscope',
            'VIEW': 'fas fa-eye',
            'MODIFY': 'fas fa-edit'
        };
        return icons[action] || 'fas fa-dot-circle';
    }
};

// Email Functions
async function loadEmails(page = 1) {
    try {
        // Update current page
        currentEmailPage = page;
        
        // Show loading indicator
        document.getElementById('emailsBody').innerHTML = '<tr><td colspan="6" class="text-center">Loading emails...</td></tr>';
        
        const response = await fetch(`/api/emails?page=${page}&limit=${emailsPerPage}`);
        const data = await response.json();
        
        if (Array.isArray(data.emails)) {
            // Sort emails by date (newest first)
            data.emails.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            // Update UI
            updateEmailTable(data.emails);
            
            // Update pagination
            totalEmails = data.total || data.emails.length;
            updateEmailPagination(page, totalEmails);
            
            // Update counter
            document.getElementById('emailCount').textContent = `${totalEmails} emails`;
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error loading emails:', error);
        document.getElementById('emailsBody').innerHTML = 
            `<tr><td colspan="6" class="text-center text-danger">Error loading emails: ${error.message}</td></tr>`;
    }
}

// Add this new function to handle pagination UI
function updateEmailPagination(currentPage, totalCount) {
    const totalPages = Math.ceil(totalCount / emailsPerPage);
    const paginationEl = document.getElementById('emailPagination');
    
    let paginationHtml = `
        <nav aria-label="Email pagination">
            <ul class="pagination justify-content-center mb-0">
                <li class="page-item ${currentPage <= 1 ? 'disabled' : ''}">
                    <button class="page-link" ${currentPage <= 1 ? 'disabled' : ''} 
                     onclick="loadEmails(${currentPage-1})">Previous</button>
                </li>
    `;
    
    // Show page numbers with limit to avoid too many buttons
    const maxPageButtons = 5;
    const startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
    const endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
    
    if (startPage > 1) {
        paginationHtml += `<li class="page-item"><button class="page-link" onclick="loadEmails(1)">1</button></li>`;
        if (startPage > 2) paginationHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${currentPage === i ? 'active' : ''}">
                <button class="page-link" onclick="loadEmails(${i})">${i}</button>
            </li>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) paginationHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        paginationHtml += `<li class="page-item"><button class="page-link" onclick="loadEmails(${totalPages})">${totalPages}</button></li>`;
    }
    
    paginationHtml += `
                <li class="page-item ${currentPage >= totalPages ? 'disabled' : ''}">
                    <button class="page-link" ${currentPage >= totalPages ? 'disabled' : ''}
                     onclick="loadEmails(${currentPage+1})">Next</button>
                </li>
            </ul>
        </nav>
        <div class="text-center text-muted small mt-2">
            Showing page ${currentPage} of ${totalPages || 1} (${totalCount} emails total)
        </div>
    `;
    
    paginationEl.innerHTML = paginationHtml;
}

async function refreshEmails() {
    const btn = document.getElementById('refreshEmails');
    const originalText = btn.innerHTML;
    
    try {
        // Update button state
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching...';
        
        // Fetch new emails
        const response = await fetch('/api/emails/fetch', { 
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Reset to first page since we have new emails
            currentEmailPage = 1;
            
            // Force refresh email list
            await loadEmails(1); // Explicitly go to page 1 to see new emails
            
            // Show success message
            Utils.showAlert('success', data.message || `Fetched ${data.count} new emails`);
        } else {
            throw new Error(data.message || 'Failed to fetch new emails');
        }
    } catch (error) {
        console.error('Email refresh failed:', error);
        Utils.showAlert('danger', `Failed to refresh emails: ${error.message}`);
    } finally {
        // Reset button state
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Add checkboxes to email rows in updateEmailTable function
function updateEmailTable(emails) {
    const tbody = document.getElementById('emailsBody');
    
    // Clear existing content
    tbody.innerHTML = '';
    
    // Add new rows
    emails.forEach(email => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="email-checkbox" data-id="${email.id}">
            </td>
            <td>${new Date(email.date).toLocaleString()}</td>
            <td>${email.sender}</td>
            <td>${email.subject}</td>
            <td>
                <span class="badge bg-${email.spf_pass ? 'success' : 'danger'}" title="SPF">SPF</span>
                <span class="badge bg-${email.dkim_pass ? 'success' : 'danger'}" title="DKIM">DKIM</span>
                <span class="badge bg-${email.dmarc_pass ? 'success' : 'danger'}" title="DMARC">DMARC</span>
            </td>
            <td>
                <span class="badge ${email.is_forged ? 'bg-danger' : 'bg-success'}">
                    ${email.is_forged ? 'Suspicious' : 'Valid'}
                </span>
                ${email.has_attachments ? '<span class="badge bg-warning ms-1">Attachment</span>' : ''}
            </td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteEmail(${email.id}, '${email.subject.replace(/'/g, "\\'")}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Update header to include checkbox column
    const headerRow = document.querySelector('#emailsTable thead tr');
    if (headerRow && headerRow.querySelector('th:first-child') && !headerRow.querySelector('th:first-child').classList.contains('select-all')) {
        const selectAllCell = document.createElement('th');
        selectAllCell.classList.add('select-all');
        selectAllCell.innerHTML = '<input type="checkbox" id="selectAllEmails">';
        headerRow.insertBefore(selectAllCell, headerRow.firstChild);
        
        // Add select all event handler
        document.getElementById('selectAllEmails').addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.email-checkbox');
            checkboxes.forEach(checkbox => checkbox.checked = this.checked);
        });
    }
}

// Add delete selected function
function deleteSelectedEmails() {
    const selectedEmails = document.querySelectorAll('.email-checkbox:checked');
    if (selectedEmails.length === 0) {
        Utils.showAlert('warning', 'No emails selected');
        return;
    }
    
    if (confirm(`Are you sure you want to delete ${selectedEmails.length} selected emails?`)) {
        const ids = Array.from(selectedEmails).map(checkbox => checkbox.dataset.id);
        
        fetch('/api/emails/delete-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        })
        .then(response => {
            if (response.ok) {
                Utils.showAlert('success', `Successfully deleted ${selectedEmails.length} emails`);
                loadEmails(currentEmailPage);
            } else {
                throw new Error('Failed to delete selected emails');
            }
        })
        .catch(error => {
            Utils.showAlert('danger', error.message);
        });
    }
}

// Add delete selected button to card header
// Find and modify the email card header element
const emailHeader = document.querySelector('#emailEvidence .card-header');
if (emailHeader) {
    const deleteSelectedButton = document.createElement('button');
    deleteSelectedButton.className = 'btn btn-danger btn-sm ms-2';
    deleteSelectedButton.innerHTML = '<i class="fas fa-trash-alt"></i> Delete Selected';
    deleteSelectedButton.onclick = deleteSelectedEmails;
    
    // Add to the header's button container
    emailHeader.querySelector('div').appendChild(deleteSelectedButton);
}

// Evidence Functions
async function loadEvidence() {
    try {
        const response = await fetch('/api/evidence');
        const data = await response.json();
        
        if (Array.isArray(data)) {
            // Sort data by upload_date in descending order (newest first)
            data.sort((a, b) => {
                const dateA = new Date(a.upload_date || 0);
                const dateB = new Date(b.upload_date || 0);
                return dateB - dateA;  // For descending order
            });
            
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = '';
            data.forEach(result => addResultRow(result));
            analysisCount = data.length;
            document.getElementById('resultCount').textContent = `${analysisCount} files`;
        }
    } catch (error) {
        console.error('Error loading evidence:', error);
        Utils.showAlert('danger', 'Failed to load evidence');
    }
}

function addResultRow(result) {
    const tbody = document.getElementById('resultsBody');
    const row = document.createElement('tr');
    
    // Format the file type display
    const getFileType = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        const types = {
            'pdf': 'PDF Document',
            'jpg': 'JPEG Image',
            'jpeg': 'JPEG Image',
            'png': 'PNG Image',
            'gif': 'GIF Image',
            'bmp': 'Bitmap Image',
            'txt': 'Text Document'
        };
        return types[ext] || 'Unknown File';
    };

    const fileType = getFileType(result.filename);
    
    // Clean the result data for JSON stringification
    const jsonStr = JSON.stringify(result).replace(/'/g, "&apos;");
    
    row.innerHTML = `
        <td>${result.filename}</td>
        <td>${fileType}</td>
        <td>${Utils.formatFileSize(result.size)}</td>
        
        <td>
            <button class="btn btn-sm btn-details me-2" onclick='showDetails(${jsonStr})'>
                Details
            </button>
            <button class="btn btn-sm btn-danger" onclick='deleteEvidence(${result.id}, "${result.filename}")'>
                Delete
            </button>
        </td>
    `;
    tbody.insertBefore(row, tbody.firstChild);
}

function showDetails(result) {
    console.log('Raw result data:', result);
    const content = document.getElementById('fileDetailsContent');
    
    try {
        // Check file type based on filename for PDFs
        const isPDF = result.filename.toLowerCase().endsWith('.pdf');
        const isImage = result.type === 'image' || 
                       (result.mime_type && result.mime_type.startsWith('image/')) ||
                       /\.(jpg|jpeg|png|gif|bmp)$/i.test(result.filename);
        
        console.log('File type checks:', { isPDF, isImage, filename: result.filename });
        
        if (isPDF) {
            content.innerHTML = createPDFContent(result);
        } else if (isImage) {
            content.innerHTML = createImageContent(result);
        } else {
            content.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Unsupported file type: ${result.filename}
                </div>
            `;
        }

        // Load custody chain
        if (result.id) {
            loadCustodyChain(result.id);
        }
        
        // Show modal
        modal.show();

    } catch (error) {
        console.error('Error in showDetails:', error);
        content.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error showing file details: ${error.message}
            </div>
        `;
    }
}

function createImageContent(result) {
    console.log('Image metadata received:', result);  // Add this line for debugging
    
    // If metadata is nested inside a 'metadata' field, use it
    const metadata = result.metadata || result;
    
    return `
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h6 class="border-bottom pb-2 mb-3">Image Technical Details</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <ul class="list-group mb-3">
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Dimensions:</span>
                                    <span class="text-muted">${metadata.width || result.width} × ${metadata.height || result.height} px</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Format:</span>
                                    <span class="text-muted">${metadata.format || result.format || result.type}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Color Mode:</span>
                                    <span class="text-muted">${metadata.mode || result.mode || 'N/A'}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Color Depth:</span>
                                    <span class="text-muted">${metadata.color_depth || result.color_depth || '24-bit color'}</span>
                                </li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <ul class="list-group mb-3">
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Resolution:</span>
                                    <span class="text-muted">${metadata.dpi ? (Array.isArray(metadata.dpi) ? `${metadata.dpi[0]}, ${metadata.dpi[1]} DPI` : metadata.dpi) : 'N/A'}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>File Size:</span>
                                    <span class="text-muted">${Utils.formatFileSize(metadata.size || result.size)}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Aspect Ratio:</span>
                                    <span class="text-muted">${metadata.aspect_ratio || result.aspect_ratio || (metadata.width && metadata.height ? (metadata.width / metadata.height).toFixed(2) : 'N/A')}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Orientation:</span>
                                    <span class="text-muted">${metadata.orientation || result.orientation || 'Normal'}</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function createPDFContent(result) {
    return `
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h6 class="border-bottom pb-2 mb-3">PDF Document Information</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <ul class="list-group mb-3">
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Filename:</span>
                                    <span class="text-muted">${result.filename}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>File Size:</span>
                                    <span class="text-muted">${Utils.formatFileSize(result.size)}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>File Hash:</span>
                                    <span class="text-muted text-truncate" style="max-width: 200px;" title="${result.hash}">${result.hash}</span>
                                </li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <ul class="list-group mb-3">
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Upload Date:</span>
                                    <span class="text-muted">${new Date(result.upload_date).toLocaleString()}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>Risk Score:</span>
                                    <span class="badge ${Utils.getBadgeClass(result.manipulation_score)}">
                                        ${result.manipulation_score?.toFixed(2) || 'N/A'}
                                    </span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Custody Chain Functions
async function loadCustodyChain(evidenceId) {
    const timeline = document.getElementById('custodyTimeline');
    
    try {
        const response = await fetch(`/api/custody/${evidenceId}`);
        if (!response.ok) throw new Error('Failed to fetch custody data');
        
        const custodyData = await response.json();
        
        if (!custodyData.length) {
            timeline.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="fas fa-info-circle me-2"></i>
                    No custody records found
                </div>
            `;
            return;
        }
        
        timeline.innerHTML = custodyData.map(record => `
            <div class="custody-record">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <span class="badge ${Utils.getActionBadgeClass(record.action)} custody-badge">
                            <i class="${Utils.getActionIcon(record.action)} me-1"></i>
                            ${record.action}
                        </span>
                        <span class="custody-handler ms-2">${record.handler || 'System'}</span>
                    </div>
                    <span class="custody-timestamp">
                        ${new Date(record.timestamp).toLocaleString()}
                    </span>
                </div>
                <div class="text-muted small">
                    <i class="fas fa-map-marker-alt me-1"></i>
                    ${record.location || 'Local System'}
                </div>
                ${record.notes ? `
                    <div class="mt-2 text-muted small">
                        <i class="fas fa-comment-alt me-1"></i>
                        ${record.notes}
                    </div>
                ` : ''}
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading custody chain:', error);
        timeline.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load custody chain: ${error.message}
            </div>
        `;
    }
}

// Delete Functions
async function deleteEvidence(id, filename) {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
        try {
            const response = await fetch(`/api/evidence/delete/${id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                loadEvidence();
                Utils.showAlert('success', 'Evidence deleted successfully');
            } else {
                const data = await response.json();
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error deleting file:', error);
            Utils.showAlert('danger', 'Failed to delete file');
        }
    }
}

async function deleteEmail(id, subject) {
    if (confirm(`Are you sure you want to delete email "${subject}"?`)) {
        try {
            const response = await fetch(`/api/emails/delete/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                Utils.showAlert('success', 'Email deleted successfully');
                loadEmails(currentEmailPage); // Reload current page
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Failed to delete email');
            }
        } catch (error) {
            console.error('Error deleting email:', error);
            Utils.showAlert('danger', `Failed to delete email: ${error.message}`);
        }
    }
}

// Add these functions

function loadMemoryAnalysis() {
    // Update system memory info
    updateSystemMemory();
    // Load process list
    refreshProcesses();
}

function updateSystemMemory() {
    fetch('/api/memory/system')
        .then(response => response.json())
        .then(data => {
            const memInfo = document.getElementById('systemMemoryInfo');
            memInfo.innerHTML = `
                <div class="memory-stats">
                    <div class="mb-3">
                        <h5>RAM Usage</h5>
                        <div class="progress mb-2">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${data.memory_percent}%"
                                 aria-valuenow="${data.memory_percent}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                                ${data.memory_percent}%
                            </div>
                        </div>
                        <small class="text-muted">
                            ${data.available_memory}GB free of ${data.total_memory}GB
                        </small>
                    </div>
                    <div class="mt-3">
                        <h5>Swap Usage</h5>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-info" role="progressbar" 
                                 style="width: ${data.swap_percent}%"
                                 aria-valuenow="${data.swap_percent}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                                ${data.swap_percent}%
                            </div>
                        </div>
                        <small class="text-muted">
                            ${data.swap_free}GB free of ${data.total_memory}GB
                        </small>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error loading memory info:', error);
            document.getElementById('systemMemoryInfo').innerHTML = 
                '<div class="alert alert-danger">Error loading system memory information</div>';
        });
}

// Add auto-refresh for memory stats
setInterval(updateSystemMemory, 5000); // Update every 5 seconds

function refreshProcesses() {
    fetch('/api/memory/processes')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#processTable tbody');
            tbody.innerHTML = '';
            
            data.forEach((process, index) => {
                tbody.innerHTML += `
                    <tr ${index < 5 ? 'class="table-info"' : ''}>
                        <td>${process.pid}</td>
                        <td>${process.name}</td>
                        <td>${process.memory_usage} MB</td>
                        <td>
                            <button class="btn btn-sm btn-info" 
                                    onclick="analyzeProcess(${process.pid})">
                                <i class="fas fa-search"></i> Analyze
                            </button>
                        </td>
                    </tr>
                `;
            });
        });
}

function analyzeProcess(pid) {
    fetch(`/api/memory/analyze/${pid}`)
        .then(response => response.json())
        .then(data => {
            // Show process analysis in modal
            const modal = new bootstrap.Modal(document.getElementById('analysisModal'));
            document.getElementById('analysisContent').innerHTML = 
                `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            modal.show();
        });
}

// Add event listener for tab change
document.addEventListener('DOMContentLoaded', function() {
    // Listen for tab changes
    document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (event) {
            if (event.target.getAttribute('href') === '#memoryAnalysis') {
                loadMemoryAnalysis();
            }
        });
    });
});

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    loadEvidence();
    loadEmails();
    
    // File Upload Handler
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const fileInput = document.getElementById('fileInput');
        const analysisStatus = document.getElementById('analysisStatus');
        const statusText = document.getElementById('statusText');
        const spinner = form.querySelector('.spinner-border');
        const uploadText = form.querySelector('.upload-text');

        if (!fileInput.files.length) {
            Utils.showAlert('warning', 'Please select a file');
            return;
        }

        // Update UI for processing
        form.querySelector('button').disabled = true;
        spinner.classList.remove('d-none');
        uploadText.textContent = 'Analyzing...';
        analysisStatus.style.display = 'block';
        analysisStatus.className = 'analysis-status alert alert-info';

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                addResultRow(result.result);
                analysisCount++;
                document.getElementById('resultCount').textContent = `${analysisCount} files`;
                statusText.textContent = 'Analysis complete!';
                analysisStatus.classList.replace('alert-info', 'alert-success');
                Utils.showAlert('success', 'File analyzed successfully');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            analysisStatus.classList.replace('alert-info', 'alert-danger');
            statusText.textContent = `Error: ${error.message}`;
            Utils.showAlert('danger', `Analysis failed: ${error.message}`);
        } finally {
            form.querySelector('button').disabled = false;
            spinner.classList.add('d-none');
            uploadText.textContent = 'Analyze File';
            fileInput.value = '';
            setTimeout(() => {
                analysisStatus.style.display = 'none';
            }, 3000);
        }
    });
});

document.getElementById('imageUploadForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    const fileInput = document.getElementById('imageInput');
    
    if (fileInput.files.length === 0) {
        alert('Please select an image first');
        return;
    }
    
    formData.append('file', fileInput.files[0]);
    
    // Show loading state
    document.getElementById('analysisResult').innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Analyzing...</span>
            </div>
        </div>
    `;
    
    fetch('/api/analyze-image', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Display results
        document.getElementById('analysisResult').innerHTML = `
            <div class="alert ${data.is_tampered ? 'alert-danger' : 'alert-success'}">
                <h5>Analysis Results:</h5>
                <p>Status: ${data.is_tampered ? 'Potentially Tampered' : 'Likely Authentic'}</p>
                <p>Confidence: ${(data.confidence * 100).toFixed(2)}%</p>
                <p>Risk Level: ${data.risk_level}</p>
            </div>
        `;
        
        // Add to history
        addToHistory(fileInput.files[0].name, data);
    })
    .catch(error => {
        document.getElementById('analysisResult').innerHTML = `
            <div class="alert alert-danger">
                Error: ${error.message}
            </div>
        `;
    });
});

function addToHistory(filename, result) {
    const historyDiv = document.getElementById('analysisHistory');
    const historyItem = document.createElement('div');
    historyItem.className = 'mb-2 p-2 border rounded';
    historyItem.innerHTML = `
        <small class="text-muted">${new Date().toLocaleString()}</small>
        <p class="mb-1"><strong>${filename}</strong></p>
        <span class="badge ${result.is_tampered ? 'bg-danger' : 'bg-success'}">
            ${result.is_tampered ? 'Tampered' : 'Authentic'}
        </span>
    `;
    historyDiv.insertBefore(historyItem, historyDiv.firstChild);
}

async function showFileDetails(fileId) {
    const custodyTimeline = document.getElementById('custodyTimeline');
    custodyTimeline.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    
    try {
        const response = await fetch(`/api/custody/${fileId}`);
        if (!response.ok) throw new Error('Failed to fetch custody data');
        
        const custodyData = await response.json();
        
        if (!custodyData.length) {
            custodyTimeline.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No custody records found for this evidence.
                </div>`;
            return;
        }
        
        const timelineHtml = custodyData.map(record => `
            <div class="custody-record">
                <div class="custody-header">
                    <span class="badge bg-${getActionBadgeColor(record.action_type)}">
                        ${record.action_type}
                    </span>
                    <span class="custody-timestamp">
                        ${new Date(record.action_timestamp).toLocaleString()}
                    </span>
                </div>
                <div class="custody-details">
                    <div class="custody-handler">
                        <i class="fas fa-user me-2"></i>${record.handler}
                    </div>
                    <div class="custody-location">
                        <i class="fas fa-map-marker-alt me-2"></i>${record.location}
                    </div>
                    ${record.notes ? `
                        <div class="custody-notes">
                            <i class="fas fa-sticky-note me-2"></i>${record.notes}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        custodyTimeline.innerHTML = timelineHtml;
        
    } catch (error) {
        console.error('Error loading custody chain:', error);
        custodyTimeline.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load custody chain: ${error.message}
            </div>`;
    }
}

function getActionBadgeColor(action) {
    const colors = {
        'INITIAL_UPLOAD': 'primary',
        'ANALYSIS_STARTED': 'info',
        'ANALYSIS_COMPLETED': 'success',
        'ERROR': 'danger',
        'DEFAULT': 'secondary'
    };
    return colors[action] || colors['DEFAULT'];
}

// Update your document ready function
document.addEventListener('DOMContentLoaded', function() {
    // Set up image analysis form
    const imageAnalysisForm = document.getElementById('imageAnalysisForm');
    if (imageAnalysisForm) {
        imageAnalysisForm.addEventListener('submit', analyzeImage);
    }
    
    // Set up analysis type toggle
    const analysisTypeRadios = document.querySelectorAll('input[name="analysisType"]');
    if (analysisTypeRadios.length) {
        analysisTypeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                // Reset form and hide results when changing analysis type
                if (imageAnalysisForm) {
                    imageAnalysisForm.reset();
                }
                document.getElementById('tamperingResult').classList.add('d-none');
                document.getElementById('deepfakeResult').classList.add('d-none');
            });
        });
    }
});

// Update your analyzeImage function
async function analyzeImage(e) {
    e.preventDefault();
    
    // Get selected analysis type
    const analysisType = document.querySelector('input[name="analysisType"]:checked').value;
    
    const form = e.target;
    const fileInput = form.querySelector('input[type="file"]');
    
    if (!fileInput.files.length) {
        Utils.showAlert('warning', 'Please select an image to analyze');
        return;
    }
    
    const file = fileInput.files[0];
    if (!file.type.startsWith('image/')) {
        Utils.showAlert('warning', 'Please select a valid image file');
        return;
    }
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    
    try {
        // Determine which API endpoint to use
        const endpoint = analysisType === 'deepfake' ? 
            '/api/analyze/deepfake' : '/api/analyze/image';
        
        // Send to API
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Hide both result containers first
        document.getElementById('tamperingResult').classList.add('d-none');
        document.getElementById('deepfakeResult').classList.add('d-none');
        
        if (analysisType === 'deepfake') {
            displayDeepfakeResults(result);
        } else {
            // Your existing code to display tampering results
            displayTamperingResults(result);
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        Utils.showAlert('danger', `Error: ${error.message}`);
    } finally {
        // Reset form state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// Add this new function
function displayDeepfakeResults(result) {
    const resultDiv = document.getElementById('deepfakeResult');
    const alertDiv = document.getElementById('deepfakeAlert');
    const msgDiv = document.getElementById('deepfakeMessage');
    const confSpan = document.getElementById('deepfakeConfidence');
    const origImg = document.getElementById('deepfakeOriginal');
    const visImg = document.getElementById('deepfakeVisualization');
    
    // Update UI elements
    resultDiv.classList.remove('d-none');
    
    if (result.is_deepfake) {
        alertDiv.className = 'alert alert-danger';
        msgDiv.innerHTML = `<strong>Potential deepfake detected!</strong> ${result.message}`;
    } else {
        alertDiv.className = 'alert alert-success';
        msgDiv.innerHTML = `<strong>No deepfake detected.</strong> ${result.message}`;
    }
    
    confSpan.textContent = `${Math.round(result.confidence * 100)}%`;
    
    // Display images
    origImg.src = `/uploads/${result.filename}`;
    if (result.visualization_path) {
        // Extract the filename from the full path
        const visPath = result.visualization_path.split('/').pop();
        visImg.src = `/uploads/${visPath}`;
    }
    
    // Scroll to results
    resultDiv.scrollIntoView({ behavior: 'smooth' });
}

// Add this to your dashboard.js or create a new script file

// Deepfake detection handling
$(document).ready(function() {
    // Handle file input change
    $("#deepfake-file").change(function() {
        var fileName = $(this).val().split("\\").pop();
        $(this).next(".custom-file-label").html(fileName);
    });
    
    // Handle form submission
    $("#deepfake-form").submit(function(e) {
        e.preventDefault();
        
        // Check if file is selected
        if (!$("#deepfake-file").val()) {
            alert("Please select an image file first.");
            return;
        }
        
        // Create form data
        var formData = new FormData(this);
        
        // Reset results
        $("#deepfake-results-container").hide();
        $("#deepfake-analyze-btn").html('<i class="fas fa-spinner fa-spin"></i> Analyzing...');
        $("#deepfake-analyze-btn").prop("disabled", true);
        
        // Submit to API
        $.ajax({
            url: "/api/analyze/deepfake",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                displayDeepfakeResults(response);
            },
            error: function(xhr, status, error) {
                alert("Analysis failed: " + (xhr.responseJSON?.error || error));
                $("#deepfake-analyze-btn").html('<i class="fas fa-search"></i> Check for Deepfakes');
                $("#deepfake-analyze-btn").prop("disabled", false);
            }
        });
    });
    
    // Function to display results
    function displayDeepfakeResults(result) {
        // Enable the button again
        $("#deepfake-analyze-btn").html('<i class="fas fa-search"></i> Check for Deepfakes');
        $("#deepfake-analyze-btn").prop("disabled", false);
        
        // Show results container
        $("#deepfake-results-container").show();
        
        // Set result data
        const isFake = result.is_deepfake;
        const confidence = result.confidence * 100;
        
        // Update status
        $("#deepfake-status").text(isFake ? "DEEPFAKE DETECTED" : "LIKELY AUTHENTIC");
        
        // Set alert style
        $("#deepfake-alert").removeClass("alert-danger alert-success");
        if (isFake) {
            $("#deepfake-alert").addClass("alert-danger").text("This image appears to contain artificially manipulated face features.");
        } else {
            $("#deepfake-alert").addClass("alert-success").text("No deepfake manipulation detected in this image.");
        }
        
        // Update details
        $("#deepfake-confidence").text(confidence.toFixed(2) + "%");
        $("#deepfake-message").text(result.message || "Analysis complete");
        $("#deepfake-faces").text(result.faces_detected || "0");
        
        // Show visualization if available
        if (result.visualization_url) {
            $("#deepfake-visualization").attr("src", result.visualization_url);
            $("#deepfake-visualization").parent().show();
        } else {
            $("#deepfake-visualization").parent().hide();
        }
    }
});