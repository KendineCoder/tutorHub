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

# ========== SESSION SCHEDULING API ENDPOINTS ==========

@tutor_bp.route('/api/tutors/available', methods=['GET'])
@login_required
def get_available_tutors():
    """Get list of available tutors with their specialties"""
    conn = get_db_connection()
    try:
        tutors = conn.execute('''
            SELECT u.id, u.username, u.email,
                   GROUP_CONCAT(DISTINCT c.title) as subjects
            FROM users u
            LEFT JOIN sessions s ON u.id = s.tutor_id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE u.role = 'tutor'
            GROUP BY u.id, u.username, u.email
            ORDER BY u.username
        ''').fetchall()
        
        tutors_list = [dict(tutor) for tutor in tutors]
        return jsonify({'tutors': tutors_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@tutor_bp.route('/api/tutors/<int:tutor_id>/availability', methods=['GET'])
@login_required
def get_tutor_availability(tutor_id):
    """Get tutor's availability schedule"""
    date = request.args.get('date')  # YYYY-MM-DD format
    
    conn = get_db_connection()
    try:
        # Get tutor availability
        availability = conn.execute('''
            SELECT day_of_week, start_time, end_time, is_available
            FROM tutor_availability
            WHERE tutor_id = ? AND is_available = 1
            ORDER BY day_of_week, start_time
        ''', (tutor_id,)).fetchall()
        
        # Get existing sessions for the date if provided
        existing_sessions = []
        if date:
            existing_sessions = conn.execute('''
                SELECT scheduled_time, duration
                FROM sessions
                WHERE tutor_id = ? AND scheduled_date = ? AND status IN ('scheduled', 'completed')
            ''', (tutor_id, date)).fetchall()
        
        availability_list = [dict(slot) for slot in availability]
        sessions_list = [dict(session) for session in existing_sessions]
        
        return jsonify({
            'availability': availability_list,
            'existing_sessions': sessions_list
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@tutor_bp.route('/api/sessions', methods=['POST'])
@login_required
@role_required('student')
def create_session():
    """Create a new tutoring session"""
    data = request.get_json()
    
    required_fields = ['tutor_id', 'scheduled_date', 'scheduled_time', 'duration']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    try:
        # Check if tutor is available at the requested time
        day_of_week = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').weekday()
        day_of_week = (day_of_week + 1) % 7  # Convert to Sunday=0 format
        
        availability = conn.execute('''
            SELECT * FROM tutor_availability
            WHERE tutor_id = ? AND day_of_week = ? AND is_available = 1
            AND start_time <= ? AND end_time >= ?
        ''', (data['tutor_id'], day_of_week, data['scheduled_time'], data['scheduled_time'])).fetchone()
        
        if not availability:
            return jsonify({'error': 'Tutor is not available at the requested time'}), 400
        
        # Check for conflicting sessions
        conflict = conn.execute('''
            SELECT id FROM sessions
            WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
            AND status IN ('scheduled', 'completed')
        ''', (data['tutor_id'], data['scheduled_date'], data['scheduled_time'])).fetchone()
        
        if conflict:
            return jsonify({'error': 'Time slot is already booked'}), 400
        
        # Create the session
        cursor = conn.execute('''
            INSERT INTO sessions (student_id, tutor_id, course_id, scheduled_date, 
                                scheduled_time, duration, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?)
        ''', (session['user_id'], data['tutor_id'], data.get('course_id'),
              data['scheduled_date'], data['scheduled_time'], 
              data['duration'], data.get('notes', ''))
        )
        
        session_id = cursor.lastrowid
        conn.commit()
        
        # Create notification for tutor
        conn.execute('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, 'info')
        ''', (data['tutor_id'], 'New Session Scheduled', 
              f'A new tutoring session has been scheduled with you on {data["scheduled_date"]} at {data["scheduled_time"]}'))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'message': 'Session scheduled successfully'
        }), 201
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@tutor_bp.route('/api/sessions/<int:session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    """Update session details or status"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Get session and check permissions
        session_data = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if user has permission to update
        if (session['user_role'] not in ['admin'] and 
            session['user_id'] not in [session_data['student_id'], session_data['tutor_id']]):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update allowed fields
        update_fields = []
        update_values = []
        
        if 'status' in data:
            update_fields.append('status = ?')
            update_values.append(data['status'])
        
        if 'notes' in data:
            update_fields.append('notes = ?')
            update_values.append(data['notes'])
        
        if 'scheduled_date' in data and session['user_role'] in ['admin', 'tutor']:
            update_fields.append('scheduled_date = ?')
            update_values.append(data['scheduled_date'])
        
        if 'scheduled_time' in data and session['user_role'] in ['admin', 'tutor']:
            update_fields.append('scheduled_time = ?')
            update_values.append(data['scheduled_time'])
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        update_values.append(session_id)
        
        conn.execute(f'''
            UPDATE sessions 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)
        
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Session updated successfully'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@tutor_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def cancel_session(session_id):
    """Cancel a session"""
    conn = get_db_connection()
    try:
        # Get session and check permissions
        session_data = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if user has permission to cancel
        if (session['user_role'] not in ['admin'] and 
            session['user_id'] not in [session_data['student_id'], session_data['tutor_id']]):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update status to cancelled instead of deleting
        conn.execute('UPDATE sessions SET status = ? WHERE id = ?', ('cancelled', session_id))
        conn.commit()
        
        # Notify the other party
        other_user_id = (session_data['tutor_id'] if session['user_id'] == session_data['student_id'] 
                        else session_data['student_id'])
        
        conn.execute('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, 'warning')
        ''', (other_user_id, 'Session Cancelled', 
              f'A tutoring session on {session_data["scheduled_date"]} at {session_data["scheduled_time"]} has been cancelled'))
        
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Session cancelled successfully'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@tutor_bp.route('/api/users/<int:user_id>/sessions', methods=['GET'])
@login_required
def get_user_sessions(user_id):
    """Get sessions for a specific user"""
    # Check permissions
    if session['user_id'] != user_id and session['user_role'] not in ['admin', 'tutor']:
        return jsonify({'error': 'Permission denied'}), 403
    
    status_filter = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 10))
    
    conn = get_db_connection()
    try:
        query = '''
            SELECT s.*, 
                   student.username as student_name,
                   tutor.username as tutor_name,
                   c.title as course_title
            FROM sessions s
            LEFT JOIN users student ON s.student_id = student.id
            LEFT JOIN users tutor ON s.tutor_id = tutor.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE (s.student_id = ? OR s.tutor_id = ?)
        '''
        
        params = [user_id, user_id]
        
        if status_filter != 'all':
            query += ' AND s.status = ?'
            params.append(status_filter)
        
        query += ' ORDER BY s.scheduled_date DESC, s.scheduled_time DESC LIMIT ?'
        params.append(limit)
        
        sessions = conn.execute(query, params).fetchall()
        sessions_list = [dict(s) for s in sessions]
        
        return jsonify({'sessions': sessions_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()