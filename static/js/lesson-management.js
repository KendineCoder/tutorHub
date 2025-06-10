// Lesson Management JavaScript Module

class LessonManager {
    constructor() {
        this.baseUrl = '/api';
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Event delegation for lesson actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('.edit-lesson-btn, .edit-lesson-btn *')) {
                const lessonId = e.target.closest('.edit-lesson-btn').dataset.lessonId;
                this.editLesson(lessonId);
            }

            if (e.target.matches('.delete-lesson-btn, .delete-lesson-btn *')) {
                const lessonId = e.target.closest('.delete-lesson-btn').dataset.lessonId;
                this.deleteLesson(lessonId);
            }

            if (e.target.matches('.reorder-lessons-btn, .reorder-lessons-btn *')) {
                const courseId = e.target.closest('.reorder-lessons-btn').dataset.courseId;
                this.openReorderModal(courseId);
            }            if (e.target.matches('.add-lesson-btn, .add-lesson-btn *')) {
                const courseId = e.target.closest('.add-lesson-btn').dataset.courseId;
                window.location.href = `/content/lesson/create/${courseId}`;
            }
        });
    }

    async editLesson(lessonId) {
        try {
            // Fetch current lesson data
            const response = await fetch(`${this.baseUrl}/lessons/${lessonId}`);
            const lesson = await response.json();

            if (!response.ok) {
                throw new Error(lesson.error || 'Failed to fetch lesson data');
            }

            // Open edit modal with current data
            this.openEditModal(lesson);

        } catch (error) {
            showNotification('Failed to load lesson data: ' + error.message, 'error');
        }
    }

    async deleteLesson(lessonId) {
        const confirmed = await this.showConfirmDialog(
            'Delete Lesson',
            'Are you sure you want to delete this lesson? This action cannot be undone.'
        );

        if (!confirmed) return;

        try {
            const response = await fetch(`${this.baseUrl}/lessons/${lessonId}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Lesson deleted successfully!', 'success');
                // Remove lesson card from DOM
                const lessonCard = document.querySelector(`[data-lesson-id="${lessonId}"]`).closest('.lesson-card');
                if (lessonCard) {
                    lessonCard.remove();
                }
                // Refresh page to update lesson numbering
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(result.error || 'Failed to delete lesson');
            }
        } catch (error) {
            showNotification('Failed to delete lesson: ' + error.message, 'error');
        }
    }

    openEditModal(lesson) {
        const modalHtml = `
            <div class="modal fade" id="editLessonModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-edit me-2"></i>Edit Lesson
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editLessonForm">
                                <input type="hidden" id="editLessonId" value="${lesson.id}">
                                <div class="row">
                                    <div class="col-md-8">
                                        <div class="mb-3">
                                            <label for="editLessonTitle" class="form-label">Lesson Title</label>
                                            <input type="text" class="form-control" id="editLessonTitle" 
                                                   value="${lesson.title}" required>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <label for="editLessonOrder" class="form-label">Lesson Order</label>
                                            <input type="number" class="form-control" id="editLessonOrder" 
                                                   value="${lesson.lesson_order}" min="1" required>
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="editLessonContent" class="form-label">Content</label>
                                    <textarea class="form-control" id="editLessonContent" 
                                              rows="6" required>${lesson.content}</textarea>
                                </div>
                                <div class="mb-3">
                                    <label for="editLessonDuration" class="form-label">Duration (minutes)</label>
                                    <input type="number" class="form-control" id="editLessonDuration" 
                                           value="${lesson.duration || 60}" min="5" max="480">
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="lessonManager.updateLesson()">
                                <i class="fas fa-save me-1"></i>Update Lesson
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('editLessonModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editLessonModal'));
        modal.show();
    }

    async updateLesson() {
        const lessonId = document.getElementById('editLessonId').value;
        const data = {
            title: document.getElementById('editLessonTitle').value,
            content: document.getElementById('editLessonContent').value,
            lesson_order: parseInt(document.getElementById('editLessonOrder').value),
            duration: parseInt(document.getElementById('editLessonDuration').value)
        };

        try {
            const response = await fetch(`${this.baseUrl}/lessons/${lessonId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Lesson updated successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editLessonModal'));
                modal.hide();

                // Refresh page to show updated data
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(result.error || 'Failed to update lesson');
            }
        } catch (error) {
            showNotification('Failed to update lesson: ' + error.message, 'error');
        }
    }

    async openReorderModal(courseId) {
        try {
            // Fetch course lessons
            const response = await fetch(`${this.baseUrl}/courses/${courseId}/lessons`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch lessons');
            }

            const lessons = data.lessons || [];

            const modalHtml = `
                <div class="modal fade" id="reorderLessonsModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-sort me-2"></i>Reorder Lessons
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p class="text-muted mb-3">Drag and drop to reorder lessons</p>
                                <div id="sortableLessons" class="list-group">
                                    ${lessons.map(lesson => `
                                        <div class="list-group-item d-flex justify-content-between align-items-center" 
                                             data-lesson-id="${lesson.id}" data-order="${lesson.lesson_order}">
                                            <div>
                                                <i class="fas fa-grip-vertical text-muted me-2"></i>
                                                <strong>Lesson ${lesson.lesson_order}:</strong> ${lesson.title}
                                            </div>
                                            <small class="text-muted">${lesson.duration || 60} min</small>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" onclick="lessonManager.saveReorder()">
                                    <i class="fas fa-save me-1"></i>Save Order
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal if any
            const existingModal = document.getElementById('reorderLessonsModal');
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Initialize sortable (would need SortableJS library for drag-and-drop)
            // For now, we'll use simple up/down buttons
            this.addReorderButtons();

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('reorderLessonsModal'));
            modal.show();

        } catch (error) {
            showNotification('Failed to load lessons: ' + error.message, 'error');
        }
    }

    addReorderButtons() {
        const items = document.querySelectorAll('#sortableLessons .list-group-item');
        items.forEach((item, index) => {
            const buttonsHtml = `
                <div class="btn-group-vertical btn-group-sm ms-2">
                    ${index > 0 ? '<button type="button" class="btn btn-outline-primary btn-sm move-up" data-direction="up"><i class="fas fa-chevron-up"></i></button>' : ''}
                    ${index < items.length - 1 ? '<button type="button" class="btn btn-outline-primary btn-sm move-down" data-direction="down"><i class="fas fa-chevron-down"></i></button>' : ''}
                </div>
            `;
            item.insertAdjacentHTML('beforeend', buttonsHtml);
        });

        // Add event listeners for move buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.move-up')) {
                this.moveLesson(e.target.closest('.list-group-item'), 'up');
            } else if (e.target.closest('.move-down')) {
                this.moveLesson(e.target.closest('.list-group-item'), 'down');
            }
        });
    }

    moveLesson(item, direction) {
        const sibling = direction === 'up' ? item.previousElementSibling : item.nextElementSibling;
        if (sibling) {
            if (direction === 'up') {
                item.parentNode.insertBefore(item, sibling);
            } else {
                item.parentNode.insertBefore(sibling, item);
            }
            this.updateReorderButtons();
        }
    }

    updateReorderButtons() {
        // Remove existing buttons
        document.querySelectorAll('#sortableLessons .btn-group-vertical').forEach(btn => btn.remove());
        // Re-add buttons with correct state
        this.addReorderButtons();
    }

    async saveReorder() {
        const items = document.querySelectorAll('#sortableLessons .list-group-item');
        const updates = [];

        items.forEach((item, index) => {
            const lessonId = item.dataset.lessonId;
            const newOrder = index + 1;
            updates.push({
                id: parseInt(lessonId),
                lesson_order: newOrder
            });
        });

        try {
            // Update each lesson order
            const updatePromises = updates.map(update =>
                fetch(`${this.baseUrl}/lessons/${update.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ lesson_order: update.lesson_order })
                })
            );

            await Promise.all(updatePromises);

            showNotification('Lesson order updated successfully!', 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('reorderLessonsModal'));
            modal.hide();

            // Refresh page
            setTimeout(() => location.reload(), 1000);

        } catch (error) {
            showNotification('Failed to update lesson order: ' + error.message, 'error');
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

// Initialize lesson manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    if (window.location.pathname.includes('/course/') || window.location.pathname.includes('/content')) {
        window.lessonManager = new LessonManager();
    }
});
