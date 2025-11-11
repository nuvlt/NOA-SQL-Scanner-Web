/**
 * NOA SQL Scanner Web - Main JavaScript
 */

// Global variables
let currentScanId = null;
let socket = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add loading animation to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }
        });
    });
});

// WebSocket connection for real-time updates
function initializeWebSocket(scanId) {
    currentScanId = scanId;
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
        socket.emit('subscribe_scan', { scan_id: scanId });
        addLog('Connected to scan session', 'info');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
        addLog('Disconnected from server', 'warning');
    });
    
    socket.on('scan_progress', function(data) {
        if (data.scan_id === currentScanId) {
            updateProgress(data.progress, data.message);
            addLog(data.message, 'info');
        }
    });
    
    socket.on('vulnerability_found', function(data) {
        if (data.scan_id === currentScanId) {
            addVulnerability(data.vulnerability);
            updateVulnCount();
            addLog('🚨 VULNERABILITY FOUND!', 'danger');
            showNotification('Vulnerability Detected!', 'A SQL injection vulnerability was found!', 'danger');
        }
    });
    
    socket.on('error', function(error) {
        console.error('WebSocket error:', error);
        addLog('Connection error occurred', 'danger');
    });
}

// Update progress bar
function updateProgress(percent, message) {
    const progressBar = document.getElementById('progress-bar');
    const progressMessage = document.getElementById('progress-message');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.textContent = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
        
        if (percent === 100) {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-success');
            
            const stopBtn = document.getElementById('stop-scan');
            if (stopBtn) {
                stopBtn.disabled = true;
            }
            
            showNotification('Scan Complete', 'The security scan has finished!', 'success');
        }
    }
    
    if (progressMessage) {
        progressMessage.textContent = message;
    }
}

// Add log entry
function addLog(message, type = 'info') {
    const logContent = document.getElementById('log-content');
    if (!logContent) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const colorClass = type === 'danger' ? 'text-danger' : 
                       type === 'warning' ? 'text-warning' : 
                       type === 'success' ? 'text-success' : 'text-info';
    
    const logEntry = document.createElement('div');
    logEntry.className = colorClass;
    logEntry.innerHTML = `[${timestamp}] ${escapeHtml(message)}`;
    
    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;
}

// Add vulnerability to list
function addVulnerability(vuln) {
    const section = document.getElementById('vulnerabilities-section');
    const list = document.getElementById('vulnerabilities-list');
    
    if (!section || !list) return;
    
    section.style.display = 'block';
    
    const item = document.createElement('div');
    item.className = 'list-group-item list-group-item-danger';
    item.innerHTML = `
        <div class="d-flex w-100 justify-content-between">
            <h6 class="mb-1">
                <i class="fas fa-bug"></i> ${escapeHtml(vuln.attack_type)} - ${escapeHtml(vuln.db_type)}
            </h6>
            <small>${new Date().toLocaleTimeString()}</small>
        </div>
        <p class="mb-1"><strong>URL:</strong> <code>${escapeHtml(vuln.url)}</code></p>
        <p class="mb-1"><strong>Parameter:</strong> <code>${escapeHtml(vuln.parameter)}</code></p>
        <small><strong>Payload:</strong> <code>${escapeHtml(vuln.payload)}</code></small>
    `;
    
    list.insertBefore(item, list.firstChild);
}

// Update vulnerability count
function updateVulnCount() {
    const vulnCount = document.getElementById('vulns-found');
    if (!vulnCount) return;
    
    const count = document.querySelectorAll('#vulnerabilities-list .list-group-item').length;
    vulnCount.textContent = count;
    
    if (count > 0) {
        vulnCount.classList.add('text-danger', 'fw-bold');
    }
}

// Show notification
function showNotification(title, message, type = 'info') {
    // Check if browser supports notifications
    if (!("Notification" in window)) {
        console.log('This browser does not support notifications');
        return;
    }
    
    // Check notification permission
    if (Notification.permission === "granted") {
        new Notification(title, {
            body: message,
            icon: '/static/img/logo.png'
        });
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                new Notification(title, {
                    body: message,
                    icon: '/static/img/logo.png'
                });
            }
        });
    }
    
    // Also show toast notification
    showToast(title, message, type);
}

// Show toast notification
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'danger' ? 'bg-danger' : 
                    type === 'warning' ? 'bg-warning' : 
                    type === 'success' ? 'bg-success' : 'bg-info';
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${escapeHtml(title)}</strong><br>
                    ${escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Create toast container
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Stop scan
function stopScan(scanId) {
    if (!confirm('Are you sure you want to stop this scan?')) {
        return;
    }
    
    fetch(`/api/scan/stop/${scanId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        addLog('Scan stopped by user', 'warning');
        showNotification('Scan Stopped', 'The scan has been stopped.', 'warning');
        
        const stopBtn = document.getElementById('stop-scan');
        if (stopBtn) {
            stopBtn.disabled = true;
        }
    })
    .catch(error => {
        console.error('Error stopping scan:', error);
        showNotification('Error', 'Failed to stop scan.', 'danger');
    });
}

// Poll for scan status
function pollScanStatus(scanId, interval = 2000) {
    setInterval(function() {
        fetch(`/api/scan/status/${scanId}`)
            .then(response => response.json())
            .then(data => {
                if (data) {
                    // Update stats
                    const urlsFound = document.getElementById('urls-found');
                    const urlsScanned = document.getElementById('urls-scanned');
                    
                    if (urlsFound) urlsFound.textContent = data.urls_found || 0;
                    if (urlsScanned) urlsScanned.textContent = data.urls_scanned || 0;
                    
                    // If scan is complete, reload page after 3 seconds
                    if (data.status === 'completed' && !sessionStorage.getItem('scan_complete_' + scanId)) {
                        sessionStorage.setItem('scan_complete_' + scanId, 'true');
                        setTimeout(function() {
                            window.location.href = `/report/${scanId}`;
                        }, 3000);
                    }
                }
            })
            .catch(error => {
                console.error('Error polling scan status:', error);
            });
    }, interval);
}

// Utility: Escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Utility: Copy to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied', 'Text copied to clipboard!', 'success');
        });
    } else {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Copied', 'Text copied to clipboard!', 'success');
    }
}

// Export functions to global scope
window.initializeWebSocket = initializeWebSocket;
window.stopScan = stopScan;
window.pollScanStatus = pollScanStatus;
window.copyToClipboard = copyToClipboard;
