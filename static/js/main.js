// Learning Hub JavaScript functionality

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    initializeTooltips();

    // Initialize progress rings
    initializeProgressRings();

    // Initialize search functionality
    initializeSearch();

    // Auto-hide alerts
    autoHideAlerts();

    // Set up auto-refresh for dashboard data
    if (window.location.pathname.includes('dashboard')) {
        setInterval(refreshDashboardData, 30000); // Refresh every 30 seconds
    }

    // Add fade-in animation to main content
    document.querySelector('.main-content')?.classList.add('fade-in');
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Progress ring animation
function initializeProgressRings() {
    const rings = document.querySelectorAll('.course-progress-ring');
    rings.forEach(ring => {
        const progress = ring.dataset.progress || 0;
        ring.style.setProperty('--progress', progress);

        // Animate the ring
        setTimeout(() => {
            ring.style.transform = 'scale(1.1)';
            setTimeout(() => {
                ring.style.transform = 'scale(1)';
            }, 200);
        }, 300);
    });
}

// Auto-hide alerts after 5 seconds
function autoHideAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (bootstrap.Alert.getInstance(alert)) {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                bsAlert.close();
            }
        });
    }, 5000);
}

// Update progress function
function updateProgress(courseId, lessonId = null) {
    const progressElement = document.querySelector(`[data-course="${courseId}"] .progress-bar`);
    if (!progressElement) {
        showNotification('Progress element not found', 'error');
        return;
    }

    const currentProgress = parseInt(progressElement.getAttribute('aria-valuenow')) || 0;
    const newProgress = Math.min(currentProgress + 10, 100);

    // Show loading spinner
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="loading-spinner"></span> Updating...';
    button.disabled = true;

    fetch('/api/update_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            course_id: courseId,
            lesson_id: lessonId,
            progress: newProgress
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Animate progress bar update
            progressElement.style.width = newProgress + '%';
            progressElement.setAttribute('aria-valuenow', newProgress);

            // Update progress text
            const progressText = document.querySelector(`[data-course="${courseId}"] .progress-text`);
            if (progressText) {
                progressText.textContent = newProgress + '% Complete';
            }

            // Update progress ring if exists
            const progressRing = document.querySelector(`[data-course="${courseId}"] .course-progress-ring`);
            if (progressRing) {
                progressRing.style.setProperty('--progress', newProgress);
            }

            // Show success message
            showNotification('Progress updated successfully!', 'success');

            // Check if course is completed
            if (newProgress === 100) {
                showNotification('🎉 Congratulations! Course completed!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }
        } else {
            showNotification('Failed to update progress', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while updating progress', 'error');
    })
    .finally(() => {
        // Restore button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 1050; min-width: 300px; max-width: 400px;';
    alertDiv.innerHTML = `
        <i class="fas fa-${getIconForType(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Animate in
    setTimeout(() => {
        alertDiv.classList.add('slide-in-left');
    }, 100);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.add('fade');
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }
    }, 5000);
}

// Get icon for notification type
function getIconForType(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error': case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'bell';
    }
}

// Refresh dashboard data
function refreshDashboardData() {
    // Show refresh indicator
    const refreshIndicator = document.createElement('div');
    refreshIndicator.className = 'position-fixed top-0 end-0 p-3';
    refreshIndicator.style.zIndex = '1055';
    refreshIndicator.innerHTML = `
        <div class="bg-primary text-white px-3 py-2 rounded shadow">
            <small><i class="fas fa-sync-alt fa-spin me-2"></i>Refreshing...</small>
        </div>
    `;
    document.body.appendChild(refreshIndicator);

    // In a real application, you would fetch new data here
    // For now, we'll just simulate a refresh
    setTimeout(() => {
        refreshIndicator.remove();

        // Update timestamps or other dynamic content
        updateTimestamps();
    }, 1000);
}

// Update timestamps to show relative time
function updateTimestamps() {
    const timestamps = document.querySelectorAll('[data-timestamp]');
    timestamps.forEach(element => {
        const timestamp = element.dataset.timestamp;
        const relativeTime = getRelativeTime(new Date(timestamp));
        element.textContent = relativeTime;
    });
}

// Get relative time string
function getRelativeTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
}

// Schedule session modal
function openScheduleModal(tutorId = null, courseId = null) {
    // Create modal HTML
    const modalHTML = `
        <div class="modal fade" id="scheduleModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-calendar-plus me-2"></i>Schedule Session
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="scheduleForm">
                            <div class="mb-3">
                                <label for="courseSelect" class="form-label">Course</label>
                                <select class="form-select" id="courseSelect" required>
                                    <option value="">Select a course</option>
                                    <option value="1">Introduction to Python Programming</option>
                                    <option value="2">Advanced Mathematics</option>
                                    <option value="3">English Literature</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="tutorSelect" class="form-label">Tutor</label>
                                <select class="form-select" id="tutorSelect" required>
                                    <option value="">Select a tutor</option>
                                    <option value="3">Jane Smith (Python, Math)</option>
                                    <option value="7">Mike Johnson (Web Development)</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="sessionDate" class="form-label">Date</label>
                                <input type="date" class="form-control" id="sessionDate" required>
                            </div>
                            <div class="mb-3">
                                <label for="sessionTime" class="form-label">Time</label>
                                <input type="time" class="form-control" id="sessionTime" required>
                            </div>
                            <div class="mb-3">
                                <label for="sessionNotes" class="form-label">Notes (Optional)</label>
                                <textarea class="form-control" id="sessionNotes" rows="3"
                                         placeholder="Any specific topics or requirements..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="submitScheduleForm()">
                            <i class="fas fa-calendar-check me-2"></i>Schedule Session
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('scheduleModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Set minimum date to today
    const dateInput = document.getElementById('sessionDate');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;

    // Pre-fill if parameters provided
    if (courseId) {
        document.getElementById('courseSelect').value = courseId;
    }
    if (tutorId) {
        document.getElementById('tutorSelect').value = tutorId;
    }

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
    modal.show();
}

// Submit schedule form
function submitScheduleForm() {
    if (!validateForm('scheduleForm')) {
        showNotification('Please fill in all required fields', 'warning');
        return;
    }

    const formData = {
        course_id: document.getElementById('courseSelect').value,
        tutor_id: document.getElementById('tutorSelect').value,
        date: document.getElementById('sessionDate').value,
        time: document.getElementById('sessionTime').value,
        notes: document.getElementById('sessionNotes').value
    };

    // Show loading
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="loading-spinner"></span> Scheduling...';
    submitBtn.disabled = true;

    // Simulate API call (in real app, this would be an actual API call)
    setTimeout(() => {
        showNotification('Session scheduled successfully!', 'success');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleModal'));
        modal.hide();

        // Reset button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;

        // Optionally reload page or update UI
        setTimeout(() => {
            location.reload();
        }, 1500);
    }, 1500);
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const searchableItems = document.querySelectorAll('[data-searchable]');

            searchableItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                const parent = item.closest('.card, .list-group-item, tr');

                if (text.includes(searchTerm)) {
                    parent.style.display = '';
                    parent.classList.add('fade-in');
                } else {
                    parent.style.display = 'none';
                    parent.classList.remove('fade-in');
                }
            });

            // Show no results message if needed
            const visibleItems = document.querySelectorAll('[data-searchable]').length;
            const hiddenItems = document.querySelectorAll('[data-searchable]').filter(item =>
                item.closest('.card, .list-group-item, tr').style.display === 'none'
            ).length;

            if (searchTerm && visibleItems === hiddenItems) {
                showNoResultsMessage();
            } else {
                hideNoResultsMessage();
            }
        });
    }
}

