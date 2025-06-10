/**
 * User Management JavaScript Module
 * Handles admin user management functionality
 */

class UserManager {
    constructor() {
        this.baseUrl = '/api';
        this.currentFilters = {
            search: '',
            role: 'all',
            status: 'all'
        };
        this.initializeEventListeners();
        this.initializeSearchAndFilters();
    }

    initializeEventListeners() {
        // View user details
        document.addEventListener('click', (e) => {
            if (e.target.matches('.view-user-btn, .view-user-btn *')) {
                const userId = e.target.closest('.view-user-btn').dataset.userId;
                this.viewUserDetails(userId);
            }

            if (e.target.matches('.edit-user-btn, .edit-user-btn *')) {
                const userId = e.target.closest('.edit-user-btn').dataset.userId;
                this.editUser(userId);
            }

            if (e.target.matches('.toggle-status-btn, .toggle-status-btn *')) {
                const userId = e.target.closest('.toggle-status-btn').dataset.userId;
                this.toggleUserStatus(userId);
            }

            if (e.target.matches('.reset-password-btn, .reset-password-btn *')) {
                const userId = e.target.closest('.reset-password-btn').dataset.userId;
                this.resetUserPassword(userId);
            }

            if (e.target.matches('.delete-user-btn, .delete-user-btn *')) {
                const userId = e.target.closest('.delete-user-btn').dataset.userId;
                this.deleteUser(userId);
            }
        });
    }

