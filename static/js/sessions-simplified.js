/**
 * Sessions Management JavaScript - Simplified Version
 * Handles session scheduling, cancellation, rescheduling, and availability checking
 */

/**
 * Main SessionManager class responsible for all session-related functionality
 */
class SessionManager {
    constructor() {
        // Core state
        this.state = {
            selectedTutorId: null,
            selectedDate: null,
            availableSlots: []
        };

        // Initialize components
        this.api = new SessionAPI();
        this.ui = new SessionUI(this);

        // Initialize everything after DOM is loaded
        document.addEventListener('DOMContentLoaded', () => this.init());
    }

    /**
     * Initialize the SessionManager
     */
    init() {
        this.initializeModals();
        this.setupEventListeners();
        this.initializeDatePicker();
        this.checkCourseAvailability();
    }

    /**
     * Initialize Bootstrap modals
     */
    initializeModals() {
        const scheduleModalElement = document.getElementById('scheduleModal');
        if (scheduleModalElement) {
            this.scheduleModal = new bootstrap.Modal(scheduleModalElement);
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Schedule button
        const scheduleBtn = document.getElementById('scheduleNewSessionBtn');
        if (scheduleBtn) {
            scheduleBtn.addEventListener('click', () => this.openScheduleModal());
        }

        // Course selection
        const courseSelect = document.getElementById('courseSelect');
        if (courseSelect) {
            courseSelect.addEventListener('change', () => this.loadTutorsForCourse());
        }

        // Tutor selection
        const tutorSelect = document.getElementById('tutorSelect');
        if (tutorSelect) {
            tutorSelect.addEventListener('change', () => this.onTutorSelected());
        }

        // Date selection
        const dateInput = document.getElementById('sessionDate');
        if (dateInput) {
            dateInput.addEventListener('change', () => this.onDateSelected());
        }

        // Schedule form submission
        const scheduleForm = document.getElementById('scheduleForm');
        if (scheduleForm) {
            scheduleForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitScheduleForm();
            });
        }
    }

    /**
     * Initialize date picker with constraints
     */
    initializeDatePicker() {
        const dateInput = document.getElementById('sessionDate');
        if (dateInput) {
            // Set min date to today
            const today = new Date().toISOString().split('T')[0];
            dateInput.min = today;

            // Set max date to 60 days from now
            const maxDate = new Date();
            maxDate.setDate(maxDate.getDate() + 60);
            dateInput.max = maxDate.toISOString().split('T')[0];
        }
    }

    /**
     * Check if student is enrolled in any courses
     */
    checkCourseAvailability() {
        const courseSelect = document.getElementById('courseSelect');
        if (courseSelect && courseSelect.options.length <= 1) {
            this.ui.showNoCoursesWarning();
        }
    }

    /**
     * Open schedule session modal
     */
    openScheduleModal(tutorId = null, courseId = null) {
        if (!this.scheduleModal) {
            this.ui.showError("Unable to open schedule modal. Please refresh the page and try again.");
            return;
        }

        // Reset form and selections
        document.getElementById('scheduleForm').reset();
        this.ui.clearAvailabilityPreview();
        this.state.selectedTutorId = null;
        this.state.selectedDate = null;

        // Pre-fill if parameters provided
        if (courseId) {
            document.getElementById('courseSelect').value = courseId;
            this.loadTutorsForCourse();
        }

        if (tutorId) {
            setTimeout(() => {
                document.getElementById('tutorSelect').value = tutorId;
                this.onTutorSelected();
            }, 300);
        }

        // Show the modal
        this.scheduleModal.show();
    }

    /**
     * Load tutors based on selected course
     */
    loadTutorsForCourse() {
        const courseSelect = document.getElementById('courseSelect');
        const tutorSelect = document.getElementById('tutorSelect');
        const courseId = courseSelect.value;

        // Reset tutor selection when course changes
        this.state.selectedTutorId = null;

        // If no course selected or no enrolled courses
        if (!courseId || courseSelect.options.length <= 1) {
            this.ui.resetTutorDropdown();
            return;
        }

        // Show loading state
        this.ui.setTutorDropdownLoading();

        // Get tutors for the selected course
        this.api.getTutorsForCourse(courseId)
            .then(data => {
                if (data.status === 'success' && data.tutors?.length > 0) {
                    this.ui.populateTutors(data.tutors);
                } else {
                    this.ui.setNoTutorsAvailable();
                }
            })
            .catch(error => {
                console.error('Error loading tutors:', error);
                this.ui.setTutorLoadError();
            });
    }

    /**
     * Handle tutor selection
     */
    onTutorSelected() {
        const tutorSelect = document.getElementById('tutorSelect');
        this.state.selectedTutorId = tutorSelect.value;

        if (this.state.selectedTutorId) {
            if (this.state.selectedDate) {
                this.loadAvailableSlots();
            } else {
                this.ui.highlightDateInput();
            }
        } else {
            this.ui.clearAvailabilityPreview();
        }
    }

    /**
     * Handle date selection
     */
    onDateSelected() {
        const dateInput = document.getElementById('sessionDate');
        this.state.selectedDate = dateInput.value;

        if (this.state.selectedDate) {
            if (this.state.selectedTutorId) {
                this.loadAvailableSlots();
            } else {
                this.ui.highlightTutorSelect();
            }
        } else {
            this.ui.clearAvailabilityPreview();
        }
    }

    /**
     * Load available time slots
     */
    loadAvailableSlots() {
        if (!this.state.selectedTutorId || !this.state.selectedDate) {
            return;
        }

        const slotsSelect = document.getElementById('availableSlots');
        this.ui.setSlotsLoading();

        this.api.getTutorAvailability(this.state.selectedTutorId, this.state.selectedDate)
            .then(data => {
                this.state.availableSlots = data.slots || [];

                if (this.state.availableSlots.length > 0) {
                    this.ui.displayAvailableSlots(this.state.availableSlots);
                    this.ui.showAvailabilityPreview(this.state.availableSlots);
                } else {
                    this.ui.setNoSlotsAvailable();
                    this.ui.clearAvailabilityPreview();
                }
            })
            .catch(error => {
                console.error('Error loading slots:', error);
                this.ui.setSlotsError();
                this.ui.clearAvailabilityPreview();
            });
    }

    /**
     * Submit schedule form
     */
    submitScheduleForm() {
        // Get form data
        const formData = this.ui.getScheduleFormData();

        // Validate form
        if (!this.validateScheduleForm(formData)) {
            return;
        }

        // Show loading state
        this.ui.setScheduleSubmitLoading(true);

        // Submit the request
        this.api.scheduleSession(formData)
            .then(result => {
                if (result.success) {
                    this.ui.showSuccess('Session scheduled successfully!');
                    this.scheduleModal.hide();

                    // Reload page after a delay
                    setTimeout(() => location.reload(), 1000);
                } else {
                    throw new Error(result.error || 'Failed to schedule session');
                }
            })
            .catch(error => {
                this.ui.showError(error.message || 'An error occurred while scheduling the session');
            })
            .finally(() => {
                this.ui.setScheduleSubmitLoading(false);
            });
    }

    /**
     * Validate schedule form
     */
    validateScheduleForm(formData) {
        const { courseId, tutorId, date, time } = formData;

        if (!courseId || !tutorId || !date || !time) {
            this.ui.showValidationErrors(formData);
            return false;
        }

        return true;
    }

    /**
     * Cancel a session
     */
    cancelSession(sessionId) {
        if (!confirm('Are you sure you want to cancel this session? This action cannot be undone.')) {
            return;
        }

        this.api.cancelSession(sessionId)
            .then(result => {
                if (result.success) {
                    this.ui.showSuccess('Session cancelled successfully');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    throw new Error(result.error || 'Failed to cancel session');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            });
    }

    /**
     * End an active session
     */
    endSession(sessionId) {
        if (!confirm('Are you sure you want to end this session? This will mark it as completed.')) {
            return;
        }

        this.api.endSession(sessionId)
            .then(result => {
                if (result.success) {
                    this.ui.showSuccess('Session ended successfully');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    throw new Error(result.error || 'Failed to end session');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            });
    }

    /**
     * View session details
     */
    viewSessionDetails(sessionId) {
        this.api.getSessionDetails(sessionId)
            .then(data => {
                if (data.session) {
                    this.ui.showSessionDetailsModal(data.session);
                } else {
                    throw new Error('Failed to load session details');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            });
    }

    /**
     * Rate a session
     */
    rateSession(sessionId) {
        this.ui.showRatingModal(sessionId);
    }

    /**
     * Submit session rating
     */
    submitRating(sessionId, rating, review) {
        if (!rating) {
            this.ui.showError('Please select a rating');
            return;
        }

        this.ui.setRatingSubmitLoading(true);

        this.api.rateSession(sessionId, rating, review)
            .then(result => {
                if (result.success) {
                    this.ui.showSuccess('Rating submitted successfully!');
                    this.ui.closeRatingModal();
                    this.ui.updateRatingDisplay(sessionId, rating);
                } else {
                    throw new Error(result.error || 'Failed to submit rating');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            })
            .finally(() => {
                this.ui.setRatingSubmitLoading(false);
            });
    }

    /**
     * Reschedule a session
     */
    rescheduleSession(sessionId) {
        this.api.getSessionDetails(sessionId)
            .then(data => {
                if (data.session) {
                    this.ui.showRescheduleModal(data.session);
                } else {
                    throw new Error('Failed to load session details');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            });
    }

    /**
     * Submit reschedule request
     */
    submitReschedule(sessionId, rescheduleData) {
        if (!rescheduleData.date || !rescheduleData.time) {
            this.ui.showError('Please select a new date and time');
            return;
        }

        this.ui.setRescheduleSubmitLoading(true);

        this.api.rescheduleSession(sessionId, rescheduleData)
            .then(result => {
                if (result.success) {
                    this.ui.showSuccess('Session rescheduled successfully!');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    throw new Error(result.error || 'Failed to reschedule session');
                }
            })
            .catch(error => {
                this.ui.showError(error.message);
            })
            .finally(() => {
                this.ui.setRescheduleSubmitLoading(false);
            });
    }
}

/**
 * SessionAPI: Handles all API requests
 */
class SessionAPI {
    /**
     * Get tutors qualified for a specific course
     */
    getTutorsForCourse(courseId) {
        return fetch(`/student/api/tutors-for-course/${courseId}`)
            .then(this.handleResponse);
    }

    /**
     * Get tutor availability for a specific date
     */
    getTutorAvailability(tutorId, date) {
        return fetch(`/student/api/tutor-availability?tutor_id=${tutorId}&date=${date}`)
            .then(this.handleResponse);
    }

    /**
     * Schedule a new session
     */
    scheduleSession(sessionData) {
        return fetch('/student/api/schedule-session', {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(sessionData)
        })
            .then(this.handleResponse);
    }

    /**
     * Cancel a session
     */
    cancelSession(sessionId) {
        return fetch(`/student/api/cancel-session/${sessionId}`, {
            method: 'POST',
            headers: this.getHeaders()
        })
            .then(this.handleResponse);
    }

    /**
     * End an active session
     */
    endSession(sessionId) {
        return fetch(`/student/api/end_session/${sessionId}`, {
            method: 'POST',
            headers: this.getHeaders()
        })
            .then(this.handleResponse);
    }

    /**
     * Get session details
     */
    getSessionDetails(sessionId) {
        return fetch(`/student/api/session-details/${sessionId}`)
            .then(this.handleResponse);
    }

    /**
     * Rate a session
     */
    rateSession(sessionId, rating, review) {
        return fetch(`/student/api/rate-session/${sessionId}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({
                rating: parseInt(rating),
                review: review || ''
            })
        })
            .then(this.handleResponse);
    }

    /**
     * Reschedule a session
     */
    rescheduleSession(sessionId, data) {
        return fetch(`/student/api/reschedule-session/${sessionId}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        })
            .then(this.handleResponse);
    }

    /**
     * Handle API response
     */
    handleResponse(response) {
        if (!response.ok) {
            return response.json().then(data => Promise.reject(new Error(data.error || `Server error (${response.status})`)));
        }
        return response.json();
    }

    /**
     * Get common headers for requests
     */
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
    }
}

/**
 * SessionUI: Handles all UI operations
 */
class SessionUI {
    constructor(manager) {
        this.manager = manager;
    }

    /**
     * Show a notification message
     */
    showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 1050; min-width: 300px; max-width: 400px;';

        const iconClass = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        }[type] || 'bell';

        alertDiv.innerHTML = `
            <i class="fas fa-${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.classList.add('fade-out');
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Show warning message
     */
    showWarning(message) {
        this.showNotification(message, 'warning');
    }

    /**
     * Show a warning about no courses
     */
    showNoCoursesWarning() {
        const courseSelect = document.getElementById('courseSelect');
        const warningContainer = courseSelect.closest('.form-group') || courseSelect.parentElement;

        if (warningContainer && !warningContainer.querySelector('.no-courses-warning')) {
            const warning = document.createElement('div');
            warning.className = 'alert alert-warning mt-2 no-courses-warning';
            warning.innerHTML = 'You are not enrolled in any courses. Please enroll in a course before scheduling a session.';
            warningContainer.appendChild(warning);
        }
    }

    /**
     * Reset tutor dropdown
     */
    resetTutorDropdown() {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">Select a course first</option>';
        tutorSelect.disabled = true;
        this.clearAvailabilityPreview();
    }

    /**
     * Set tutor dropdown to loading state
     */
    setTutorDropdownLoading() {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">Loading tutors...</option>';
        tutorSelect.disabled = true;
    }

    /**
     * Set tutor dropdown to show no tutors available
     */
    setNoTutorsAvailable() {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">No qualified tutors available for this course</option>';
        tutorSelect.disabled = true;
    }

    /**
     * Set tutor dropdown to show error
     */
    setTutorLoadError() {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">Error loading tutors</option>';
        tutorSelect.disabled = true;
    }

    /**
     * Populate tutor dropdown with list of tutors
     */
    populateTutors(tutors) {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">Select a tutor</option>';

        tutors.forEach(tutor => {
            const option = document.createElement('option');
            option.value = tutor.id;

            // Format tutor display name with rating
            let displayName = tutor.username;

            if (tutor.avg_rating) {
                const stars = '★'.repeat(Math.round(tutor.avg_rating)) +
                    '☆'.repeat(5 - Math.round(tutor.avg_rating));
                displayName += ` (${stars})`;
            }

            option.textContent = displayName;
            option.dataset.rating = tutor.avg_rating || '0';
            tutorSelect.appendChild(option);
        });

        tutorSelect.disabled = false;
    }

    /**
     * Highlight date input field
     */
    highlightDateInput() {
        const dateInput = document.getElementById('sessionDate');
        dateInput.classList.add('highlight-required');
        setTimeout(() => dateInput.classList.remove('highlight-required'), 2000);
    }

    /**
     * Highlight tutor select field
     */
    highlightTutorSelect() {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.classList.add('highlight-required');
        setTimeout(() => tutorSelect.classList.remove('highlight-required'), 2000);
    }

    /**
     * Set time slots to loading state
     */
    setSlotsLoading() {
        const slotsSelect = document.getElementById('availableSlots');
        slotsSelect.innerHTML = '<option value="">Loading available slots...</option>';
        slotsSelect.disabled = true;
    }

    /**
     * Set time slots to no slots available
     */
    setNoSlotsAvailable() {
        const slotsSelect = document.getElementById('availableSlots');
        slotsSelect.innerHTML = '<option value="">No available slots for this date</option>';
        slotsSelect.disabled = true;
    }

    /**
     * Set time slots to error state
     */
    setSlotsError() {
        const slotsSelect = document.getElementById('availableSlots');
        slotsSelect.innerHTML = '<option value="">Error loading time slots</option>';
        slotsSelect.disabled = true;
    }

    /**
     * Display available time slots in dropdown
     */
    displayAvailableSlots(slots) {
        const slotsSelect = document.getElementById('availableSlots');
        slotsSelect.innerHTML = '<option value="">Select a time</option>';

        slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot;
            option.textContent = this.formatTime(slot);
            slotsSelect.appendChild(option);
        });

        slotsSelect.disabled = false;
    }

    /**
     * Get form data from schedule form
     */
    getScheduleFormData() {
        return {
            courseId: document.getElementById('courseSelect').value,
            tutorId: document.getElementById('tutorSelect').value,
            date: document.getElementById('sessionDate').value,
            time: document.getElementById('availableSlots').value,
            duration: document.getElementById('sessionDuration').value,
            notes: document.getElementById('sessionNotes').value
        };
    }

    /**
     * Show validation errors for form
     */
    showValidationErrors(formData) {
        if (!formData.courseId) document.getElementById('courseSelect').classList.add('is-invalid');
        if (!formData.tutorId) document.getElementById('tutorSelect').classList.add('is-invalid');
        if (!formData.date) document.getElementById('sessionDate').classList.add('is-invalid');
        if (!formData.time) document.getElementById('availableSlots').classList.add('is-invalid');

        this.showWarning('Please fill in all required fields');

        setTimeout(() => {
            document.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
            });
        }, 3000);
    }

    /**
     * Set schedule submit button loading state
     */
    setScheduleSubmitLoading(isLoading) {
        const btn = document.getElementById('scheduleSubmitBtn');
        if (isLoading) {
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Scheduling...';
            btn.disabled = true;
        } else {
            btn.innerHTML = '<i class="fas fa-calendar-check me-2"></i>Schedule Session';
            btn.disabled = false;
        }
    }

    /**
     * Set rating submit button loading state
     */
    setRatingSubmitLoading(isLoading) {
        const btn = document.getElementById('submitRatingBtn');
        if (isLoading) {
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
            btn.disabled = true;
        } else {
            btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit Rating';
            btn.disabled = false;
        }
    }

    /**
     * Set reschedule submit button loading state
     */
    setRescheduleSubmitLoading(isLoading) {
        const btn = document.getElementById('rescheduleSubmitBtn');
        if (isLoading) {
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Rescheduling...';
            btn.disabled = true;
        } else {
            btn.innerHTML = '<i class="fas fa-calendar-check me-2"></i>Reschedule Session';
            btn.disabled = false;
        }
    }

    /**
     * Format time string (24h to 12h)
     */
    formatTime(timeString) {
        if (!timeString) return '';

        const [hours, minutes] = timeString.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    }

    /**
     * Show availability preview
     */
    showAvailabilityPreview(slots) {
        const previewDiv = document.getElementById('tutorAvailabilityPreview');
        const slotsDiv = document.getElementById('availabilitySlots');

        if (!previewDiv || !slotsDiv || !slots || slots.length === 0) {
            this.clearAvailabilityPreview();
            return;
        }

        slotsDiv.innerHTML = slots.map(slot =>
            `<span class="badge bg-success me-2 mb-2">${this.formatTime(slot)}</span>`
        ).join('');

        previewDiv.classList.remove('d-none');
    }

    /**
     * Clear availability preview
     */
    clearAvailabilityPreview() {
        const previewDiv = document.getElementById('tutorAvailabilityPreview');
        if (previewDiv) {
            previewDiv.classList.add('d-none');
        }
    }

    /**
     * Show session details modal
     */
    showSessionDetailsModal(session) {
        // Create and show modal with session details
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
                                    <p><strong>Time:</strong> ${this.formatTime(session.scheduled_time)}</p>
                                    <p><strong>Duration:</strong> ${session.duration || 60} minutes</p>
                                </div>
                                <div class="col-md-6">
                                    <h6><i class="fas fa-info me-2"></i>Status</h6>
                                    <p><strong>Status:</strong> 
                                        <span class="badge bg-${session.status === 'completed' ? 'success' :
                session.status === 'cancelled' ? 'danger' : 'secondary'
            }">
                                            ${session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                                        </span>
                                    </p>
                                    ${session.completed_at ? `<p><strong>Completed:</strong> ${session.completed_at}</p>` : ''}
                                </div>
                            </div>
                            ${session.notes ? `
                                <hr>
                                <h6><i class="fas fa-sticky-note me-2"></i>Session Notes</h6>
                                <p class="border-start border-3 ps-3 mb-2">${session.notes}</p>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            ${session.status === 'completed' && !session.rating ? `
                                <button type="button" class="btn btn-primary" 
                                        onclick="sessionManager.rateSession(${session.id})" data-bs-dismiss="modal">
                                    <i class="fas fa-star me-2"></i>Rate Session
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('sessionDetailsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show it
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('sessionDetailsModal'));
        modal.show();
    }

    /**
     * Show rating modal for a session
     */
    showRatingModal(sessionId) {
        const modalHtml = `
            <div class="modal fade" id="ratingModal" tabindex="-1">
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
                                <div class="mb-3 text-center">
                                    <label class="form-label">Rating (1-5 stars)</label>
                                    <div class="rating-stars mb-3">
                                        ${[1, 2, 3, 4, 5].map(i => `
                                            <i class="fas fa-star rating-star text-muted" 
                                               data-rating="${i}" 
                                               style="font-size: 2rem; cursor: pointer;"
                                               onclick="sessionManager.ui.selectRating(${i})"></i>
                                        `).join('')}
                                    </div>
                                    <input type="hidden" id="selectedRating" value="0">
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
                            <button type="button" class="btn btn-warning" id="submitRatingBtn"
                                    onclick="sessionManager.submitRating(${sessionId}, 
                                                                     document.getElementById('selectedRating').value,
                                                                     document.getElementById('reviewText').value)">
                                <i class="fas fa-paper-plane me-2"></i>Submit Rating
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('ratingModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show it
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('ratingModal'));
        modal.show();
    }

    /**
     * Select rating when stars are clicked
     */
    selectRating(rating) {
        document.getElementById('selectedRating').value = rating;
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
     * Close the rating modal
     */
    closeRatingModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('ratingModal'));
        if (modal) {
            modal.hide();
        }
    }

    /**
     * Update rating display in the session list
     */
    updateRatingDisplay(sessionId, rating) {
        // Find session elements with this ID
        const sessionElements = document.querySelectorAll(`[data-session-id="${sessionId}"]`);

        sessionElements.forEach(element => {
            const ratingDiv = element.querySelector('.rating');
            if (ratingDiv) {
                let starsHtml = '';
                for (let i = 0; i < 5; i++) {
                    const starClass = i < rating ? 'text-warning' : 'text-muted';
                    starsHtml += `<i class="fas fa-star ${starClass}"></i>`;
                }
                ratingDiv.innerHTML = starsHtml;
            }
        });
    }

    /**
     * Show reschedule modal
     */
    showRescheduleModal(session) {
        // Get date constraints
        const today = new Date().toISOString().split('T')[0];
        const maxDate = new Date();
        maxDate.setDate(maxDate.getDate() + 60);
        const maxDateStr = maxDate.toISOString().split('T')[0];

        const modalHtml = `
            <div class="modal fade" id="rescheduleModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-calendar-alt me-2"></i>Reschedule Session
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Current Session:</strong> ${session.course_title || 'General Session'} with ${session.tutor_name}<br>
                                <strong>Current Time:</strong> ${session.scheduled_date} at ${this.formatTime(session.scheduled_time)}
                            </div>
                            
                            <form id="rescheduleForm">
                                <div class="mb-3">
                                    <label for="rescheduleDate" class="form-label">New Date</label>
                                    <input type="date" class="form-control" id="rescheduleDate" 
                                           min="${today}" max="${maxDateStr}" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="rescheduleTime" class="form-label">New Time</label>
                                    <select class="form-select" id="rescheduleTime" required>
                                        <option value="">Select a date first</option>
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
                            <button type="button" class="btn btn-primary" id="rescheduleSubmitBtn" onclick="sessionManager.submitReschedule(
                                ${session.id}, 
                                { 
                                    date: document.getElementById('rescheduleDate').value,
                                    time: document.getElementById('rescheduleTime').value,
                                    reason: document.getElementById('rescheduleReason').value || 'Rescheduled by student'
                                }
                            )">
                                <i class="fas fa-calendar-check me-2"></i>Reschedule Session
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('rescheduleModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show it
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Add date change event listener
        const dateInput = document.getElementById('rescheduleDate');
        if (dateInput) {
            dateInput.addEventListener('change', () => this.loadRescheduleTimeSlots(session.tutor_id));
        }

        const modal = new bootstrap.Modal(document.getElementById('rescheduleModal'));
        modal.show();
    }

    /**
     * Load available time slots for rescheduling
     */
    loadRescheduleTimeSlots(tutorId) {
        const dateInput = document.getElementById('rescheduleDate');
        const timeSelect = document.getElementById('rescheduleTime');

        if (!dateInput.value) {
            timeSelect.innerHTML = '<option value="">Select a date first</option>';
            return;
        }

        timeSelect.innerHTML = '<option value="">Loading available times...</option>';

        fetch(`/student/api/tutor-availability?tutor_id=${tutorId}&date=${dateInput.value}`)
            .then(response => response.json())
            .then(data => {
                if (data.slots && data.slots.length > 0) {
                    timeSelect.innerHTML = '<option value="">Select a time</option>';
                    data.slots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot;
                        option.textContent = this.formatTime(slot);
                        timeSelect.appendChild(option);
                    });
                } else {
                    timeSelect.innerHTML = '<option value="">No available times for this date</option>';
                }
            })
            .catch(error => {
                console.error('Error loading time slots:', error);
                timeSelect.innerHTML = '<option value="">Error loading time slots</option>';
            });
    }
}

// Initialize session manager and connect it to the global scope
let sessionManager;
document.addEventListener('DOMContentLoaded', () => {
    sessionManager = new SessionManager();

    // Set up global functions for backward compatibility with existing HTML
    window.cancelSession = (sessionId) => sessionManager.cancelSession(sessionId);
    window.endSession = (sessionId) => sessionManager.endSession(sessionId);
    window.viewSessionDetails = (sessionId) => sessionManager.viewSessionDetails(sessionId);
    window.rateSession = (sessionId) => sessionManager.rateSession(sessionId);
    window.submitScheduleForm = () => sessionManager.submitScheduleForm();
    window.openScheduleModal = (tutorId, courseId) => sessionManager.openScheduleModal(tutorId, courseId);
    window.rescheduleSession = (sessionId) => sessionManager.rescheduleSession(sessionId);
    window.bookAgain = (tutorId, courseId) => sessionManager.openScheduleModal(tutorId, courseId);
});