// Show no results message
function showNoResultsMessage() {
    const existingMessage = document.getElementById('noResultsMessage');
    if (existingMessage) return;

    const message = document.createElement('div');
    message.id = 'noResultsMessage';
    message.className = 'alert alert-info text-center mt-3';
    message.innerHTML = '<i class="fas fa-search me-2"></i>No results found';

    const searchContainer = document.querySelector('.main-content');
    if (searchContainer) {
        searchContainer.appendChild(message);
    }
}

// Hide no results message
function hideNoResultsMessage() {
    const message = document.getElementById('noResultsMessage');
    if (message) {
        message.remove();
    }
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;

            // Add error message if not exists
            if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('invalid-feedback')) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                errorDiv.textContent = 'This field is required';
                input.parentNode.appendChild(errorDiv);
            }
        } else {
            input.classList.remove('is-invalid');

            // Remove error message
            const errorDiv = input.nextElementSibling;
            if (errorDiv && errorDiv.classList.contains('invalid-feedback')) {
                errorDiv.remove();
            }
        }
    });

    return isValid;
}

// Export functionality for reports
function exportData(format, data) {
    if (format === 'csv') {
        const csv = convertToCSV(data);
        downloadFile(csv, 'learning_hub_data.csv', 'text/csv');
    } else if (format === 'json') {
        const json = JSON.stringify(data, null, 2);
        downloadFile(json, 'learning_hub_data.json', 'application/json');
    }

    showNotification(`Data exported as ${format.toUpperCase()}`, 'success');
}

function convertToCSV(data) {
    if (!data.length) return '';

    const headers = Object.keys(data[0]);
    const csv = [
        headers.join(','),
        ...data.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
    ].join('\n');

    return csv;
}

function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Sidebar toggle for mobile
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('show');
    }
}

// Add mobile menu button if needed
function addMobileMenuButton() {
    if (window.innerWidth <= 768) {
        const navbar = document.querySelector('.navbar .container-fluid');
        if (navbar && !document.getElementById('mobileMenuBtn')) {
            const menuBtn = document.createElement('button');
            menuBtn.id = 'mobileMenuBtn';
            menuBtn.className = 'btn btn-outline-primary d-md-none';
            menuBtn.innerHTML = '<i class="fas fa-bars"></i>';
            menuBtn.onclick = toggleSidebar;

            navbar.insertBefore(menuBtn, navbar.firstChild);
        }
    }
}

// Handle window resize
window.addEventListener('resize', function() {
    addMobileMenuButton();

    // Hide sidebar on desktop
    if (window.innerWidth > 768) {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.remove('show');
        }
    }
});

// Initialize mobile menu button
addMobileMenuButton();

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading state to buttons
function addLoadingState(button, text = 'Loading...') {
    const originalText = button.innerHTML;
    button.innerHTML = `<span class="loading-spinner"></span> ${text}`;
    button.disabled = true;

    return function() {
        button.innerHTML = originalText;
        button.disabled = false;
    };
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape to close modals
    if (e.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Analytics tracking (placeholder)
function trackEvent(category, action, label = '') {
    // In a real application, you would send this to your analytics service
    console.log('Event tracked:', { category, action, label });
}

// Track navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function() {
        trackEvent('Navigation', 'Click', this.textContent.trim());
    });
});

// Track button clicks
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function() {
        trackEvent('Button', 'Click', this.textContent.trim());
    });
});

// Console welcome message
console.log(`
🎓 Learning Hub - School Project
📚 Full-stack Flask application
🔧 Built with Flask, SQLite, Bootstrap 5
👨‍💻 Ready for demonstration!

Demo accounts:
- Student: john.doe@student.edu
- Tutor: jane.smith@tutor.edu
- Admin: admin@learninghub.edu
- Password: password123

Happy learning! 🚀
`);