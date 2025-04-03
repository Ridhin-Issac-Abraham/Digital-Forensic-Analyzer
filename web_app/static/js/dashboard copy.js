/* filepath: /f:/MSCAIML/S6/digital_forensics/web_app/static/js/dashboard.js */
let analysisCount = 0;
const modal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    loadEvidence();
    loadEmails();
});


// Copy all functions from script tag...

async function loadEvidence() {
    try {
        const response = await fetch('/api/evidence');
        const data = await response.json();
        
        if (Array.isArray(data)) {
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = '';
            data.forEach(result => addResultRow(result));
            analysisCount = data.length;
            document.getElementById('resultCount').textContent = 
                `${analysisCount} files`;
        }
    } catch (error) {
        console.error('Error loading evidence:', error);
    }
}

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
        alert('Please select a file');
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
            document.getElementById('resultCount').textContent = 
                `${analysisCount} files`;
            
            statusText.textContent = 'Analysis complete!';
            analysisStatus.classList.replace('alert-info', 'alert-success');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        analysisStatus.classList.replace('alert-info', 'alert-danger');
        statusText.textContent = `Error: ${error.message}`;
    } finally {
        // Reset form state
        form.querySelector('button').disabled = false;
        spinner.classList.add('d-none');
        uploadText.textContent = 'Analyze File';
        fileInput.value = '';
    }
});

