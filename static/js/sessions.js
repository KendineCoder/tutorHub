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
                console.log('No tutors found for this course');
            }
        })
        .catch(error => {
            console.error('Error loading tutors:', error);
            tutorSelect.innerHTML = '<option value="">Error loading tutors</option>';
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
                console.log(data.message || 'No available slots for this date');
                clearAvailabilityPreview();
            }
        })
        .catch(error => {
            console.error('Error loading slots:', error);
            slotsSelect.innerHTML = '<option value="">Error loading slots</option>';
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
    };    // Validate required fields
    if (!formData.courseId || !formData.tutorId || !formData.date || !formData.time) {
        alert('Please fill in all required fields');
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
 * End session - Mark session as completed
 */
function endSession(sessionId) {
    console.log('Attempting to end session:', sessionId);

    if (!confirm('Are you sure you want to end this session? This will mark it as completed.')) {
        return;
    }

    console.log('Ending session...');

    fetch(`/student/api/end_session/${sessionId}`, {
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
                console.log('Session ended successfully');
                alert('Session ended successfully and moved to history');

                // Force page reload
                setTimeout(() => {
                    console.log('Reloading page after ending session...');
                    window.location.reload(true);
                }, 500);
            } else {
                console.error('Failed to end session:', data.error);
                alert(data.error || 'Failed to end session');
            }
        })
        .catch(error => {
            console.error('Error ending session:', error);
            alert('An error occurred while ending the session');
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

/**
 * View session details
 */
function viewSessionDetails(sessionId) {
    console.log('Viewing session details for:', sessionId);

    fetch(`/student/api/session-details/${sessionId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.session) {
                const session = data.session;

                // Create a modal to show session details
                const modalHtml = `
                    <div class="modal fade" id="sessionDetailsModal" tabindex="-1">
                        <div class="modal-dialog modal-lg">
                            <div class="modal-content">
                                <div class="modal-header bg-info text-white">
                                    <h5 class="modal-title">
                                        <i class="fas fa-info-circle me-2"></i>Session Details
                                    </h5>
                                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <h6><i class="fas fa-chalkboard-teacher me-2"></i>Tutor Information</h6>
                                            <p><strong>Name:</strong> ${session.tutor_name}</p>
                                            <p><strong>Email:</strong> ${session.tutor_email || 'N/A'}</p>
                                        </div>
                                        <div class="col-md-6">
                                            <h6><i class="fas fa-book me-2"></i>Course Information</h6>
                                            <p><strong>Course:</strong> ${session.course_title || 'General Session'}</p>
                                            <p><strong>Description:</strong> ${session.course_description || 'N/A'}</p>
                                        </div>
                                    </div>
                                    <hr>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <h6><i class="fas fa-calendar me-2"></i>Session Schedule</h6>
                                            <p><strong>Date:</strong> ${session.scheduled_date}</p>
                                            <p><strong>Time:</strong> ${session.scheduled_time}</p>
                                            <p><strong>Duration:</strong> ${session.duration || 60} minutes</p>
                                        </div>
                                        <div class="col-md-6">
                                            <h6><i class="fas fa-info me-2"></i>Status</h6>
                                            <p><strong>Status:</strong> <span class="badge bg-${session.status === 'completed' ? 'success' : session.status === 'cancelled' ? 'danger' : 'secondary'}">${session.status.charAt(0).toUpperCase() + session.status.slice(1)}</span></p>
                                            ${session.completed_at ? `<p><strong>Completed:</strong> ${session.completed_at}</p>` : ''}
                                        </div>
                                    </div>
                                    ${session.notes && session.notes.length > 0 ? `
                                        <hr>
                                        <h6><i class="fas fa-sticky-note me-2"></i>Session Notes</h6>
                                        ${session.notes.map(note => `<p class="border-start border-3 ps-3 mb-2">${note.content}</p>`).join('')}
                                    ` : ''}
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                // Remove existing modal if any
                const existingModal = document.getElementById('sessionDetailsModal');
                if (existingModal) {
                    existingModal.remove();
                }

                // Add modal to DOM and show it
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                const modal = new bootstrap.Modal(document.getElementById('sessionDetailsModal'));
                modal.show();
            } else {
                alert('Failed to load session details');
            }
        })
        .catch(error => {
            console.error('Error loading session details:', error);
            alert('An error occurred while loading session details');
        });
}

/**
 * Rate a completed session
 */
function rateSession(sessionId) {
    console.log('Rating session:', sessionId);

    // Create rating modal
    const modalHtml = `
        <div class="modal fade" id="rateSessionModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-star me-2"></i>Rate This Session
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="ratingForm">
                            <div class="mb-3">
                                <label class="form-label">Rating (1-5 stars)</label>
                                <div class="rating-input d-flex gap-2 justify-content-center mb-3">
                                    ${[1, 2, 3, 4, 5].map(i => `
                                        <i class="fas fa-star rating-star text-muted" 
                                           data-rating="${i}" 
                                           style="font-size: 2rem; cursor: pointer;"
                                           onclick="setRating(${i})"></i>
                                    `).join('')}
                                </div>
                                <input type="hidden" id="selectedRating" value="">
                            </div>
                            <div class="mb-3">
                                <label for="reviewText" class="form-label">Review (Optional)</label>
                                <textarea class="form-control" id="reviewText" rows="3" 
                                         placeholder="Share your experience with this session..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-warning" onclick="submitRating(${sessionId})" id="submitRatingBtn">
                            <i class="fas fa-star me-2"></i>Submit Rating
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('rateSessionModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to DOM and show it
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('rateSessionModal'));
    modal.show();
}

/**
 * Set rating stars
 */
function setRating(rating) {
    document.getElementById('selectedRating').value = rating;

    // Update star display
    const stars = document.querySelectorAll('.rating-star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.remove('text-muted');
            star.classList.add('text-warning');
        } else {
            star.classList.remove('text-warning');
            star.classList.add('text-muted');
        }
    });
}

/**
 * Submit rating
 */
function submitRating(sessionId) {
    const rating = document.getElementById('selectedRating').value;
    const review = document.getElementById('reviewText').value;

    if (!rating) {
        alert('Please select a rating');
        return;
    }

    const submitBtn = document.getElementById('submitRatingBtn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
    submitBtn.disabled = true;

    fetch(`/student/api/rate-session/${sessionId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            rating: parseInt(rating),
            review: review
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Rating submitted successfully!');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('rateSessionModal'));
                modal.hide();

                // Update the rating display in the table without reloading
                updateRatingDisplay(sessionId, parseInt(rating));

                // Optional: Show a brief success message
                showSessionsNotification('Rating submitted successfully!', 'success');
            } else {
                alert(data.error || 'Failed to submit rating');
            }
        })
        .catch(error => {
            console.error('Error submitting rating:', error);
            alert('An error occurred while submitting rating');
        })
        .finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
}

