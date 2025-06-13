// Course Management JavaScript Module

class CourseManager {
    constructor() {
        this.baseUrl = '/content/api';
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Edit course buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.edit-course-btn, .edit-course-btn *')) {
                const courseId = e.target.closest('.edit-course-btn').dataset.courseId;
                this.editCourse(courseId);
            }

            if (e.target.matches('.delete-course-btn, .delete-course-btn *')) {
                const courseId = e.target.closest('.delete-course-btn').dataset.courseId;
                this.deleteCourse(courseId);
            }
        });
    } async editCourse(courseId) {
        try {
            // Fetch current course data
            console.log(`Fetching course data from: ${this.baseUrl}/courses/${courseId}`);
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server returned ${response.status}: ${response.statusText}`);
            }

            const course = await response.json();

            // Open edit modal with current data
            this.openEditModal(course);

        } catch (error) {
            console.error('Error editing course:', error);
            showNotification('Failed to load course data: ' + error.message, 'error');
        }
    } async deleteCourse(courseId) {
        const confirmed = await this.showConfirmDialog(
            'Delete Course',
            'Are you sure you want to delete this course? This action cannot be undone.'
        );

        if (!confirmed) return;

        try {
            console.log(`Deleting course at: ${this.baseUrl}/courses/${courseId}`);
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server returned ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            showNotification('Course deleted successfully!', 'success');

            // Remove course row from table
            const courseRow = document.querySelector(`[data-course-id="${courseId}"]`).closest('tr');
            if (courseRow) {
                courseRow.remove();
            } else {
                // If row can't be found, reload the page
                setTimeout(() => location.reload(), 1000);
            }
        } catch (error) {
            console.error('Error deleting course:', error);
            showNotification('Failed to delete course: ' + error.message, 'error');
        }
    }

    openEditModal(course) {
        const modalHtml = `
            <div class="modal fade" id="editCourseModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-edit me-2"></i>Edit Course
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editCourseForm">
                                <input type="hidden" id="editCourseId" value="${course.id}">
                                <div class="mb-3">
                                    <label for="editCourseTitle" class="form-label">Course Title</label>
                                    <input type="text" class="form-control" id="editCourseTitle" 
                                           value="${course.title}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="editCourseDescription" class="form-label">Description</label>
                                    <textarea class="form-control" id="editCourseDescription" 
                                              rows="4" required>${course.description}</textarea>
                                </div>
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="editDifficultyLevel" class="form-label">Difficulty Level</label>
                                            <select class="form-select" id="editDifficultyLevel" required>
                                                <option value="beginner" ${course.difficulty_level === 'beginner' ? 'selected' : ''}>Beginner</option>
                                                <option value="intermediate" ${course.difficulty_level === 'intermediate' ? 'selected' : ''}>Intermediate</option>
                                                <option value="advanced" ${course.difficulty_level === 'advanced' ? 'selected' : ''}>Advanced</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="editEstimatedDuration" class="form-label">Duration (hours)</label>
                                            <input type="number" class="form-control" id="editEstimatedDuration" 
                                                   value="${course.estimated_duration}" min="1" max="200" required>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="courseManager.updateCourse()">
                                <i class="fas fa-save me-1"></i>Update Course
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('editCourseModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editCourseModal'));
        modal.show();
    } async updateCourse() {
        const courseId = document.getElementById('editCourseId').value;
        const data = {
            title: document.getElementById('editCourseTitle').value,
            description: document.getElementById('editCourseDescription').value,
            difficulty_level: document.getElementById('editDifficultyLevel').value,
            estimated_duration: parseInt(document.getElementById('editEstimatedDuration').value)
        };

        try {
            console.log(`Updating course at: ${this.baseUrl}/courses/${courseId}`, data);
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server returned ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            showNotification('Course updated successfully!', 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editCourseModal'));
            modal.hide();

            // Refresh page to show updated data
            setTimeout(() => location.reload(), 1000);
        } catch (error) {
            console.error('Error updating course:', error);
            showNotification('Failed to update course: ' + error.message, 'error');
        }
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
                                <button type="button" class="btn btn-danger" id="confirmBtn">Delete</button>
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

// Initialize course manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    // Ensure showNotification function exists (fallback if it doesn't)
    if (typeof showNotification !== 'function') {
        window.showNotification = function (message, type = 'info') {
            console.log(`Notification (${type}):`, message);

            // Create a simple alert for notifications
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
            alertDiv.setAttribute('role', 'alert');
            alertDiv.innerHTML = `
                <div>${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;

            // Insert at top of page
            document.body.insertBefore(alertDiv, document.body.firstChild);

            // Remove after 5 seconds
            setTimeout(() => {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.remove(), 150);
            }, 5000);
        };
    }

    if (window.location.pathname.includes('/content')) {
        window.courseManager = new CourseManager();
        console.log('Course Manager initialized!');
    }
});

// Add global error handler to catch any unhandled errors
window.addEventListener('error', function (event) {
    console.error('Global error:', event.error);
    showNotification('An error occurred: ' + (event.error?.message || 'Unknown error'), 'error');
});