// Email Functions
async function loadEmails() {
try {
const response = await fetch('/api/emails');
const data = await response.json();

if (data.status === 'success') {
    const tbody = document.getElementById('emailsBody');
    tbody.innerHTML = '';
    
    data.emails.forEach(email => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${email.sender}</td>
            <td>${email.subject}</td>
            <td>${new Date(email.date).toLocaleString()}</td>
            <td>
                <span class="badge bg-${email.security.spf ? 'success' : 'danger'}" title="SPF">SPF</span>
                <span class="badge bg-${email.security.dkim ? 'success' : 'danger'}" title="DKIM">DKIM</span>
                <span class="badge bg-${email.security.dmarc ? 'success' : 'danger'}" title="DMARC">DMARC</span>
            </td>
            <td>
                <span class="badge ${email.is_forged ? 'bg-danger' : 'bg-success'}">
                    ${email.is_forged ? 'Suspicious' : 'Valid'}
                </span>
                ${email.has_attachments ? '<span class="badge bg-warning ms-1">Attachment</span>' : ''}
            </td>
        `;
        tbody.appendChild(row);
    });
    
    document.getElementById('emailCount').textContent = `${data.emails.length} emails`;
} else {
    throw new Error(data.message);
}
} catch (error) {
showAlert('danger', `Failed to load emails: ${error.message}`);
}
}


// Add this function after loadEmails
function updateEmailTable(emails) {
    const tbody = document.getElementById('emailsBody');
    tbody.innerHTML = '';
    
    emails.forEach(email => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(email.date).toLocaleString()}</td>
            <td>${email.sender}</td>
            <td>${email.subject}</td>
            <td>
                <span class="badge bg-${email.security.spf ? 'success' : 'danger'}" title="SPF">SPF</span>
                <span class="badge bg-${email.security.dkim ? 'success' : 'danger'}" title="DKIM">DKIM</span>
                <span class="badge bg-${email.security.dmarc ? 'success' : 'danger'}" title="DMARC">DMARC</span>
            </td>
            <td>
                <span class="badge ${email.is_forged ? 'bg-danger' : 'bg-success'}">
                    ${email.is_forged ? 'Suspicious' : 'Valid'}
                </span>
                ${email.has_attachments ? '<span class="badge bg-warning ms-1">Attachment</span>' : ''}
            </td>
        `;
        tbody.appendChild(row);
    });
    
    document.getElementById('emailCount').textContent = `${emails.length} emails`;
}

// Then modify your loadEmails function to use updateEmailTable
async function loadEmails() {
    try {
        const response = await fetch('/api/emails');
        const data = await response.json();
        
        if (data.status === 'success') {
            updateEmailTable(data.emails);
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        showAlert('danger', `Failed to load emails: ${error.message}`);
    }
}

// Utility Functions
function addResultRow(result) {
const tbody = document.getElementById('resultsBody');
const row = document.createElement('tr');
row.innerHTML = `
<td>${result.filename}</td>
<td>${result.type}</td>
<td>${formatFileSize(result.size)}</td>
<td>
    <span class="badge ${getBadgeClass(result.manipulation_score)}">
        ${result.manipulation_score?.toFixed(2) || 'N/A'}
    </span>
</td>
<td>
    <button class="btn btn-sm btn-info me-2" 
            onclick='showDetails(${JSON.stringify(result)})'>
        Details
    </button>
    <button class="btn btn-sm btn-danger" 
            onclick='deleteEvidence(${result.id}, "${result.filename}")'>
        Delete
    </button>
</td>
`;
tbody.insertBefore(row, tbody.firstChild);
}

function showDetails(result) {
    const manipulationScore = parseFloat(result.manipulation_score) || 0;
    const status = getStatus(manipulationScore);
    const statusClass = getBadgeClass(manipulationScore);
    
    document.getElementById('fileDetailsContent').innerHTML = `
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h6>Basic Information</h6>
                    <ul class="list-group mb-3">
                        <li class="list-group-item">Name: ${result.filename}</li>
                        <li class="list-group-item">Type: ${result.type}</li>
                        <li class="list-group-item">Size: ${formatFileSize(result.size)}</li>
                        <li class="list-group-item">Hash: <span class="hash-text">${result.hash}</span></li>
                    </ul>
                    
                    <h6>Analysis Results</h6>
                    <ul class="list-group">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Manipulation Score: 
                            <span class="badge ${statusClass}">${manipulationScore.toFixed(2)}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Status: 
                            <span class="badge ${statusClass}">${status}</span>
                        </li>
                    </ul>
                </div>
            </div>
            ${result.preview ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Content Preview</h6>
                        <div class="border p-2 bg-light">
                            <pre class="mb-0">${result.preview}</pre>
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    loadCustodyChain(result.id);
    modal.show();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getBadgeClass(score) {
    if (!score) return 'bg-secondary';
    if (score < 0.3) return 'bg-success';
    if (score < 0.7) return 'bg-warning';
    return 'bg-danger';
}

function getStatus(score) {
    if (score === 0) return 'Original';
    if (score < 0.3) return 'Low Risk';
    if (score < 0.7) return 'Medium Risk';
    return 'High Risk';
}

function getSecurityBadgeClass(score) {
    if (score === 3) return 'bg-success';
    if (score === 2) return 'bg-warning';
    return 'bg-danger';
}
async function deleteEvidence(id, filename) {
if (confirm(`Are you sure you want to delete "${filename}"?`)) {
try {
    const response = await fetch(`/api/evidence/delete/${id}`, {
        method: 'DELETE'
    });
    if (response.ok) {
        loadEvidence(); // Reload the table
    } else {
        const data = await response.json();
        alert(`Error: ${data.error}`);
    }
} catch (error) {
    console.error('Error deleting file:', error);
    alert('Failed to delete file');
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
        loadEmails(); // Reload the table
    } else {
        const data = await response.json();
        alert(`Error: ${data.error}`);
    }
} catch (error) {
    console.error('Error deleting email:', error);
    alert('Failed to delete email');
}
}
}

/* filepath: /e:/MSCAIML/S6/digital_forensics/web_app/templates/dashboard.html */
async function loadCustodyChain(evidenceId) {
const timeline = document.getElementById('custodyTimeline');
const actionFilter = document.getElementById('actionFilter');
let custodyData = [];

try {
const response = await fetch(`/api/custody/${evidenceId}`);
if (!response.ok) throw new Error('Failed to fetch custody data');

custodyData = await response.json();

const renderTimeline = (filterValue = '') => {
    const filteredData = filterValue ? 
        custodyData.filter(record => record.action === filterValue) : 
        custodyData;
    
    if (filteredData.length === 0) {
        timeline.innerHTML = `
            <div class="text-center text-muted p-4">
                <i class="fas fa-info-circle me-2"></i>
                No custody records found
            </div>
        `;
        return;
    }
    
    timeline.innerHTML = filteredData.map(record => `
        <div class="custody-record">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <span class="badge ${getActionBadgeClass(record.action)} custody-badge">
                        <i class="${getActionIcon(record.action)} me-1"></i>
                        ${record.action}
                    </span>
                    <span class="custody-handler ms-2">${record.handler}</span>
                </div>
                <span class="custody-timestamp">
                    ${new Date(record.timestamp).toLocaleString()}
                </span>
            </div>
            <div class="text-muted small">
                <i class="fas fa-map-marker-alt me-1"></i>
                ${record.location}
            </div>
            ${record.notes ? `
                <div class="mt-2 text-muted small">
                    <i class="fas fa-comment-alt me-1"></i>
                    ${record.notes}
                </div>
            ` : ''}
        </div>
    `).join('');
};

// Initial render
renderTimeline();

// Add filter functionality
actionFilter.addEventListener('change', (e) => {
    renderTimeline(e.target.value);
});

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

//to refresh emails
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
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            Utils.showAlert('success', data.message);
            
            // Only reload if new emails were fetched
            if (data.refresh) {
                // Fetch updated email list
                const emailsResponse = await fetch('/api/emails');
                const emailsData = await emailsResponse.json();
                
                if (emailsData.status === 'success') {
                    updateEmailTable(emailsData.emails);
                }
            }
        } else {
            throw new Error(data.message);
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

function showAlert(type, message) {
const alertDiv = document.createElement('div');
alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
alertDiv.innerHTML = `
${message}
<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
`;

const emailTab = document.getElementById('emailEvidence');
emailTab.insertBefore(alertDiv, emailTab.firstChild);

// Auto dismiss after 5 seconds
setTimeout(() => {
alertDiv.remove();
}, 5000);
}


function getActionBadgeClass(action) {
const classes = {
'COLLECT': 'bg-success',
'ANALYZE': 'bg-primary',
'VIEW': 'bg-info',
'MODIFY': 'bg-warning'
};
return classes[action] || 'bg-secondary';
}

function getActionIcon(action) {
const icons = {
'COLLECT': 'fas fa-plus',
'ANALYZE': 'fas fa-microscope',
'VIEW': 'fas fa-eye',
'MODIFY': 'fas fa-edit'
};
return icons[action] || 'fas fa-dot-circle';
}


/* ... rest of your JavaScript code ... */