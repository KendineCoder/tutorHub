"""
Tutor dashboard and functionality
"""
from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, flash
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

@tutor_bp.route('/students')
@login_required
@role_required('tutor')
def my_students():
    """My Students page with detailed metrics"""
    conn = get_db_connection()
    try:
        # Get students with comprehensive metrics
        students = conn.execute('''
            SELECT DISTINCT u.id, u.username, u.email, u.created_at,
                   COUNT(DISTINCT s.id) as total_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) as completed_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'scheduled' THEN s.id END) as upcoming_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'cancelled' THEN s.id END) as cancelled_sessions,
                   COUNT(DISTINCT s.course_id) as courses_taught,
                   AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating END) as avg_rating,
                   MAX(s.scheduled_date) as last_session_date,
                   MIN(s.scheduled_date) as first_session_date
            FROM users u 
            JOIN sessions s ON u.id = s.student_id 
            LEFT JOIN reviews r ON s.id = r.session_id
            WHERE s.tutor_id = ?
            GROUP BY u.id, u.username, u.email, u.created_at
            ORDER BY MAX(s.scheduled_date) DESC
        ''', (session['user_id'],)).fetchall()

        # Get course progress summary for each student
        students_with_progress = []
        for student in students:
            # Get average progress across courses taught by this tutor
            progress_data = conn.execute('''
                SELECT AVG(
                    CASE WHEN l.total_lessons > 0 
                    THEN (CAST(p.completed_lessons as FLOAT) / l.total_lessons) * 100 
                    ELSE 0 END
                ) as avg_progress
                FROM (
                    SELECT DISTINCT c.id, COUNT(DISTINCT les.id) as total_lessons
                    FROM courses c 
                    JOIN sessions s ON c.id = s.course_id 
                    LEFT JOIN lessons les ON c.id = les.course_id
                    WHERE s.tutor_id = ? AND s.student_id = ?
                    GROUP BY c.id
                ) l
                LEFT JOIN (
                    SELECT c.id as course_id, 
                           COUNT(DISTINCT CASE WHEN pr.completed = 1 THEN pr.lesson_id END) as completed_lessons
                    FROM courses c 
                    JOIN sessions s ON c.id = s.course_id 
                    LEFT JOIN lessons les ON c.id = les.course_id
                    LEFT JOIN progress pr ON les.id = pr.lesson_id AND pr.user_id = ?
                    WHERE s.tutor_id = ? AND s.student_id = ?
                    GROUP BY c.id
                ) p ON l.id = p.course_id
            ''', (session['user_id'], student['id'], student['id'], session['user_id'], student['id'])).fetchone()
            
            student_dict = dict(student)
            student_dict['avg_progress'] = round(progress_data['avg_progress'] or 0, 1)
            student_dict['avg_rating'] = round(student_dict['avg_rating'], 1) if student_dict['avg_rating'] else None
            students_with_progress.append(student_dict)

        return render_template('tutor_students.html', students=students_with_progress)
        
    except sqlite3.Error as e:
        flash('Error loading student data', 'error')
        return redirect(url_for('tutor.dashboard'))
    finally:
        conn.close()

# ========== STUDENT PROGRESS ROUTES ==========