/**
 * Update rating display in the session history table
 */
function updateRatingDisplay(sessionId, rating) {
    // Find the row for this session
    const rows = document.querySelectorAll('#history tbody tr');

    rows.forEach(row => {
        const buttons = row.querySelectorAll('button[onclick*="viewSessionDetails"]');
        if (buttons.length > 0) {
            const onclickAttr = buttons[0].getAttribute('onclick');
            const extractedSessionId = onclickAttr.match(/\d+/);

            if (extractedSessionId && parseInt(extractedSessionId[0]) === sessionId) {
                // Find the rating cell (6th column, 0-indexed)
                const cells = row.querySelectorAll('td');
                if (cells.length >= 6) {
                    const ratingCell = cells[5]; // Rating column

                    // Update the rating display
                    let starsHtml = '<div class="rating">';
                    for (let i = 0; i < 5; i++) {
                        const starClass = i < rating ? 'text-warning' : 'text-muted';
                        starsHtml += `<i class="fas fa-star ${starClass}"></i>`;
                    }
                    starsHtml += '</div>';

                    ratingCell.innerHTML = starsHtml;
                }
                return;
            }
        }
    });
}

/**
 * Book again with the same tutor
 */
function bookAgain(tutorId, courseId) {
    console.log('Booking again with tutor:', tutorId, 'course:', courseId);

    // Open the schedule modal with pre-filled tutor and course
    if (typeof openScheduleModal === 'function') {
        openScheduleModal(tutorId, courseId);
    } else {
        // Fallback - redirect to sessions page
        window.location.href = `/student/sessions?tutor=${tutorId}&course=${courseId || ''}`;
    }
}

/**
 * Download session information
 */
function downloadSessionInfo(sessionId) {
    console.log('Downloading session info for:', sessionId);

    fetch(`/student/api/session-details/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.session) {
                const session = data.session;

                // Create downloadable content
                const content = `
SESSION INFORMATION
==================

Tutor: ${session.tutor_name}
Email: ${session.tutor_email || 'N/A'}
Course: ${session.course_title || 'General Session'}
Date: ${session.scheduled_date}
Time: ${session.scheduled_time}
Duration: ${session.duration || 60} minutes
Status: ${session.status}
${session.completed_at ? `Completed: ${session.completed_at}` : ''}

${session.notes && session.notes.length > 0 ? `
NOTES:
${session.notes.map(note => `- ${note.content}`).join('\n')}
` : ''}

Generated on: ${new Date().toLocaleString()}
                `.trim();

                // Create and download file
                const blob = new Blob([content], { type: 'text/plain' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `session_${sessionId}_${session.scheduled_date}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                alert('Session information downloaded successfully!');
            } else {
                alert('Failed to load session details');
            }
        })
        .catch(error => {
            console.error('Error downloading session info:', error);
            alert('An error occurred while downloading session information');
        });
}

