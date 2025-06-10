// Session Scheduling JavaScript Module

class SessionScheduler {
    constructor() {
        this.baseUrl = '/tutor/api';
        this.selectedTutor = null;
        this.selectedDate = null;
        this.selectedTime = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Initialize scheduling functionality
        document.addEventListener('click', (e) => {
            if (e.target.matches('.schedule-session-btn, .schedule-session-btn *')) {
                this.openScheduleModal();
            }

            if (e.target.matches('.cancel-session-btn, .cancel-session-btn *')) {
                const sessionId = e.target.closest('.cancel-session-btn').dataset.sessionId;
                this.cancelSession(sessionId);
            }

            if (e.target.matches('.reschedule-session-btn, .reschedule-session-btn *')) {
                const sessionId = e.target.closest('.reschedule-session-btn').dataset.sessionId;
                this.rescheduleSession(sessionId);
            }
        });

        // Date change handler
        document.addEventListener('change', (e) => {
            if (e.target.id === 'sessionDate') {
                this.updateAvailableTimeSlots();
            }
            if (e.target.id === 'tutorSelect') {
                this.updateAvailableTimeSlots();
            }
        });
    }

    async openScheduleModal(courseId = null, tutorId = null) {
        const modalHtml = `
            <div class="modal fade" id="scheduleSessionModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-calendar-plus me-2"></i>Schedule Tutoring Session
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="scheduleSessionForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="courseSelect" class="form-label">Course</label>
                                            <select class="form-select" id="courseSelect" name="course_id">
                                                <option value="">Select a course (optional)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="tutorSelect" class="form-label">Tutor *</label>
                                            <select class="form-select" id="tutorSelect" name="tutor_id" required>
                                                <option value="">Select a tutor</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="sessionDate" class="form-label">Date *</label>
                                            <input type="date" class="form-control" id="sessionDate" 
                                                   name="scheduled_date" required min="${this.getTodayDate()}">
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="sessionDuration" class="form-label">Duration *</label>
                                            <select class="form-select" id="sessionDuration" name="duration" required>
                                                <option value="30">30 minutes</option>
                                                <option value="60" selected>60 minutes</option>
                                                <option value="90">90 minutes</option>
                                                <option value="120">120 minutes</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="timeSlots" class="form-label">Available Time Slots *</label>
                                    <div id="timeSlots" class="time-slots-container">
                                        <div class="text-muted text-center py-3">
                                            <i class="fas fa-clock me-2"></i>
                                            Please select a tutor and date to view available times
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="sessionNotes" class="form-label">Notes</label>
                                    <textarea class="form-control" id="sessionNotes" name="notes" 
                                              rows="3" placeholder="Any specific topics or requests for the session"></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="scheduleBtn" disabled>
                                <i class="fas fa-calendar-check me-1"></i>Schedule Session
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('scheduleSessionModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Load courses and tutors
        await this.loadCoursesAndTutors();

        // Pre-select course and tutor if provided
        if (courseId) {
            document.getElementById('courseSelect').value = courseId;
        }
        if (tutorId) {
            document.getElementById('tutorSelect').value = tutorId;
            this.updateAvailableTimeSlots();
        }

        // Add schedule button handler
        document.getElementById('scheduleBtn').addEventListener('click', () => {
            this.scheduleSession();
        });

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('scheduleSessionModal'));
        modal.show();
    }
    async loadCoursesAndTutors() {
        try {
            // Load enrolled courses
            const coursesResponse = await fetch('/student/api/courses/enrolled');
            const coursesData = await coursesResponse.json();

            const courseSelect = document.getElementById('courseSelect');
            if (coursesData.courses) {
                coursesData.courses.forEach(course => {
                    courseSelect.innerHTML += `<option value="${course.id}">${course.title}</option>`;
                });
            }

            // Load available tutors
            const tutorsResponse = await fetch('/student/api/tutors/find');
            const tutorsData = await tutorsResponse.json();

            const tutorSelect = document.getElementById('tutorSelect');
            if (tutorsData.tutors) {
                tutorsData.tutors.forEach(tutor => {
                    const subjects = tutor.subjects ? ` - ${tutor.subjects}` : '';
                    tutorSelect.innerHTML += `<option value="${tutor.id}">${tutor.username}${subjects}</option>`;
                });
            }

        } catch (error) {
            console.error('Error loading courses and tutors:', error);
            showNotification('Failed to load courses and tutors', 'error');
        }
    }

    async updateAvailableTimeSlots() {
        const tutorId = document.getElementById('tutorSelect').value;
        const date = document.getElementById('sessionDate').value;
        const timeSlotsContainer = document.getElementById('timeSlots');
        const scheduleBtn = document.getElementById('scheduleBtn');

        if (!tutorId || !date) {
            timeSlotsContainer.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-clock me-2"></i>
                    Please select a tutor and date to view available times
                </div>
            `;
            scheduleBtn.disabled = true;
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/tutors/${tutorId}/availability?date=${date}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch availability');
            }

