/**
 * Sessions Management JavaScript - Refactored Version
 * Handles session scheduling, cancellation, rescheduling, and availability checking
 * 
 * This is a modular, class-based implementation that simplifies the original 1200+ line file
 * by organizing code into logical components with clear responsibilities.
 */

/**
 * Main SessionManager class that handles all session-related functionality
 */
class SessionManager {
    constructor() {
        // State variables
        this.selectedTutorId = null;
        this.selectedDate = null;
        this.availableSlots = [];
        this.scheduleModal = null;

        // Initialize components
        this.api = new SessionAPI();
        this.ui = new SessionUI(this);

        // Bind methods to maintain 'this' context
        this.openScheduleModal = this.openScheduleModal.bind(this);
        this.loadTutorsForCourse = this.loadTutorsForCourse.bind(this);
        this.onTutorSelected = this.onTutorSelected.bind(this);
        this.onDateSelected = this.onDateSelected.bind(this);
        this.submitScheduleForm = this.submitScheduleForm.bind(this);

        // Initialize after DOM is loaded
        this.init();
    }

    /**
     * Initialize the manager
     */
    init() {
        // Initialize modal if it exists
        const scheduleModalElement = document.getElementById('scheduleModal');
        if (scheduleModalElement) {
            this.scheduleModal = new bootstrap.Modal(scheduleModalElement);
        } else {
            console.error('Schedule modal element not found!');
            return;
        }

        // Set up event listeners
        this.setupEventListeners();

        // Initialize date picker
        this.initializeDatePicker();

        // Check if course select is empty
        const courseSelect = document.getElementById('courseSelect');
        if (courseSelect && courseSelect.options.length <= 1) {
            console.log("No courses found - student may not be enrolled in any courses");
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Add click handler for schedule button
        const scheduleBtn = document.getElementById('scheduleNewSessionBtn');
        if (scheduleBtn) {
            scheduleBtn.addEventListener('click', () => this.openScheduleModal());
        }

        // Course selection change
        const courseSelect = document.getElementById('courseSelect');
        if (courseSelect) {
            courseSelect.addEventListener('change', this.loadTutorsForCourse);
        }

        // Tutor selection change
        const tutorSelect = document.getElementById('tutorSelect');
        if (tutorSelect) {
            tutorSelect.addEventListener('change', this.onTutorSelected);
        }

        // Date selection change
        const dateInput = document.getElementById('sessionDate');
        if (dateInput) {
            dateInput.addEventListener('change', this.onDateSelected);
        }
    }

    /**
     * Initialize date picker with minimum date as today
     */
    initializeDatePicker() {
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
     * Open schedule session modal
     */
    openScheduleModal(tutorId = null, courseId = null) {
        // Initialize modal if not already done
        if (!this.scheduleModal) {
            const modalElement = document.getElementById('scheduleModal');
            if (!modalElement) {
                console.error("Modal element not found!");
                alert("Unable to open schedule modal. Please refresh the page and try again.");
                return;
            }
            this.scheduleModal = new bootstrap.Modal(modalElement);
        }

        // Reset form and clear previous selections
        const form = document.getElementById('scheduleForm');
        form.reset();
        this.ui.clearAvailabilityPreview();

        this.selectedTutorId = null;
        this.selectedDate = null;

        // Set today as minimum date for date picker
        const dateInput = document.getElementById('sessionDate');
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;

        // Set 60 days from now as maximum date
        const maxDate = new Date();
        maxDate.setDate(maxDate.getDate() + 60);
        dateInput.max = maxDate.toISOString().split('T')[0];

        // Ensure dropdown is ready
        const courseSelect = document.getElementById('courseSelect');

        if (courseSelect.options.length <= 1) {
            console.log("No enrolled courses found!");
            this.ui.showEnrolledCoursesWarning();
        }

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
        this.selectedTutorId = null;

        // If no enrolled courses, show a clear message
        if (courseSelect.options.length <= 1) {
            tutorSelect.innerHTML = '<option value="">No enrolled courses available</option>';
            tutorSelect.disabled = true;

            // Show a warning message in the form
            this.ui.showNoCoursesWarning();
            return;
        }

        if (!courseId) {
            tutorSelect.innerHTML = '<option value="">Select a course first</option>';
            tutorSelect.disabled = true;
            this.ui.clearAvailabilityPreview();
            return;
        }

        // Show loading
        tutorSelect.innerHTML = '<option value="">Loading tutors for this course...</option>';
        tutorSelect.disabled = true;

        // Call the API to get tutors qualified for this specific course
        this.api.getTutorsForCourse(courseId)
            .then(data => {
                if (data.status === 'success' && data.tutors && data.tutors.length > 0) {
                    this.ui.populateTutors(data.tutors);
                } else {
                    tutorSelect.innerHTML = '<option value="">No qualified tutors available for this course</option>';
                    tutorSelect.disabled = true;
                }
            })
            .catch(error => {
                console.error('Error loading tutors:', error);
                tutorSelect.innerHTML = '<option value="">Error loading tutors</option>';
                tutorSelect.disabled = true;
            });
    }

    /**
     * Handle tutor selection
     */
    onTutorSelected() {
        const tutorSelect = document.getElementById('tutorSelect');
        this.selectedTutorId = tutorSelect.value;

        if (this.selectedTutorId) {
            // If date is also selected, load slots
            if (this.selectedDate) {
                this.loadAvailableSlots();
            } else {
                // Prompt user to select date
                const dateInput = document.getElementById('sessionDate');
                dateInput.classList.add('highlight-required');
                setTimeout(() => dateInput.classList.remove('highlight-required'), 2000);
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
        this.selectedDate = dateInput.value;

        if (this.selectedDate) {
            // If tutor is also selected, load slots
            if (this.selectedTutorId) {
                this.loadAvailableSlots();
            } else {
                // Prompt user to select tutor
                const tutorSelect = document.getElementById('tutorSelect');
                tutorSelect.classList.add('highlight-required');
                setTimeout(() => tutorSelect.classList.remove('highlight-required'), 2000);
            }
        } else {
            this.ui.clearAvailabilityPreview();
        }
    }

    /**
     * Load available time slots based on tutor and date
     */
    loadAvailableSlots() {
        if (!this.selectedTutorId || !this.selectedDate) {
            return;
        }

        const slotsSelect = document.getElementById('availableSlots');
        slotsSelect.innerHTML = '<option value="">Loading available time slots...</option>';
        slotsSelect.disabled = true;

        this.api.getTutorAvailability(this.selectedTutorId, this.selectedDate)
            .then(data => {
                this.availableSlots = data.slots || [];
                this.ui.populateAvailableSlots(this.availableSlots);
                this.ui.showAvailabilityPreview(this.availableSlots, data.tutor_name);
            })
            .catch(error => {
                console.error('Error loading time slots:', error);
                slotsSelect.innerHTML = '<option value="">Error loading time slots</option>';
                slotsSelect.disabled = true;
                this.ui.clearAvailabilityPreview();
            });
    }

    /**
     * Submit the schedule form
     */
    submitScheduleForm() {
        // Get form data
        const courseId = document.getElementById('courseSelect').value;
        const tutorId = document.getElementById('tutorSelect').value;
        const date = document.getElementById('sessionDate').value;
        const timeSelect = document.getElementById('availableSlots');
        const time = timeSelect.value;
        const duration = document.getElementById('sessionDuration').value;
        const notes = document.getElementById('sessionNotes').value;

        // Validate form
        if (!courseId || !tutorId || !date || !time) {
            this.ui.showNotification('Please fill in all required fields.', 'warning');

            // Highlight missing fields
            if (!courseId) document.getElementById('courseSelect').classList.add('highlight-required');
            if (!tutorId) document.getElementById('tutorSelect').classList.add('highlight-required');
            if (!date) document.getElementById('sessionDate').classList.add('highlight-required');
            if (!time) timeSelect.classList.add('highlight-required');

            setTimeout(() => {
                document.querySelectorAll('.highlight-required').forEach(el => {
                    el.classList.remove('highlight-required');
                });
            }, 2000);

            return;
        }

        // Prepare data
        const sessionData = {
            courseId: parseInt(courseId),
            tutorId: parseInt(tutorId),
            date: date,
            time: time,
            duration: parseInt(duration),
            notes: notes
        };

        // Show loading state
        const submitBtn = document.getElementById('scheduleSubmitBtn');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Scheduling...';
        submitBtn.disabled = true;

        // Submit the data
        this.api.scheduleSession(sessionData)
            .then(result => {
                if (result.success) {
                    this.ui.showNotification(result.message || 'Session scheduled successfully!', 'success');

                    // Close modal
                    this.scheduleModal.hide();

                    // Refresh page after a delay
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else {
                    throw new Error(result.error || 'Failed to schedule session.');
                }
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
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
                if (result.status === 'success') {
                    this.ui.showNotification(result.message || 'Session cancelled successfully.', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    throw new Error(result.error || 'Failed to cancel session.');
                }
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }

    /**
     * End an in-progress session
     */
    endSession(sessionId) {
        if (!confirm('Are you sure you want to end this session? This will mark it as completed.')) {
            return;
        }

        this.api.endSession(sessionId)
            .then(result => {
                if (result.success) {
                    this.ui.showNotification(result.message || 'Session ended successfully.', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    throw new Error(result.error || 'Failed to end session.');
                }
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }

    /**
     * View session details
     */
    viewSessionDetails(sessionId) {
        this.api.getSessionDetails(sessionId)
            .then(session => {
                this.ui.showSessionDetailsModal(session);
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }

    /**
     * Create rating modal for session
     */
    rateSession(sessionId) {
        this.ui.showRatingModal(sessionId);
    }

    /**
     * Submit rating for a session
     */
    submitRating(sessionId, rating, reviewText) {
        this.api.submitSessionRating(sessionId, rating, reviewText)
            .then(result => {
                if (result.success) {
                    this.ui.showNotification(result.message || 'Rating submitted successfully!', 'success');
                    this.ui.updateRatingDisplay(sessionId, rating);

                    // Close modal if it exists
                    const ratingModal = bootstrap.Modal.getInstance(document.getElementById('ratingModal'));
                    if (ratingModal) ratingModal.hide();
                } else {
                    throw new Error(result.error || 'Failed to submit rating.');
                }
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }

    /**
     * Start a rescheduling process for a session
     */
    rescheduleSession(sessionId) {
        this.api.getSessionDetails(sessionId)
            .then(session => {
                this.ui.showRescheduleModal(session);
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }

    /**
     * Submit the reschedule request
     */
    submitReschedule(sessionId, newDate, newTime, reason) {
        this.api.rescheduleSession(sessionId, newDate, newTime, reason)
            .then(result => {
                if (result.success) {
                    this.ui.showNotification(result.message || 'Session rescheduled successfully!', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    throw new Error(result.error || 'Failed to reschedule session.');
                }
            })
            .catch(error => {
                this.ui.showNotification(error.message, 'error');
            });
    }
}

/**
 * API wrapper for session-related requests
 */
class SessionAPI {
    /**
     * Get tutors qualified for a specific course
     */
    getTutorsForCourse(courseId) {
        return fetch(`/student/api/tutors-for-course/${courseId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            });
    }

    /**
     * Get tutor availability for a specific date
     */
    getTutorAvailability(tutorId, date) {
        return fetch(`/student/api/tutor-availability?tutor_id=${tutorId}&date=${date}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            });
    }

    /**
     * Schedule a new session
     */
    scheduleSession(sessionData) {
        return fetch('/student/api/schedule-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(sessionData)
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            });
    }

    /**
     * Cancel a session
     */
    cancelSession(sessionId) {
        return fetch(`/student/api/sessions/${sessionId}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            });
    }

    /**
     * End an in-progress session
     */
    endSession(sessionId) {
        return fetch(`/student/api/end_session/${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            });
    }

    /**
     * Get session details
     */
    getSessionDetails(sessionId) {
        return fetch(`/student/api/sessions/${sessionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            });
    }

    /**
     * Submit a rating for a session
     */
    submitSessionRating(sessionId, rating, reviewText) {
        return fetch(`/student/api/sessions/${sessionId}/rate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ rating, review_text: reviewText })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            });
    }

    /**
     * Reschedule a session
     */
    rescheduleSession(sessionId, newDate, newTime, reason) {
        return fetch(`/student/api/sessions/${sessionId}/reschedule`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                new_date: newDate,
                new_time: newTime,
                reason: reason
            })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            });
    }
}

/**
 * UI helper class for session-related UI operations
 */
class SessionUI {
    constructor(manager) {
        this.manager = manager;
    }

    /**
     * Show a notification message
     */
    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer') || document.body;

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' :
                type === 'error' ? 'exclamation-circle' :
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Add to container
        container.prepend(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 150);
        }, 5000);
    }

    /**
     * Show a warning about no enrolled courses
     */
    showEnrolledCoursesWarning() {
        const modalBody = document.querySelector('#scheduleModal .modal-body');
        if (modalBody) {
            const warningAlert = document.createElement('div');
            warningAlert.className = 'alert alert-warning';
            warningAlert.innerHTML = '<strong>No enrolled courses!</strong> You must enroll in a course before you can schedule tutoring sessions.';
            modalBody.prepend(warningAlert);
        }
    }

    /**
     * Show a warning about no courses in the form
     */
    showNoCoursesWarning() {
        const courseSelectParent = document.getElementById('courseSelect').parentElement;
        if (courseSelectParent) {
            if (!courseSelectParent.querySelector('.no-courses-warning')) {
                const warningMsg = document.createElement('div');
                warningMsg.className = 'alert alert-warning mt-2 no-courses-warning';
                warningMsg.innerHTML = 'You are not enrolled in any courses. Please enroll in a course before scheduling a session.';
                courseSelectParent.appendChild(warningMsg);
            }
        }
    }

    /**
     * Populate tutors dropdown
     */
    populateTutors(tutors) {
        const tutorSelect = document.getElementById('tutorSelect');
        tutorSelect.innerHTML = '<option value="">Select a tutor</option>';

        tutors.forEach(tutor => {
            const option = document.createElement('option');
            option.value = tutor.id;

            // Display only tutor name and stars
            let tutorInfo = tutor.username;

            // Add rating if available
            if (tutor.avg_rating) {
                const stars = '★'.repeat(Math.round(tutor.avg_rating)) +
                    '☆'.repeat(5 - Math.round(tutor.avg_rating));
                tutorInfo += ` (${stars})`;
            }

            option.textContent = tutorInfo;
            option.dataset.rating = tutor.avg_rating || '0';
            tutorSelect.appendChild(option);
        });

        tutorSelect.disabled = false;
    }

    /**
     * Populate available time slots dropdown
     */
    populateAvailableSlots(slots) {
        const slotsSelect = document.getElementById('availableSlots');

        if (!slots || slots.length === 0) {
            slotsSelect.innerHTML = '<option value="">No available time slots</option>';
            slotsSelect.disabled = true;
            return;
        }

        slotsSelect.innerHTML = '<option value="">Select a time slot</option>';
        slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot;
            option.textContent = this.formatTime(slot);
            slotsSelect.appendChild(option);
        });

        slotsSelect.disabled = false;
    }

    /**
     * Show availability preview
     */
    showAvailabilityPreview(slots, tutorName) {
        const previewDiv = document.getElementById('tutorAvailabilityPreview');
        const slotsDiv = document.getElementById('availabilitySlots');

        if (!previewDiv || !slotsDiv) return;

        if (!slots || slots.length === 0) {
            previewDiv.classList.add('d-none');
            return;
        }

        // Update title if tutor name available
        if (tutorName) {
            previewDiv.querySelector('h6').innerHTML = `
                <i class="fas fa-clock me-2"></i>${tutorName}'s Availability
            `;
        }

        // Display slots as badges
        slotsDiv.innerHTML = slots.map(slot =>
            `<span class="badge bg-info me-1 mb-1">${this.formatTime(slot)}</span>`
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
     * Format time from 24-hour to 12-hour format
     */
    formatTime(timeString) {
        const [hours, minutes] = timeString.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const formattedHour = hour % 12 || 12;
        return `${formattedHour}:${minutes} ${ampm}`;
    }

    /**
     * Show session details in a modal
     */
    showSessionDetailsModal(session) {
        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="sessionDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-info-circle me-2"></i>Session Details
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Session information -->
                            <div class="card mb-3">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">Basic Information</h6>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <p><strong>Tutor:</strong> ${session.tutor_name}</p>
                                            <p><strong>Course:</strong> ${session.course_title || 'N/A'}</p>
                                            <p><strong>Date:</strong> ${session.scheduled_date}</p>
                                        </div>
                                        <div class="col-md-6">
                                            <p><strong>Time:</strong> ${this.formatTime(session.scheduled_time)}</p>
                                            <p><strong>Duration:</strong> ${session.duration || 60} minutes</p>
                                            <p><strong>Status:</strong> <span class="badge bg-${session.status === 'scheduled' ? 'success' :
                session.status === 'completed' ? 'primary' :
                    session.status === 'cancelled' ? 'danger' : 'info'
            }">${session.status}</span></p>
                                        </div>
                                    </div>
                                    
                                    ${session.notes ? `
                                    <h6 class="card-subtitle mb-2 mt-3 text-muted">Notes</h6>
                                    <p>${session.notes}</p>
                                    ` : ''}
                                    
                                    ${session.review_text ? `
                                    <h6 class="card-subtitle mb-2 mt-3 text-muted">Your Review</h6>
                                    <div class="mb-1">
                                        ${Array(5).fill(0).map((_, i) =>
                `<i class="fas fa-star ${i < session.rating ? 'text-warning' : 'text-muted'}"></i>`
            ).join('')}
                                    </div>
                                    <p>${session.review_text}</p>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            ${session.status === 'completed' && !session.rating ? `
                            <button type="button" class="btn btn-primary" onclick="sessionManager.rateSession(${session.id})" data-bs-dismiss="modal">
                                <i class="fas fa-star me-1"></i>Rate This Session
                            </button>
                            ` : ''}
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

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('sessionDetailsModal'));
        modal.show();
    }

    /**
     * Show rating modal
     */
    showRatingModal(sessionId) {
        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="ratingModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-star me-2"></i>Rate Your Session
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="ratingForm">
                                <input type="hidden" id="sessionIdForRating" value="${sessionId}">
                                <input type="hidden" id="selectedRating" value="0">
                                
                                <div class="mb-3 text-center">
                                    <div class="rating-stars">
                                        ${Array(5).fill(0).map((_, i) => `
                                        <i class="far fa-star rating-star" data-rating="${i + 1}" onclick="sessionManager.setRating(${i + 1})"></i>
                                        `).join('')}
                                    </div>
                                    <div class="mt-2 text-muted">Click to select rating</div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="reviewText" class="form-label">Your Review (Optional)</label>
                                    <textarea class="form-control" id="reviewText" rows="4" 
                                        placeholder="Share your experience with this tutor..."></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="submitRatingBtn" disabled>
                                <i class="fas fa-paper-plane me-1"></i>Submit Rating
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('ratingModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal and set up event listeners
        const modal = new bootstrap.Modal(document.getElementById('ratingModal'));
        modal.show();

        // Add event listener for rating stars
        document.querySelectorAll('.rating-star').forEach(star => {
            star.addEventListener('click', () => {
                const rating = parseInt(star.dataset.rating);
                this.setRating(rating);
            });

            // Add hover effects
            star.addEventListener('mouseenter', () => {
                const rating = parseInt(star.dataset.rating);
                document.querySelectorAll('.rating-star').forEach((s, i) => {
                    if (i < rating) {
                        s.classList.remove('far');
                        s.classList.add('fas');
                    }
                });
            });

            star.addEventListener('mouseleave', () => {
                const currentRating = parseInt(document.getElementById('selectedRating').value);
                document.querySelectorAll('.rating-star').forEach((s, i) => {
                    if (i < currentRating) {
                        s.classList.remove('far');
                        s.classList.add('fas');
                    } else {
                        s.classList.remove('fas');
                        s.classList.add('far');
                    }
                });
            });
        });

        // Add submit event listener
        document.getElementById('submitRatingBtn').addEventListener('click', () => {
            const sessionId = document.getElementById('sessionIdForRating').value;
            const rating = parseInt(document.getElementById('selectedRating').value);
            const reviewText = document.getElementById('reviewText').value;

            this.manager.submitRating(sessionId, rating, reviewText);
        });
    }

    /**
     * Set the rating in the rating modal
     */
    setRating(rating) {
        document.getElementById('selectedRating').value = rating;

        // Update stars
        document.querySelectorAll('.rating-star').forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas');
            } else {
                star.classList.remove('fas');
                star.classList.add('far');
            }
        });

        // Enable submit button
        document.getElementById('submitRatingBtn').disabled = false;
    }

    /**
     * Update the rating display in the session history
     */
    updateRatingDisplay(sessionId, rating) {
        const ratingDiv = document.querySelector(`[data-session-id="${sessionId}"] .rating`);
        if (ratingDiv) {
            ratingDiv.innerHTML = Array(5).fill(0).map((_, i) =>
                `<i class="fas fa-star ${i < rating ? 'text-warning' : 'text-muted'}"></i>`
            ).join('');
        }
    }

    /**
     * Show reschedule modal
     */
    showRescheduleModal(session) {
        // Create modal HTML
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
                            <form id="rescheduleForm">
                                <input type="hidden" id="sessionIdForReschedule" value="${session.id}">
                                
                                <div class="mb-3">
                                    <label class="form-label">Current Schedule</label>
                                    <p class="text-muted">
                                        ${session.scheduled_date} at ${this.formatTime(session.scheduled_time)}
                                        with ${session.tutor_name}
                                    </p>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="newDate" class="form-label">New Date</label>
                                    <input type="date" class="form-control" id="newDate" min="${today}" max="${maxDateStr}" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="newTime" class="form-label">New Time</label>
                                    <select class="form-control" id="newTime" required>
                                        <option value="">Select a new date first</option>
                                    </select>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="rescheduleReason" class="form-label">Reason for Rescheduling</label>
                                    <textarea class="form-control" id="rescheduleReason" rows="3" 
                                        placeholder="Please provide a reason for rescheduling..."></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="sessionManager.submitReschedule(
                                ${session.id},
                                document.getElementById('newDate').value,
                                document.getElementById('newTime').value,
                                document.getElementById('rescheduleReason').value
                            )">
                                <i class="fas fa-calendar-check me-1"></i>Reschedule
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

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('rescheduleModal'));
        modal.show();

        // Add event listener for date change to load available times
        document.getElementById('newDate').addEventListener('change', async (e) => {
            const newDate = e.target.value;
            const timeSelect = document.getElementById('newTime');

            if (!newDate) {
                timeSelect.innerHTML = '<option value="">Select a date first</option>';
                return;
            }

            timeSelect.innerHTML = '<option value="">Loading available times...</option>';

            try {
                const response = await fetch(`/student/api/tutor-availability?tutor_id=${session.tutor_id}&date=${newDate}`);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to load available times');
                }

                const availableSlots = data.slots || [];

                if (availableSlots.length === 0) {
                    timeSelect.innerHTML = '<option value="">No available times for this date</option>';
                } else {
                    timeSelect.innerHTML = '<option value="">Select a time</option>';
                    availableSlots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot;
                        option.textContent = this.formatTime(slot);
                        timeSelect.appendChild(option);
                    });
                }
            } catch (error) {
                timeSelect.innerHTML = '<option value="">Error loading available times</option>';
                console.error('Error loading available times:', error);
            }
        });
    }
}

// Initialize the session manager when the DOM is loaded
let sessionManager;
document.addEventListener('DOMContentLoaded', function () {
    sessionManager = new SessionManager();

    // Set up global functions for HTML button onclick attributes
    window.cancelSession = (sessionId) => sessionManager.cancelSession(sessionId);
    window.endSession = (sessionId) => sessionManager.endSession(sessionId);
    window.viewSessionDetails = (sessionId) => sessionManager.viewSessionDetails(sessionId);
    window.rateSession = (sessionId) => sessionManager.rateSession(sessionId);
    window.setRating = (rating) => sessionManager.ui.setRating(rating);
    window.rescheduleSession = (sessionId) => sessionManager.rescheduleSession(sessionId);
    window.bookAgain = (tutorId, courseId) => sessionManager.openScheduleModal(tutorId, courseId);
});