/**
 * Reschedule session
 */
function rescheduleSession(sessionId) {
    console.log('Attempting to reschedule session:', sessionId);

    // First, get session details to populate the reschedule form
    fetch(`/student/api/session-details/${sessionId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.session) {
                openRescheduleModal(sessionId, data.session);
            } else {
                alert('Failed to load session details');
            }
        })
        .catch(error => {
            console.error('Error loading session details:', error);
            alert('An error occurred while loading session details');
        });
}

/**
 * Open reschedule modal
 */
function openRescheduleModal(sessionId, sessionData) {
    // Create the reschedule modal HTML
    const modalHtml = `
        <div class="modal fade" id="rescheduleModal" tabindex="-1" aria-labelledby="rescheduleModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="rescheduleModalLabel">
                            <i class="fas fa-calendar-alt me-2"></i>Reschedule Session
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Current Session:</strong> ${sessionData.course_title || 'General Session'} with ${sessionData.tutor_name}<br>
                            <strong>Current Time:</strong> ${sessionData.scheduled_date} at ${sessionData.scheduled_time}
                        </div>
                        
                        <form id="rescheduleForm">
                            <div class="mb-3">
                                <label for="rescheduleDate" class="form-label">New Date</label>
                                <input type="date" class="form-control" id="rescheduleDate" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="rescheduleTime" class="form-label">New Time</label>
                                <select class="form-select" id="rescheduleTime" required>
                                    <option value="">Select a time</option>
                                    <option value="08:00">8:00 AM</option>
                                    <option value="09:00">9:00 AM</option>
                                    <option value="10:00">10:00 AM</option>
                                    <option value="11:00">11:00 AM</option>
                                    <option value="12:00">12:00 PM</option>
                                    <option value="13:00">1:00 PM</option>
                                    <option value="14:00">2:00 PM</option>
                                    <option value="15:00">3:00 PM</option>
                                    <option value="16:00">4:00 PM</option>
                                    <option value="17:00">5:00 PM</option>
                                    <option value="18:00">6:00 PM</option>
                                    <option value="19:00">7:00 PM</option>
                                    <option value="20:00">8:00 PM</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="rescheduleReason" class="form-label">Reason for Rescheduling (Optional)</label>
                                <textarea class="form-control" id="rescheduleReason" rows="3" 
                                          placeholder="Please provide a reason for rescheduling..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-warning" onclick="submitReschedule(${sessionId})">
                            <i class="fas fa-calendar-alt me-1"></i>Reschedule Session
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('rescheduleModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to document
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Set minimum date to today
    const dateInput = document.getElementById('rescheduleDate');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;

    // Set max date to 60 days from now
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 60);
    dateInput.max = maxDate.toISOString().split('T')[0];

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('rescheduleModal'));
    modal.show();

    // Clean up modal when hidden
    document.getElementById('rescheduleModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

/**
 * Submit reschedule request
 */
function submitReschedule(sessionId) {
    const form = document.getElementById('rescheduleForm');
    const submitBtn = event.target;

    // Validate form
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = {
        date: document.getElementById('rescheduleDate').value,
        time: document.getElementById('rescheduleTime').value,
        reason: document.getElementById('rescheduleReason').value || 'Rescheduled by student'
    };

    // Show loading
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Rescheduling...';
    submitBtn.disabled = true;

    // Submit reschedule request
    fetch(`/student/api/reschedule-session/${sessionId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(formData)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Session rescheduled successfully!');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('rescheduleModal'));
                if (modal) {
                    modal.hide();
                }

                // Reload page to show updated session
                setTimeout(() => {
                    window.location.reload(true);
                }, 1000);
            } else {
                alert(data.error || 'Failed to reschedule session');
            }
        })
        .catch(error => {
            console.error('Error rescheduling session:', error);
            alert('An error occurred while rescheduling the session');
        })
        .finally(() => {
            // Restore button
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
}

// Make functions globally available
window.submitScheduleForm = submitScheduleForm;
window.cancelSession = cancelSession;
window.endSession = endSession;
window.openScheduleModal = openScheduleModal;
window.viewSessionDetails = viewSessionDetails;
window.rateSession = rateSession;
window.setRating = setRating;
window.submitRating = submitRating;
window.updateRatingDisplay = updateRatingDisplay;
window.bookAgain = bookAgain;
window.downloadSessionInfo = downloadSessionInfo;
window.rescheduleSession = rescheduleSession;
window.submitReschedule = submitReschedule;

// Override main.js functions
document.addEventListener('DOMContentLoaded', function () {
    console.log('Sessions.js loaded - functions available globally');
});