// Course Management JavaScript Module

class CourseManager {
    constructor() {
        this.baseUrl = '/api';
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
    }

    async editCourse(courseId) {
        try {
            // Fetch current course data
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`);
            const course = await response.json();

            if (!response.ok) {
                throw new Error(course.error || 'Failed to fetch course data');
            }

            // Open edit modal with current data
            this.openEditModal(course);

        } catch (error) {
            showNotification('Failed to load course data: ' + error.message, 'error');
        }
    }

    async deleteCourse(courseId) {
        const confirmed = await this.showConfirmDialog(
            'Delete Course',
            'Are you sure you want to delete this course? This action cannot be undone.'
        );

        if (!confirmed) return;

        try {
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Course deleted successfully!', 'success');
                // Remove course row from table
                const courseRow = document.querySelector(`[data-course-id="${courseId}"]`).closest('tr');
                if (courseRow) {
                    courseRow.remove();
                }
            } else {
                throw new Error(result.error || 'Failed to delete course');
            }
        } catch (error) {
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
    }

    async updateCourse() {
        const courseId = document.getElementById('editCourseId').value;
        const data = {
            title: document.getElementById('editCourseTitle').value,
            description: document.getElementById('editCourseDescription').value,
            difficulty_level: document.getElementById('editDifficultyLevel').value,
            estimated_duration: parseInt(document.getElementById('editEstimatedDuration').value)
        };

        try {
            const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Course updated successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editCourseModal'));
                modal.hide();

                // Refresh page to show updated data
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(result.error || 'Failed to update course');
            }
        } catch (error) {
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
    if (window.location.pathname.includes('/content')) {
        window.courseManager = new CourseManager();
    }
});
