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

@tutor_bp.route('/my-courses')
@login_required
@role_required('tutor')
def my_courses():
    """My Courses page - courses assigned to this tutor"""
    conn = get_db_connection()
    try:
        # Get courses where this tutor has taught sessions or is assigned
        courses = conn.execute('''
            SELECT DISTINCT c.id, c.title, c.description, c.difficulty_level, 
                   c.estimated_duration, c.created_at,
                   COUNT(DISTINCT s.id) as total_sessions,
                   COUNT(DISTINCT s.student_id) as students_taught,
                   COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) as completed_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'scheduled' THEN s.id END) as upcoming_sessions,
                   COUNT(DISTINCT l.id) as total_lessons,
                   AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating END) as avg_rating,
                   MAX(s.scheduled_date) as last_session_date,
                   MIN(s.scheduled_date) as first_session_date
            FROM courses c 
            JOIN sessions s ON c.id = s.course_id 
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN reviews r ON s.id = r.session_id
            WHERE s.tutor_id = ?
            GROUP BY c.id, c.title, c.description, c.difficulty_level, 
                     c.estimated_duration, c.created_at
            ORDER BY MAX(s.scheduled_date) DESC
        ''', (session['user_id'],)).fetchall()
        
        # Convert to list of dictionaries for easier template handling
        courses_list = []
        for course in courses:
            course_dict = dict(course)
            course_dict['avg_rating'] = round(course_dict['avg_rating'], 1) if course_dict['avg_rating'] else None
            courses_list.append(course_dict)

        return render_template('tutor_courses.html', courses=courses_list)
        
    except sqlite3.Error as e:
        flash('Error loading courses data', 'error')
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
        
        # TODO: Implement session creation logic
        return jsonify({'status': 'success', 'message': 'Session created successfully'})
        
    except Exception as e:
        return jsonify({'error': 'Failed to create session'}), 500

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

# ========== COURSE STUDENTS API ENDPOINTS ==========

@tutor_bp.route('/api/courses/<int:course_id>/students')
@login_required
@role_required('tutor')
def get_course_students(course_id):
    """Get students enrolled in a specific course that this tutor has taught"""
    conn = get_db_connection()
    try:
        # Verify this tutor has taught this course
        tutor_course_relation = conn.execute('''
            SELECT DISTINCT s.course_id FROM sessions s 
            WHERE s.tutor_id = ? AND s.course_id = ?
        ''', (session['user_id'], course_id)).fetchone()
        
        if not tutor_course_relation:
            return jsonify({'error': 'You do not have access to this course'}), 403
        
        # Get students enrolled in this course with their progress and session stats
        students = conn.execute('''
            SELECT DISTINCT u.id, u.username, u.email, e.enrolled_date, e.status,
                   COUNT(DISTINCT s.id) as total_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) as completed_sessions,
                   COUNT(DISTINCT CASE WHEN s.status = 'scheduled' THEN s.id END) as upcoming_sessions,
                   COUNT(DISTINCT l.id) as total_lessons,
                   COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons,
                   AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating END) as avg_rating,
                   MAX(s.scheduled_date) as last_session_date
            FROM users u 
            JOIN enrollments e ON u.id = e.student_id
            JOIN sessions s ON u.id = s.student_id AND s.course_id = e.course_id AND s.tutor_id = ?
            LEFT JOIN lessons l ON e.course_id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = u.id
            LEFT JOIN reviews r ON s.id = r.session_id AND r.student_id = u.id
            WHERE e.course_id = ? AND e.status IN ('active', 'completed')
            GROUP BY u.id, u.username, u.email, e.enrolled_date, e.status
            ORDER BY e.enrolled_date DESC
        ''', (session['user_id'], course_id)).fetchall()
        
        # Calculate progress percentage for each student
        students_with_progress = []
        for student in students:
            progress = 0
            if student['total_lessons'] > 0:
                progress = (student['completed_lessons'] / student['total_lessons']) * 100
            
            student_dict = dict(student)
            student_dict['progress'] = round(progress, 1)
            student_dict['avg_rating'] = round(student_dict['avg_rating'], 1) if student_dict['avg_rating'] else None
            students_with_progress.append(student_dict)
        
        return jsonify({
            'status': 'success',
            'students': students_with_progress
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()