    initializeSearchAndFilters() {
        // Search functionality
        const searchInput = document.getElementById('searchUsers');
        const roleFilter = document.getElementById('roleFilter');
        const statusFilter = document.getElementById('statusFilter');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.currentFilters.search = e.target.value;
                this.applyFilters();
            });
        }

        if (roleFilter) {
            roleFilter.addEventListener('change', (e) => {
                this.currentFilters.role = e.target.value;
                this.applyFilters();
            });
        }

        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.currentFilters.status = e.target.value;
                this.applyFilters();
            });
        }
    }

    applyFilters() {
        const rows = document.querySelectorAll('.user-row');

        rows.forEach(row => {
            const username = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const email = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
            const role = row.querySelector('.role-badge').textContent.toLowerCase().replace(/\s+/g, '_');
            const status = row.querySelector('.status-badge').textContent.toLowerCase();

            let showRow = true;

            // Apply search filter
            if (this.currentFilters.search) {
                const searchTerm = this.currentFilters.search.toLowerCase();
                showRow = showRow && (username.includes(searchTerm) || email.includes(searchTerm));
            }

            // Apply role filter
            if (this.currentFilters.role !== 'all') {
                showRow = showRow && role.includes(this.currentFilters.role);
            }

            // Apply status filter
            if (this.currentFilters.status !== 'all') {
                showRow = showRow && status === this.currentFilters.status;
            }

            row.style.display = showRow ? '' : 'none';
        });
    }

    async viewUserDetails(userId) {
        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                this.displayUserDetails(result.user);
            } else {
                showNotification(result.error || 'Failed to load user details', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while loading user details', 'error');
        }
    }

    displayUserDetails(user) {
        const content = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-user me-2"></i>Basic Information</h6>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>ID:</strong></td>
                            <td>${user.id}</td>
                        </tr>
                        <tr>
                            <td><strong>Username:</strong></td>
                            <td>${user.username}</td>
                        </tr>
                        <tr>
                            <td><strong>Email:</strong></td>
                            <td>${user.email}</td>
                        </tr>
                        <tr>
                            <td><strong>Role:</strong></td>
                            <td><span class="badge bg-primary">${user.role.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Status:</strong></td>
                            <td><span class="badge bg-${user.is_active ? 'success' : 'secondary'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Joined:</strong></td>
                            <td>${new Date(user.created_at).toLocaleDateString()}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-chart-bar me-2"></i>Activity Statistics</h6>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>Enrolled Courses:</strong></td>
                            <td>${user.stats.enrolled_courses}</td>
                        </tr>
                        <tr>
                            <td><strong>Completed Sessions:</strong></td>
                            <td>${user.stats.completed_sessions}</td>
                        </tr>
                        <tr>
                            <td><strong>Progress Records:</strong></td>
                            <td>${user.stats.progress_records}</td>
                        </tr>
                    </table>
                </div>
            </div>
        `;

        document.getElementById('userDetailsContent').innerHTML = content;
        const modal = new bootstrap.Modal(document.getElementById('userDetailsModal'));
        modal.show();
    }

    async editUser(userId) {
        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                this.openEditModal(result.user);
            } else {
                showNotification(result.error || 'Failed to load user data', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while loading user data', 'error');
        }
    }

    openEditModal(user) {
        document.getElementById('editUserId').value = user.id;
        document.getElementById('editUsername').value = user.username;
        document.getElementById('editEmail').value = user.email;
        document.getElementById('editRole').value = user.role;
        document.getElementById('editIsActive').checked = user.is_active;

        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
        modal.show();
    }

    async updateUser() {
        const userId = document.getElementById('editUserId').value;
        const data = {
            username: document.getElementById('editUsername').value,
            email: document.getElementById('editEmail').value,
            role: document.getElementById('editRole').value,
            is_active: document.getElementById('editIsActive').checked
        };

        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('User updated successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                modal.hide();

                // Refresh page to show updated data
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.error || 'Failed to update user', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while updating the user', 'error');
        }
    }

    async toggleUserStatus(userId) {
        if (!confirm('Are you sure you want to toggle this user\'s status?')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}/toggle-status`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification(result.message, 'success');

                // Update UI immediately
                const row = document.querySelector(`[data-user-id="${userId}"]`);
                const statusBadge = row.querySelector('.status-badge');
                const toggleBtn = row.querySelector('.toggle-status-btn i');

                if (result.new_status) {
                    statusBadge.className = 'badge status-badge bg-success';
                    statusBadge.textContent = 'Active';
                    toggleBtn.className = 'fas fa-lock';
                    toggleBtn.parentElement.title = 'Deactivate';
                } else {
                    statusBadge.className = 'badge status-badge bg-secondary';
                    statusBadge.textContent = 'Inactive';
                    toggleBtn.className = 'fas fa-unlock';
                    toggleBtn.parentElement.title = 'Activate';
                }
            } else {
                showNotification(result.error || 'Failed to toggle user status', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while toggling user status', 'error');
        }
    }

    async resetUserPassword(userId) {
        const newPassword = prompt('Enter new password (leave empty for default "password123"):') || 'password123';

        if (!confirm(`Are you sure you want to reset this user's password to "${newPassword}"?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ new_password: newPassword })
            });

            const result = await response.json();

            if (response.ok) {
                showNotification(`${result.message}. New password: ${result.new_password}`, 'success');
            } else {
                showNotification(result.error || 'Failed to reset password', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while resetting password', 'error');
        }
    } async deleteUser(userId) {
        // Show deletion choice modal
        this.showDeletionChoiceModal(userId);
    }

    showDeletionChoiceModal(userId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'deletionChoiceModal';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Delete User</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Choose how you want to remove this user:</p>
                        <div class="d-grid gap-2">
                            <button type="button" class="btn btn-warning" onclick="userManager.performSoftDelete(${userId})">
                                <i class="fas fa-user-slash me-2"></i>
                                Deactivate Account
                                <small class="d-block text-muted">Preserve data but prevent login</small>
                            </button>
                            <button type="button" class="btn btn-danger" onclick="userManager.performHardDelete(${userId})">
                                <i class="fas fa-trash-alt me-2"></i>
                                Permanently Delete
                                <small class="d-block text-muted">Remove user and all associated data</small>
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Clean up modal when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    async performSoftDelete(userId) {
        if (!confirm('Are you sure you want to deactivate this user? This will preserve their data but prevent login.')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification(result.message, 'success');

                // Update UI immediately
                const row = document.querySelector(`[data-user-id="${userId}"]`);
                const statusBadge = row.querySelector('.status-badge');
                const toggleBtn = row.querySelector('.toggle-status-btn i');

                statusBadge.className = 'badge status-badge bg-secondary';
                statusBadge.textContent = 'Inactive';
                toggleBtn.className = 'fas fa-unlock';
                toggleBtn.parentElement.title = 'Activate';
            } else {
                showNotification(result.error || 'Failed to deactivate user', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while deactivating the user', 'error');
        }

        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('deletionChoiceModal')).hide();
    }

    async performHardDelete(userId) {
        if (!confirm('⚠️ WARNING: This will permanently delete the user and ALL associated data. This action CANNOT be undone. Are you absolutely sure?')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/users/${userId}/hard-delete`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                showNotification(result.message, 'success');

                // Remove the row from the table completely
                const row = document.querySelector(`[data-user-id="${userId}"]`);
                if (row) {
                    row.remove();
                }

                // Update user count if displayed
                this.updateUserCounts();
            } else {
                showNotification(result.error || 'Failed to permanently delete user', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while permanently deleting the user', 'error');
        }

        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('deletionChoiceModal')).hide();
    }

    updateUserCounts() {
        // Update statistics if they exist on the page
        const statsElements = document.querySelectorAll('[data-stat]');
        if (statsElements.length > 0) {
            // Refresh the page to get accurate counts
            window.location.reload();
        }
    }

    async createUser() {
        const data = {
            username: document.getElementById('addUsername').value,
            email: document.getElementById('addEmail').value,
            password: document.getElementById('addPassword').value,
            role: document.getElementById('addRole').value
        };

        // Validation
        if (!data.username || !data.email || !data.password || !data.role) {
            showNotification('Please fill in all fields', 'warning');
            return;
        }

        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams(data)
            });

            if (response.redirected || response.ok) {
                showNotification('User created successfully!', 'success');

                // Close modal and clear form
                const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
                modal.hide();
                document.getElementById('addUserForm').reset();

                // Refresh page to show new user
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Failed to create user - email may already exist', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred while creating the user', 'error');
        }
    }
}

// Global functions for onclick handlers
function updateUser() {
    window.userManager.updateUser();
}

function createUser() {
    window.userManager.createUser();
}

function clearFilters() {
    document.getElementById('searchUsers').value = '';
    document.getElementById('roleFilter').value = 'all';
    document.getElementById('statusFilter').value = 'all';
    window.userManager.currentFilters = { search: '', role: 'all', status: 'all' };
    window.userManager.applyFilters();
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    window.userManager = new UserManager();
});
