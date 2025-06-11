/**
 * Sessions Management JavaScript
 * Handles session scheduling, cancellation, rescheduling, and availability checking
 */

// Global variables
let selectedTutorId = null;
let selectedDate = null;
let availableSlots = [];
let scheduleModal = null;

// Initialize sessions page
document.addEventListener('DOMContentLoaded', function () {
    initializeDatePicker();
    initializeEventListeners();
    loadInitialData();
});

/**
 * Initialize date picker with minimum date as today
 */
function initializeDatePicker() {
    const dateInput = document.getElementById('sessionDate');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;

        // Set max date to 60 days from now
        const maxDate = new Date();
        maxDate.setDate(maxDate.getDate() + 60);
        dateInput.max = maxDate.toISOString().split('T')[0];
    }
}

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Course selection change
    const courseSelect = document.getElementById('courseSelect');
    if (courseSelect) {
        courseSelect.addEventListener('change', loadTutorsForCourse);
    }

    // Tutor selection change
    const tutorSelect = document.getElementById('tutorSelect');
    if (tutorSelect) {
        tutorSelect.addEventListener('change', onTutorSelected);
    }

    // Date selection change
    const dateInput = document.getElementById('sessionDate');
    if (dateInput) {
        dateInput.addEventListener('change', onDateSelected);
    }
}

/**
 * Load initial data for the page
 */
function loadInitialData() {
    // Load available courses and tutors
    loadTutorsForCourse();
}

/**
 * Open schedule session modal
 */
function openScheduleModal(tutorId = null, courseId = null) {
    // Initialize modal if not already done
    if (!scheduleModal) {
        scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
    }

    // Reset form
    document.getElementById('scheduleForm').reset();
    clearAvailabilityPreview();

    // Pre-fill if parameters provided
    if (courseId) {
        document.getElementById('courseSelect').value = courseId;
        loadTutorsForCourse();
    }
    if (tutorId) {
        setTimeout(() => {
            document.getElementById('tutorSelect').value = tutorId;
            onTutorSelected();
        }, 100);
    }

    scheduleModal.show();
}

/**
 * Load tutors based on selected course
 */
function loadTutorsForCourse() {
    const courseId = document.getElementById('courseSelect').value;
    const tutorSelect = document.getElementById('tutorSelect');

    if (!courseId) {
        tutorSelect.innerHTML = '<option value="">Select a course first</option>';
        clearAvailabilityPreview();
        return;
    }

    // Show loading
    tutorSelect.innerHTML = '<option value="">Loading tutors...</option>';
    tutorSelect.disabled = true;

    // Fetch tutors for the course
    fetch(`/student/api/tutors-for-course/${courseId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                tutorSelect.innerHTML = '<option value="">Select a tutor</option>';
                data.tutors.forEach(tutor => {
                    const option = document.createElement('option');
                    option.value = tutor.id;
                    option.textContent = `${tutor.username} (${tutor.subjects || 'General'})`;
                    option.dataset.rating = tutor.avg_rating || '0';
                    tutorSelect.appendChild(option);
                });
            } else {
                tutorSelect.innerHTML = '<option value="">No tutors available</option>';
                showSessionsNotification('No tutors found for this course', 'warning');
            }
        })
        .catch(error => {
            console.error('Error loading tutors:', error);
            tutorSelect.innerHTML = '<option value="">Error loading tutors</option>';
            showSessionsNotification('Error loading tutors', 'error');
        })
        .finally(() => {
            tutorSelect.disabled = false;
        });
}

/**
 * Handle tutor selection
 */
function onTutorSelected() {
    const tutorSelect = document.getElementById('tutorSelect');
    selectedTutorId = tutorSelect.value;

    if (selectedTutorId && selectedDate) {
        loadAvailableSlots();
    } else {
        clearAvailabilityPreview();
    }
}

/**
 * Handle date selection
 */
function onDateSelected() {
    const dateInput = document.getElementById('sessionDate');
    selectedDate = dateInput.value;

    if (selectedTutorId && selectedDate) {
        loadAvailableSlots();
    } else {
        clearAvailabilityPreview();
    }
}

/**
 * Load available time slots for selected tutor and date
 */
function loadAvailableSlots() {
    if (!selectedTutorId || !selectedDate) return;

    const slotsSelect = document.getElementById('availableSlots');

    // Show loading
    slotsSelect.innerHTML = '<option value="">Loading available slots...</option>';
    slotsSelect.disabled = true;

    // Fetch available slots
    fetch(`/student/api/tutor-availability?tutor_id=${selectedTutorId}&date=${selectedDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.slots && data.slots.length > 0) {
                availableSlots = data.slots;
                populateAvailableSlots(data.slots);
                showAvailabilityPreview(data.slots);
            } else {
                slotsSelect.innerHTML = '<option value="">No slots available</option>';
                showSessionsNotification(data.message || 'No available slots for this date', 'info');
                clearAvailabilityPreview();
            }
        })
        .catch(error => {
            console.error('Error loading slots:', error);
            slotsSelect.innerHTML = '<option value="">Error loading slots</option>';
            showSessionsNotification('Error loading available slots', 'error');
            clearAvailabilityPreview();
        })
        .finally(() => {
            slotsSelect.disabled = false;
        });
}

