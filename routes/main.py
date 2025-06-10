"""
Main navigation routes
"""
from flask import Blueprint, session, redirect, url_for

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if 'user_id' in session:
        role = session['user_role']
        if role == 'student':
            return redirect(url_for('student.dashboard'))
        elif role == 'tutor':
            return redirect(url_for('tutor.dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'parent':
            return redirect(url_for('parent.dashboard'))
        elif role == 'content_manager':
            return redirect(url_for('content.dashboard'))
    return redirect(url_for('auth.login'))