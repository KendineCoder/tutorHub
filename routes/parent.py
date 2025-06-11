"""
Parent dashboard and functionality
"""
from flask import Blueprint, render_template, session, request, jsonify, flash, redirect, url_for
from utils.auth import login_required, role_required
from utils.database import get_db_connection
import sqlite3
import re

parent_bp = Blueprint('parent', __name__, url_prefix='/parent')


@parent_bp.route('/')
@login_required
@role_required('parent')
def dashboard():
    """Parent dashboard overview"""
    conn = get_db_connection()
    try:
        # Get children
        children = conn.execute('''
            SELECT id, username, email, created_at 
            FROM users 
            WHERE parent_id = ? AND role = 'student' AND is_active = 1
            ORDER BY created_at DESC
        ''', (session['user_id'],)).fetchall()

        # Get children's progress summary
        children_progress = conn.execute('''
            SELECT u.id, u.username, 
                   COUNT(DISTINCT e.course_id) as total_courses,
                   ROUND(AVG(p.progress), 1) as avg_progress,
                   COUNT(DISTINCT CASE WHEN e.status = 'completed' THEN e.course_id END) as completed_courses
            FROM users u 
            LEFT JOIN enrollments e ON u.id = e.student_id AND e.status = 'active'
            LEFT JOIN progress p ON u.id = p.user_id
            WHERE u.parent_id = ? AND u.role = 'student' AND u.is_active = 1
            GROUP BY u.id, u.username
            ORDER BY u.username
        ''', (session['user_id'],)).fetchall()

        # Get recent sessions
        recent_sessions = conn.execute('''
            SELECT s.*, u1.username as student_name, u2.username as tutor_name, c.title as course_title
            FROM sessions s
            JOIN users u1 ON s.student_id = u1.id
            JOIN users u2 ON s.tutor_id = u2.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE u1.parent_id = ? 
            ORDER BY s.scheduled_date DESC, s.scheduled_time DESC
            LIMIT 5
        ''', (session['user_id'],)).fetchall()

        return render_template('parent_dashboard.html', 
                             children=children,
                             children_progress=children_progress,
                             recent_sessions=recent_sessions)
    finally:
        conn.close()


@parent_bp.route('/children')
@login_required
@role_required('parent')
def children():
    """Children management page"""
    conn = get_db_connection()
    try:
        # Get all children
        children = conn.execute('''
            SELECT id, username, email, created_at, is_active
            FROM users 
            WHERE parent_id = ? AND role = 'student'
            ORDER BY is_active DESC, username
        ''', (session['user_id'],)).fetchall()

        return render_template('parent_children.html', children=children)
    finally:
        conn.close()


@parent_bp.route('/api/add-child', methods=['POST'])
@login_required
@role_required('parent')
def add_child():
    """Add a new child account"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        # Validation
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400

        conn = get_db_connection()
        try:
            # Check if username already exists
            existing_user = conn.execute('''
                SELECT id FROM users WHERE username = ?
            ''', (username,)).fetchone()

            if existing_user:
                return jsonify({'error': 'Username already exists'}), 400

            # Check if email already exists
            existing_email = conn.execute('''
                SELECT id FROM users WHERE email = ?
            ''', (email,)).fetchone()

            if existing_email:
                return jsonify({'error': 'Email already exists'}), 400            # Create the child account
            # Note: This system uses plain text passwords (not recommended for production)
            conn.execute('''
                INSERT INTO users (username, email, password, role, parent_id, is_active)
                VALUES (?, ?, ?, 'student', ?, 1)
            ''', (username, email, password, session['user_id']))

            conn.commit()
            return jsonify({'success': True, 'message': 'Child account created successfully'})

        except sqlite3.IntegrityError as e:
            return jsonify({'error': 'Account creation failed due to existing data'}), 400
        except sqlite3.Error as e:
            return jsonify({'error': 'Database error occurred'}), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'error': 'Failed to create child account'}), 500


@parent_bp.route('/api/toggle-child/<int:child_id>', methods=['POST'])
@login_required
@role_required('parent')
def toggle_child_status(child_id):
    """Toggle child account active status"""
    try:
        conn = get_db_connection()
        try:
            # Verify the child belongs to this parent
            child = conn.execute('''
                SELECT id, is_active, username
                FROM users 
                WHERE id = ? AND parent_id = ? AND role = 'student'
            ''', (child_id, session['user_id'])).fetchone()

            if not child:
                return jsonify({'error': 'Child not found'}), 404

            new_status = 0 if child['is_active'] else 1
            action = 'activated' if new_status else 'deactivated'

            conn.execute('''
                UPDATE users 
                SET is_active = ?
                WHERE id = ?
            ''', (new_status, child_id))

            conn.commit()
            return jsonify({
                'success': True, 
                'message': f"Child account {action} successfully",
                'new_status': new_status
            })

        except sqlite3.Error as e:
            return jsonify({'error': 'Database error occurred'}), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'error': 'Failed to update child account'}), 500