/**
 * Populate available slots dropdown
 */
function populateAvailableSlots(slots) {
    const slotsSelect = document.getElementById('availableSlots');

    if (slots.length === 0) {
        slotsSelect.innerHTML = '<option value="">No slots available</option>';
        return;
    }

    slotsSelect.innerHTML = '<option value="">Select a time slot</option>';

    slots.forEach(slot => {
        const option = document.createElement('option');
        option.value = slot;
        option.textContent = formatTime(slot);
        slotsSelect.appendChild(option);
    });
}

/**
 * Show availability preview
 */
function showAvailabilityPreview(slots) {
    const previewDiv = document.getElementById('tutorAvailabilityPreview');
    const slotsDiv = document.getElementById('availabilitySlots');

    if (slots.length === 0) {
        previewDiv.classList.add('d-none');
        return;
    }

    let slotsHtml = '';
    slots.forEach(slot => {
        slotsHtml += `
            <span class="badge bg-success me-2 mb-2">
                ${formatTime(slot)}
            </span>
        `;
    });

    slotsDiv.innerHTML = slotsHtml;
    previewDiv.classList.remove('d-none');
}

/**
 * Clear availability preview
 */
function clearAvailabilityPreview() {
    const previewDiv = document.getElementById('tutorAvailabilityPreview');
    const slotsSelect = document.getElementById('availableSlots');

    previewDiv.classList.add('d-none');
    slotsSelect.innerHTML = '<option value="">Select date and tutor first</option>';
}

/**
 * Format time for display
 */
function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

/**
 * Submit schedule form (Sessions page specific version)
 */
function submitScheduleForm() {
    const form = document.getElementById('scheduleForm');
    const submitBtn = document.getElementById('scheduleSubmitBtn');

    // Validate form
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = {
        courseId: document.getElementById('courseSelect').value,
        tutorId: document.getElementById('tutorSelect').value,
        date: document.getElementById('sessionDate').value,
        time: document.getElementById('availableSlots').value,
        duration: document.getElementById('sessionDuration').value,
        notes: document.getElementById('sessionNotes').value
    };

    // Validate required fields
    if (!formData.courseId || !formData.tutorId || !formData.date || !formData.time) {
        showSessionsNotification('Please fill in all required fields', 'warning');
        return;
    }

    // Show loading
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Scheduling...';
    submitBtn.disabled = true;

    // Submit session request
    fetch('/student/api/schedule-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(formData)
    })
        .then(response => {
            console.log('Schedule session response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Session creation response:', data);
            if (data.success) {
                alert('Session scheduled successfully!');

                // Close modal
                if (scheduleModal) {
                    scheduleModal.hide();
                }

                // Clear form
                form.reset();
                clearAvailabilityPreview();

                // Force page reload
                setTimeout(() => {
                    console.log('Reloading page...');
                    window.location.reload(true);
                }, 1000);
            } else {
                alert(data.error || 'Failed to schedule session');
            }
        })
        .catch(error => {
            console.error('Error scheduling session:', error);
            alert('An error occurred while scheduling the session');
        })
        .finally(() => {
            // Restore button
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
}

/**
 * Cancel session - SIMPLIFIED VERSION
 */
function cancelSession(sessionId) {
    console.log('Attempting to cancel session:', sessionId);

    if (!confirm('Are you sure you want to cancel this session? This action cannot be undone.')) {
        return;
    }

    console.log('Cancelling session...');

    fetch(`/student/api/cancel-session/${sessionId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            if (data.success) {
                console.log('Session cancelled successfully');
                alert('Session cancelled successfully');

                // Force page reload
                setTimeout(() => {
                    console.log('Reloading page after cancellation...');
                    window.location.reload(true);
                }, 500);
            } else {
                console.error('Failed to cancel session:', data.error);
                alert(data.error || 'Failed to cancel session');
            }
        })
        .catch(error => {
            console.error('Error cancelling session:', error);
            alert('An error occurred while cancelling the session');
        });
}

/**
 * Sessions-specific notification function
 */
function showSessionsNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);

    // Create notification directly
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 1050; min-width: 300px; max-width: 400px;';

    // Get icon for type
    let icon = 'bell';
    switch (type) {
        case 'success': icon = 'check-circle'; break;
        case 'error': case 'danger': icon = 'exclamation-triangle'; break;
        case 'warning': icon = 'exclamation-circle'; break;
        case 'info': icon = 'info-circle'; break;
    }

    alertDiv.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Make functions globally available
window.submitScheduleForm = submitScheduleForm;
window.cancelSession = cancelSession;
window.openScheduleModal = openScheduleModal;

// Override main.js functions
document.addEventListener('DOMContentLoaded', function () {
    console.log('Sessions.js loaded - functions available globally');
});
