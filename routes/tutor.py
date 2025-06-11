"""
Tutor dashboard and functionality
"""
from flask import Blueprint, render_template, session, request, jsonify
from utils.auth import login_required, role_required
from utils.database import get_db_connection
from datetime import datetime
import sqlite3

tutor_bp = Blueprint('tutor', __name__, url_prefix='/tutor')

# ========== DASHBOARD ROUTES ==========

@tutor_bp.route('/')
@login_required
@role_required('tutor')
def dashboard():
    conn = get_db_connection()

    # Get assigned students
    students = conn.execute('''
        SELECT DISTINCT u.id, u.username, u.email 
        FROM users u 
        JOIN sessions s ON u.id = s.student_id 
        WHERE s.tutor_id = ?
    ''', (session['user_id'],)).fetchall()

    # Get upcoming sessions
    sessions = conn.execute('''
        SELECT s.*, u.username as student_name 
        FROM sessions s 
        JOIN users u ON s.student_id = u.id 
        WHERE s.tutor_id = ? AND s.scheduled_date >= date('now')
        ORDER BY s.scheduled_date ASC
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('tutor_dashboard.html', students=students, sessions=sessions)

# ========== TUTOR AVAILABILITY ROUTES ==========

@tutor_bp.route('/availability')
@login_required
@role_required('tutor')
def availability():
    """Tutor availability management page"""
    conn = get_db_connection()
    try:
        # Get current availability
        availability = conn.execute('''
            SELECT * FROM tutor_availability 
            WHERE tutor_id = ? 
            ORDER BY day_of_week, start_time
        ''', (session['user_id'],)).fetchall()

        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        return render_template('tutor_availability.html', availability=availability, days=days)
    finally:
        conn.close()

# ========== SESSION SCHEDULING API ENDPOINTS ==========

@tutor_bp.route('/api/availability', methods=['POST'])
@login_required
@role_required('tutor')
def add_availability():
    """Add availability slot for current tutor"""
    try:
        data = request.get_json()
        required_fields = ['day', 'start_time', 'end_time']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        try:
            # Check for overlapping slots
            existing = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE tutor_id = ? AND day_of_week = ? 
                AND ((start_time <= ? AND end_time > ?) OR (start_time < ? AND end_time >= ?))
            ''', (session['user_id'], data['day'], data['start_time'], data['start_time'],
                  data['end_time'], data['end_time'])).fetchone()
            
            if existing:
                return jsonify({'error': 'Time slot overlaps with existing availability'}), 400
            
            # Add new availability slot
            conn.execute('''
                INSERT INTO tutor_availability (tutor_id, day_of_week, start_time, end_time, is_available)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], data['day'], data['start_time'], 
                  data['end_time'], data.get('is_available', True)))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Availability added successfully'
            })
            
        except Exception as e:
            return jsonify({'error': 'Failed to add availability: ' + str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to add availability: ' + str(e)}), 500
