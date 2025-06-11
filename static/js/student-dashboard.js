/**
 * Student Dashboard JavaScript
 * Handles dashboard-specific functionality including session management
 */

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

// Make functions globally available
window.endSession = endSession;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    console.log('Student dashboard JavaScript loaded');
});