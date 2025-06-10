"""
Admin dashboard and user management
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
import sqlite3
from utils.auth import login_required, role_required
from utils.database import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@role_required('admin')
def dashboard():
    conn = get_db_connection()

    # Get statistics
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    total_courses = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()['count']
    total_sessions = conn.execute('SELECT COUNT(*) as count FROM sessions').fetchone()['count']
    
    # Get recent registrations
    recent_users = conn.execute('''
        SELECT id, username, email, role, created_at, is_active 
        FROM users 
        ORDER BY created_at DESC LIMIT 10
    ''').fetchall()

    conn.close()
    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_courses=total_courses,
                           total_sessions=total_sessions,
                           recent_users=recent_users)


@admin_bp.route('/users')
@login_required
@role_required('admin')
def user_management():
    """User management page for admins"""
    conn = get_db_connection()
    try:
        # Get all users with additional details
        users = conn.execute('''
            SELECT id, username, email, role, created_at, is_active
            FROM users 
            ORDER BY created_at DESC
        ''').fetchall()
        
        # Get statistics
        stats = {
            'total_users': len(users),
            'active_users': len([u for u in users if u['is_active']]),
            'students': len([u for u in users if u['role'] == 'student']),
            'tutors': len([u for u in users if u['role'] == 'tutor']),
            'content_managers': len([u for u in users if u['role'] == 'content_manager']),
            'parents': len([u for u in users if u['role'] == 'parent']),
            'admins': len([u for u in users if u['role'] == 'admin'])
        }
        
        return render_template('user_management.html', users=users, stats=stats)
        
    except sqlite3.Error as e:
        flash('Error loading user data', 'error')
        return redirect(url_for('admin.dashboard'))
    finally:
        conn.close()


# User management API endpoints will be in api.py