@tutor_bp.route('/api/student-progress/<int:student_id>')
@login_required
@role_required('tutor')
def get_student_progress(student_id):
    """Get detailed progress information for a student"""
    conn = get_db_connection()
    try:
        # Verify this tutor has taught this student
        tutor_student_relation = conn.execute('''
            SELECT DISTINCT s.student_id FROM sessions s 
            WHERE s.tutor_id = ? AND s.student_id = ?
        ''', (session['user_id'], student_id)).fetchone()
        
        if not tutor_student_relation:
            return jsonify({'error': 'You do not have access to this student\'s progress'}), 403
            
        # Get student basic info
        student = conn.execute('''
            SELECT id, username, email FROM users 
            WHERE id = ? AND role = 'student'
        ''', (student_id,)).fetchone()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
              # Get student's course progress - ONLY for courses where this tutor has taught the student
        courses_progress = conn.execute('''
            SELECT DISTINCT c.id, c.title, c.description, e.enrolled_date, e.status,
                   COUNT(DISTINCT l.id) as total_lessons,
                   COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons,
                   MAX(p.updated_at) as last_activity,
                   COUNT(DISTINCT s.id) as sessions_with_tutor
            FROM courses c 
            JOIN enrollments e ON c.id = e.course_id 
            JOIN sessions s ON c.id = s.course_id AND s.student_id = e.student_id AND s.tutor_id = ?
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            WHERE e.student_id = ? AND e.status IN ('active', 'completed')
            GROUP BY c.id, c.title, c.description, e.enrolled_date, e.status
            ORDER BY e.enrolled_date DESC
        ''', (session['user_id'], student_id, student_id)).fetchall()
        
        # Calculate progress percentage for each course
        progress_data = []
        for course in courses_progress:
            progress_percentage = 0
            if course['total_lessons'] > 0:
                progress_percentage = (course['completed_lessons'] / course['total_lessons']) * 100
                progress_data.append({
                'course_id': course['id'],
                'title': course['title'],
                'description': course['description'],
                'enrolled_date': course['enrolled_date'],
                'status': course['status'],
                'progress': round(progress_percentage, 1),
                'completed_lessons': course['completed_lessons'],
                'total_lessons': course['total_lessons'],
                'last_activity': course['last_activity'],
                'sessions_with_tutor': course['sessions_with_tutor']
            })
        
        # Get sessions history with this tutor
        sessions_history = conn.execute('''
            SELECT s.scheduled_date, s.scheduled_time, s.status, s.duration,
                   c.title as course_title, r.rating, r.review_text
            FROM sessions s
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN reviews r ON s.id = r.session_id
            WHERE s.tutor_id = ? AND s.student_id = ?
            ORDER BY s.scheduled_date DESC
        ''', (session['user_id'], student_id)).fetchall()
        
        return jsonify({
            'student': {
                'id': student['id'],
                'username': student['username'],
                'email': student['email']
            },
            'courses': progress_data,
            'sessions_history': [dict(session) for session in sessions_history]
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

# ========== SESSION SCHEDULING API ENDPOINTS ==========

@tutor_bp.route('/api/sessions', methods=['POST'])
@login_required
@role_required('tutor')
def create_session():
    """Create a new tutoring session as a tutor"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['student_id', 'scheduled_date', 'scheduled_time', 'duration']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        try:
            # Verify the student exists
            student = conn.execute('SELECT id FROM users WHERE id = ? AND role = "student"', 
                                 (data['student_id'],)).fetchone()
            if not student:
                return jsonify({'error': 'Invalid student selected'}), 400
            
            # Check if current tutor is available at the requested time
            from datetime import datetime
            scheduled_datetime = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
            day_of_week = scheduled_datetime.weekday() + 1  # Convert to 1-7 where Monday=1
            if day_of_week == 7:  # Sunday should be 0
                day_of_week = 0
                
            availability = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE tutor_id = ? AND day_of_week = ? 
                AND start_time <= ? AND end_time > ? AND is_available = 1
            ''', (session['user_id'], day_of_week, data['scheduled_time'], data['scheduled_time'])).fetchone()
            
            if not availability:
                return jsonify({'error': 'You are not available at the requested time. Please update your availability.'}), 400
            
            # Check for scheduling conflicts
            existing_session = conn.execute('''
                SELECT id FROM sessions 
                WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
                AND status IN ('scheduled', 'rescheduled', 'in_progress')
            ''', (session['user_id'], data['scheduled_date'], data['scheduled_time'])).fetchone()
            
            if existing_session:
                return jsonify({'error': 'This time slot is already booked'}), 400
            
            # Create the session
            session_id = conn.execute('''
                INSERT INTO sessions (student_id, tutor_id, course_id, scheduled_date, 
                                    scheduled_time, duration, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', CURRENT_TIMESTAMP)
            ''', (data['student_id'], session['user_id'], data.get('course_id'),
                  data['scheduled_date'], data['scheduled_time'], data['duration'])).lastrowid
            
            conn.commit()
            
            # Create notification for student if notifications table exists
            try:
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, 'info')
                ''', (data['student_id'], 'New Session Scheduled', 
                      f'Your tutor has scheduled a session for {data["scheduled_date"]} at {data["scheduled_time"]}'))
                conn.commit()
            except sqlite3.Error:
                # Ignore if notifications table doesn't exist
                pass
            
            return jsonify({
                'status': 'success', 
                'message': 'Session scheduled successfully',
                'session_id': session_id
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to create session: ' + str(e)}), 500

@tutor_bp.route('/api/courses/available', methods=['GET'])
@login_required
@role_required('tutor')
def get_available_courses():
    """Get courses available for tutoring sessions"""
    conn = get_db_connection()
    try:
        # Get courses that the tutor has taught or is qualified to teach
        courses = conn.execute('''
            SELECT DISTINCT c.id, c.title, c.description, c.difficulty_level
            FROM courses c
            LEFT JOIN sessions s ON c.id = s.course_id
            WHERE s.tutor_id = ? OR c.created_by = ?
            ORDER BY c.title
        ''', (session['user_id'], session['user_id'])).fetchall()
        
        courses_list = [dict(course) for course in courses]
        return jsonify({'courses': courses_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@tutor_bp.route('/api/availability', methods=['GET'])
@login_required
@role_required('tutor')
def get_my_availability():
    """Get tutor's own availability schedule"""
    date = request.args.get('date')  # YYYY-MM-DD format
    
    conn = get_db_connection()
    try:
        # Get tutor availability
        availability = conn.execute('''
            SELECT day_of_week, start_time, end_time, is_available
            FROM tutor_availability
            WHERE tutor_id = ? AND is_available = 1
            ORDER BY day_of_week, start_time
        ''', (session['user_id'],)).fetchall()
        
        # Get existing sessions for the date if provided
        existing_sessions = []
        if date:
            existing_sessions = conn.execute('''
                SELECT scheduled_time, duration
                FROM sessions
                WHERE tutor_id = ? AND scheduled_date = ? AND status IN ('scheduled', 'rescheduled', 'in_progress')
            ''', (session['user_id'], date)).fetchall()
        
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

# ========== AVAILABILITY MANAGEMENT ROUTES ==========

@tutor_bp.route('/api/availability', methods=['POST'])
@login_required
@role_required('tutor')
def create_availability():
    """Create or update availability time slots"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['day_of_week', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        day_of_week = data['day_of_week']
        start_time = data['start_time']
        end_time = data['end_time']
        is_available = data.get('is_available', True)
        
        # Validate day_of_week
        if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
            return jsonify({'error': 'day_of_week must be an integer between 0 (Sunday) and 6 (Saturday)'}), 400
        
        # Validate time format and logic
        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_time, '%H:%M')
            end_dt = datetime.strptime(end_time, '%H:%M')
            if start_dt >= end_dt:
                return jsonify({'error': 'start_time must be before end_time'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid time format. Use HH:MM format (e.g., 09:00)'}), 400
        
        conn = get_db_connection()
        try:
            # Check for overlapping time slots
            overlapping = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE tutor_id = ? AND day_of_week = ? AND is_available = 1
                AND (
                    (start_time <= ? AND end_time > ?) OR
                    (start_time < ? AND end_time >= ?) OR
                    (start_time >= ? AND end_time <= ?)
                )
            ''', (session['user_id'], day_of_week, start_time, start_time, end_time, end_time, start_time, end_time)).fetchone()
            
            if overlapping:
                return jsonify({'error': 'This time slot overlaps with an existing availability slot'}), 400
            
            # Insert new availability slot
            availability_id = conn.execute('''
                INSERT INTO tutor_availability (tutor_id, day_of_week, start_time, end_time, is_available, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session['user_id'], day_of_week, start_time, end_time, is_available)).lastrowid
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Availability slot created successfully',
                'availability_id': availability_id
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to create availability: ' + str(e)}), 500

@tutor_bp.route('/api/availability/<int:availability_id>', methods=['PUT'])
@login_required
@role_required('tutor')
def update_availability(availability_id):
    """Update an existing availability time slot"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        try:
            # Verify the availability slot belongs to this tutor
            existing = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE id = ? AND tutor_id = ?
            ''', (availability_id, session['user_id'])).fetchone()
            
            if not existing:
                return jsonify({'error': 'Availability slot not found or access denied'}), 404
            
            # Build update query dynamically based on provided fields
            update_fields = []
            params = []
            
            if 'start_time' in data:
                try:
                    datetime.strptime(data['start_time'], '%H:%M')
                    update_fields.append('start_time = ?')
                    params.append(data['start_time'])
                except ValueError:
                    return jsonify({'error': 'Invalid start_time format. Use HH:MM format'}), 400
            
            if 'end_time' in data:
                try:
                    datetime.strptime(data['end_time'], '%H:%M')
                    update_fields.append('end_time = ?')
                    params.append(data['end_time'])
                except ValueError:
                    return jsonify({'error': 'Invalid end_time format. Use HH:MM format'}), 400
            
            if 'is_available' in data:
                update_fields.append('is_available = ?')
                params.append(data['is_available'])
            
            if not update_fields:
                return jsonify({'error': 'No valid fields to update'}), 400
            
            # Add availability_id to params
            params.append(availability_id)
            
            # Update the availability slot
            update_query = f"UPDATE tutor_availability SET {', '.join(update_fields)} WHERE id = ?"
            conn.execute(update_query, params)
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Availability slot updated successfully'
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to update availability: ' + str(e)}), 500

@tutor_bp.route('/api/availability/<int:availability_id>', methods=['DELETE'])
@login_required
@role_required('tutor')
def delete_availability(availability_id):
    """Delete an availability time slot"""
    try:
        conn = get_db_connection()
        try:
            # Verify the availability slot belongs to this tutor
            existing = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE id = ? AND tutor_id = ?
            ''', (availability_id, session['user_id'])).fetchone()
            
            if not existing:
                return jsonify({'error': 'Availability slot not found or access denied'}), 404            # Get the availability slot details first
            availability_slot = conn.execute('''
                SELECT day_of_week, start_time, end_time 
                FROM tutor_availability 
                WHERE id = ? AND tutor_id = ?
            ''', (availability_id, session['user_id'])).fetchone()
            
            if not availability_slot:
                return jsonify({'error': 'Availability slot not found'}), 404
              # For now, let's simplify and just check if there are any upcoming sessions for this tutor
            # and let the user decide. We can make this more restrictive later if needed.
            scheduled_sessions = conn.execute('''
                SELECT COUNT(*) as count FROM sessions s
                WHERE s.tutor_id = ? 
                AND s.status IN ('scheduled', 'rescheduled', 'in_progress')
                AND s.scheduled_date >= date('now')
            ''', (session['user_id'],)).fetchone()
            
            # Only show warning for very recent/immediate sessions, not all future sessions
            immediate_sessions = conn.execute('''
                SELECT COUNT(*) as count FROM sessions s
                WHERE s.tutor_id = ? 
                AND s.status IN ('scheduled', 'rescheduled', 'in_progress')
                AND s.scheduled_date BETWEEN date('now') AND date('now', '+7 days')
            ''', (session['user_id'],)).fetchone()
            
            # We'll allow deletion but add a warning for immediate sessions
            warning_message = None
            if immediate_sessions and immediate_sessions['count'] > 0:
                warning_message = f'Note: You have {immediate_sessions["count"]} sessions scheduled in the next 7 days. Please ensure they don\'t conflict with this availability deletion.'
              # Delete the availability slot
            conn.execute('DELETE FROM tutor_availability WHERE id = ?', (availability_id,))
            conn.commit()
            
            response_data = {
                'status': 'success',
                'message': 'Availability slot deleted successfully'
            }
            
            if warning_message:
                response_data['warning'] = warning_message
            
            return jsonify(response_data)
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to delete availability: ' + str(e)}), 500

# ========== SESSIONS MANAGEMENT ROUTES ==========

@tutor_bp.route('/sessions')
@login_required
@role_required('tutor')
def sessions():
    """Tutor sessions page with filtering and management options"""
    conn = get_db_connection()
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        date_filter = request.args.get('date', 'all')
        
        # Base query for sessions
        base_query = '''
            SELECT s.id, s.scheduled_date, s.scheduled_time, s.duration, s.status, s.created_at,
                   u.username as student_name, u.email as student_email,
                   c.title as course_title, c.id as course_id,
                   r.rating, r.review_text
            FROM sessions s
            JOIN users u ON s.student_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN reviews r ON s.id = r.session_id
            WHERE s.tutor_id = ?
        '''
        params = [session['user_id']]
        
        # Apply status filter
        if status_filter != 'all':
            base_query += ' AND s.status = ?'
            params.append(status_filter)
        
        # Apply date filter
        if date_filter == 'upcoming':
            base_query += ' AND s.scheduled_date >= date("now")'
        elif date_filter == 'past':
            base_query += ' AND s.scheduled_date < date("now")'
        elif date_filter == 'today':
            base_query += ' AND s.scheduled_date = date("now")'
        elif date_filter == 'this_week':
            base_query += ' AND s.scheduled_date BETWEEN date("now") AND date("now", "+7 days")'
        
        base_query += ' ORDER BY s.scheduled_date DESC, s.scheduled_time DESC'
        
        sessions_data = conn.execute(base_query, params).fetchall()
        
        # Get session statistics
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled_sessions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_sessions,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_sessions,
                COUNT(CASE WHEN scheduled_date >= date("now") THEN 1 END) as upcoming_sessions
            FROM sessions 
            WHERE tutor_id = ?
        ''', (session['user_id'],)).fetchone()
        
        return render_template('tutor_sessions.html', 
                             sessions=sessions_data, 
                             stats=dict(stats),
                             current_status_filter=status_filter,
                             current_date_filter=date_filter)
        
    except sqlite3.Error as e:
        flash('Error loading sessions data', 'error')
        return redirect(url_for('tutor.dashboard'))
    finally:
        conn.close()

@tutor_bp.route('/api/sessions/<int:session_id>/cancel', methods=['POST'])
@login_required
@role_required('tutor')
def cancel_session(session_id):
    """Cancel a session"""
    try:
        data = request.get_json()
        cancellation_reason = data.get('reason', 'Cancelled by tutor')
        
        conn = get_db_connection()
        try:
            # Verify the session belongs to this tutor and can be cancelled
            session_data = conn.execute('''
                SELECT id, student_id, scheduled_date, scheduled_time, status 
                FROM sessions 
                WHERE id = ? AND tutor_id = ?
            ''', (session_id, session['user_id'])).fetchone()
            
            if not session_data:
                return jsonify({'error': 'Session not found or access denied'}), 404
            
            if session_data['status'] in ['completed', 'cancelled']:
                return jsonify({'error': 'Cannot cancel a session that is already completed or cancelled'}), 400
            
            # Check if cancellation is allowed (e.g., not too close to session time)
            from datetime import datetime, timedelta
            session_datetime = datetime.strptime(f"{session_data['scheduled_date']} {session_data['scheduled_time']}", '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            
            # Allow cancellation up to 1 hour before session (configurable)
            if session_datetime - now < timedelta(hours=1):
                return jsonify({'error': 'Cannot cancel session less than 1 hour before scheduled time'}), 400
            
            # Update session status
            conn.execute('''
                UPDATE sessions 
                SET status = 'cancelled', cancellation_reason = ?, cancelled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (cancellation_reason, session_id))
            
            # Create notification for student if notifications table exists
            try:
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, 'warning')
                ''', (session_data['student_id'], 'Session Cancelled', 
                      f'Your session scheduled for {session_data["scheduled_date"]} at {session_data["scheduled_time"]} has been cancelled. Reason: {cancellation_reason}'))
            except sqlite3.Error:
                # Ignore if notifications table doesn't exist
                pass
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Session cancelled successfully'
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to cancel session: ' + str(e)}), 500

@tutor_bp.route('/api/sessions/<int:session_id>/reschedule', methods=['POST'])
@login_required
@role_required('tutor')
def reschedule_session(session_id):
    """Reschedule a session"""
    try:
        data = request.get_json()
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        
        if not new_date or not new_time:
            return jsonify({'error': 'New date and time are required'}), 400
        
        conn = get_db_connection()
        try:
            # Verify the session belongs to this tutor
            session_data = conn.execute('''
                SELECT id, student_id, scheduled_date, scheduled_time, status 
                FROM sessions 
                WHERE id = ? AND tutor_id = ?
            ''', (session_id, session['user_id'])).fetchone()
            
            if not session_data:
                return jsonify({'error': 'Session not found or access denied'}), 404
            
            if session_data['status'] not in ['scheduled']:
                return jsonify({'error': 'Can only reschedule scheduled sessions'}), 400
            
            # Check tutor availability for new time
            from datetime import datetime
            new_datetime = datetime.strptime(new_date, '%Y-%m-%d')
            day_of_week = new_datetime.weekday() + 1
            if day_of_week == 7:
                day_of_week = 0
                
            availability = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE tutor_id = ? AND day_of_week = ? 
                AND start_time <= ? AND end_time > ? AND is_available = 1
            ''', (session['user_id'], day_of_week, new_time, new_time)).fetchone()
            
            if not availability:
                return jsonify({'error': 'You are not available at the new requested time'}), 400
            
            # Check for conflicts
            existing_session = conn.execute('''
                SELECT id FROM sessions 
                WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
                AND status IN ('scheduled', 'rescheduled', 'in_progress') AND id != ?
            ''', (session['user_id'], new_date, new_time, session_id)).fetchone()
            
            if existing_session:
                return jsonify({'error': 'The new time slot is already booked'}), 400
            
            # Update session
            conn.execute('''
                UPDATE sessions 
                SET scheduled_date = ?, scheduled_time = ?, status = 'rescheduled', 
                    reschedule_reason = ?, rescheduled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_date, new_time, data.get('reason', 'Rescheduled by tutor'), session_id))
            
            # Create notification for student
            try:
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, 'info')
                ''', (session_data['student_id'], 'Session Rescheduled', 
                      f'Your session has been rescheduled to {new_date} at {new_time}'))
            except sqlite3.Error:
                pass
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Session rescheduled successfully'
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to reschedule session: ' + str(e)}), 500

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