            this.renderTimeSlots(data.availability, data.existing_sessions, date);

        } catch (error) {
            console.error('Error fetching availability:', error);
            timeSlotsContainer.innerHTML = `
                <div class="text-danger text-center py-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error loading availability
                </div>
            `;
        }
    }

    renderTimeSlots(availability, existingSessions, date) {
        const timeSlotsContainer = document.getElementById('timeSlots');
        const selectedDayOfWeek = new Date(date).getDay();

        // Filter availability for the selected day
        const dayAvailability = availability.filter(slot => slot.day_of_week === selectedDayOfWeek);

        if (dayAvailability.length === 0) {
            timeSlotsContainer.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-calendar-times me-2"></i>
                    Tutor is not available on this day
                </div>
            `;
            return;
        }

        let slotsHtml = '<div class="row g-2">';

        dayAvailability.forEach(slot => {
            const timeSlots = this.generateTimeSlots(slot.start_time, slot.end_time, 60); // 60-minute slots

            timeSlots.forEach(timeSlot => {
                const isBooked = existingSessions.some(session =>
                    session.scheduled_time === timeSlot
                );

                const slotClass = isBooked ? 'btn-outline-secondary disabled' : 'btn-outline-primary time-slot-btn';
                const slotText = isBooked ? `${timeSlot} (Booked)` : timeSlot;

                slotsHtml += `
                    <div class="col-6 col-md-4 col-lg-3">
                        <button type="button" class="btn ${slotClass} w-100 mb-2" 
                                data-time="${timeSlot}" ${isBooked ? 'disabled' : ''}>
                            ${slotText}
                        </button>
                    </div>
                `;
            });
        });

        slotsHtml += '</div>';
        timeSlotsContainer.innerHTML = slotsHtml;

        // Add time slot selection handlers
        document.querySelectorAll('.time-slot-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Remove previous selection
                document.querySelectorAll('.time-slot-btn').forEach(b => {
                    b.classList.remove('btn-primary');
                    b.classList.add('btn-outline-primary');
                });

                // Mark as selected
                e.target.classList.remove('btn-outline-primary');
                e.target.classList.add('btn-primary');

                this.selectedTime = e.target.dataset.time;
                document.getElementById('scheduleBtn').disabled = false;
            });
        });
    }

    generateTimeSlots(startTime, endTime, intervalMinutes) {
        const slots = [];
        const start = new Date(`2000-01-01 ${startTime}`);
        const end = new Date(`2000-01-01 ${endTime}`);

        let current = new Date(start);
        while (current < end) {
            slots.push(current.toTimeString().slice(0, 5));
            current.setMinutes(current.getMinutes() + intervalMinutes);
        }

        return slots;
    }

    async scheduleSession() {
        const form = document.getElementById('scheduleSessionForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        if (!this.selectedTime) {
            showNotification('Please select a time slot', 'warning');
            return;
        }

        data.scheduled_time = this.selectedTime;
        data.tutor_id = parseInt(data.tutor_id);
        data.duration = parseInt(data.duration);

        if (data.course_id) {
            data.course_id = parseInt(data.course_id);
        }

        const scheduleBtn = document.getElementById('scheduleBtn');
        const originalText = scheduleBtn.innerHTML;
        scheduleBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Scheduling...';
        scheduleBtn.disabled = true;

        try {
            const response = await fetch(`${this.baseUrl}/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Session scheduled successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleSessionModal'));
                modal.hide();

                // Refresh page to show new session
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(result.error || 'Failed to schedule session');
            }
        } catch (error) {
            showNotification('Failed to schedule session: ' + error.message, 'error');
        } finally {
            scheduleBtn.innerHTML = originalText;
            scheduleBtn.disabled = false;
        }
    }

    async cancelSession(sessionId) {
        const confirmed = await this.showConfirmDialog(
            'Cancel Session',
            'Are you sure you want to cancel this session? This action cannot be undone.'
        );

        if (!confirmed) return;

        try {
            const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Session cancelled successfully!', 'success');
                // Update UI to show cancelled status
                const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
                if (sessionElement) {
                    sessionElement.querySelector('.session-status').textContent = 'Cancelled';
                    sessionElement.querySelector('.session-status').className = 'badge bg-danger session-status';
                }
            } else {
                throw new Error(result.error || 'Failed to cancel session');
            }
        } catch (error) {
            showNotification('Failed to cancel session: ' + error.message, 'error');
        }
    }

    async rescheduleSession(sessionId) {
        // For now, this will open a new scheduling modal
        // In a more advanced implementation, this would pre-populate the form
        showNotification('Please cancel this session and create a new one for now', 'info');
        // TODO: Implement proper rescheduling
    }

    getTodayDate() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }

    async showConfirmDialog(title, message) {
        return new Promise((resolve) => {
            const modalHtml = `
                <div class="modal fade" id="confirmModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-danger" id="confirmBtn">Confirm</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = new bootstrap.Modal(document.getElementById('confirmModal'));

            document.getElementById('confirmBtn').addEventListener('click', () => {
                resolve(true);
                modal.hide();
            });

            document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
                document.getElementById('confirmModal').remove();
                resolve(false);
            });

            modal.show();
        });
    }
}

// Initialize session scheduler when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    window.sessionScheduler = new SessionScheduler();
});

// Global function for backwards compatibility
function openScheduleModal(courseId = null, tutorId = null) {
    if (window.sessionScheduler) {
        window.sessionScheduler.openScheduleModal(courseId, tutorId);
    }
}
