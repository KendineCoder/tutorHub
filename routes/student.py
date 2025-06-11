"""
Student dashboard and functionality
"""
from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, flash
from utils.auth import login_required, role_required
from utils.database import get_db_connection
from datetime import datetime
import sqlite3

student_bp = Blueprint('student', __name__, url_prefix='/student')

# ========== DASHBOARD ROUTES ==========

@student_bp.route('/')
@login_required
@role_required('student')
def dashboard():
    """Student dashboard overview"""
    conn = get_db_connection()
    try:
        # Get enrolled courses with progress calculation
        courses = conn.execute('''
            SELECT c.*, e.enrolled_date, e.status,
                   COUNT(DISTINCT l.id) as total_lessons,
                   COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons
            FROM courses c 
            JOIN enrollments e ON c.id = e.course_id 
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            WHERE e.student_id = ? AND e.status = 'active'
            GROUP BY c.id, e.enrolled_date, e.status
            ORDER BY e.enrolled_date DESC
        ''', (session['user_id'], session['user_id'])).fetchall()
        
        # Calculate progress for each course
        courses_with_progress = []
        total_progress = 0
        for course in courses:
            progress = 0
            if course['total_lessons'] > 0:
                progress = (course['completed_lessons'] / course['total_lessons']) * 100
            
            course_dict = dict(course)
            course_dict['progress'] = round(progress, 1)
            courses_with_progress.append(course_dict)
            total_progress += progress
        avg_progress = round(total_progress / len(courses_with_progress)) if courses_with_progress else 0

        # Get current session (in progress)
        current_session = conn.execute('''
            SELECT s.*, u.username as tutor_name, c.title as course_title
            FROM sessions s 
            JOIN users u ON s.tutor_id = u.id 
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.student_id = ? AND s.status = 'in_progress'
            ORDER BY s.scheduled_date DESC LIMIT 1
        ''', (session['user_id'],)).fetchone()

        # Get upcoming sessions
        sessions = conn.execute('''
            SELECT s.*, u.username as tutor_name, c.title as course_title
            FROM sessions s 
            JOIN users u ON s.tutor_id = u.id 
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.student_id = ? AND s.status IN ('scheduled', 'rescheduled')
            AND s.scheduled_date >= date('now')
            ORDER BY s.scheduled_date ASC, s.scheduled_time ASC LIMIT 5
        ''', (session['user_id'],)).fetchall()
        
        # Get next session
        next_session = sessions[0] if sessions else None
        
        # Get recent activity (mock data for now)
        recent_activity = [
            {'icon': 'check-circle', 'color': 'success', 'description': 'Completed lesson "Introduction to Python"', 'time_ago': '2 hours ago'},
            {'icon': 'calendar', 'color': 'primary', 'description': 'Scheduled session with John Doe', 'time_ago': '1 day ago'},
            {'icon': 'book', 'color': 'info', 'description': 'Enrolled in "Advanced JavaScript"', 'time_ago': '3 days ago'},
        ]
          # Learning streak (mock data)
        learning_streak = 7

        return render_template('student_dashboard.html', 
                             courses=courses_with_progress, 
                             sessions=sessions,
                             current_session=current_session,
                             next_session=next_session,
                             avg_progress=avg_progress,
                             recent_activity=recent_activity,
                             learning_streak=learning_streak)
    finally:
        conn.close()

@student_bp.route('/my-courses')
@login_required
@role_required('student')
def my_courses():
    """My Courses page - dedicated course management"""
    conn = get_db_connection()
    try:
        # Get enrolled courses with enhanced data
        courses = conn.execute('''
            SELECT c.*, e.enrolled_date, e.status,
                   COUNT(DISTINCT l.id) as total_lessons,
                   COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons
            FROM courses c 
            JOIN enrollments e ON c.id = e.course_id 
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            WHERE e.student_id = ? AND e.status IN ('active', 'paused')
            GROUP BY c.id, e.enrolled_date, e.status
            ORDER BY e.enrolled_date DESC
        ''', (session['user_id'], session['user_id'])).fetchall()
        
        # Calculate progress for each course
        courses_with_progress = []
        for course in courses:
            progress = 0
            if course['total_lessons'] > 0:
                progress = (course['completed_lessons'] / course['total_lessons']) * 100
            
            course_dict = dict(course)
            course_dict['progress'] = round(progress, 1)
            courses_with_progress.append(course_dict)

        return render_template('my_courses.html', courses=courses_with_progress)
    finally:
        conn.close()

@student_bp.route('/sessions')
@login_required
@role_required('student')
def sessions():
    """Sessions page - dedicated session management"""
    conn = get_db_connection()
    try:
        # Get current session (in progress)
        current_session = conn.execute('''
            SELECT s.*, u.username as tutor_name, u.email as tutor_email, c.title as course_title
            FROM sessions s
            JOIN users u ON s.tutor_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.student_id = ? AND s.status = 'in_progress'
            ORDER BY s.scheduled_date DESC LIMIT 1
        ''', (session['user_id'],)).fetchone()
        
        # Get upcoming sessions (scheduled and rescheduled)
        current_sessions = conn.execute('''
            SELECT s.*, u.username as tutor_name, u.email as tutor_email, c.title as course_title
            FROM sessions s
            JOIN users u ON s.tutor_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.student_id = ? AND s.status IN ('scheduled', 'rescheduled')
            AND s.scheduled_date >= date('now')
            ORDER BY s.scheduled_date ASC, s.scheduled_time ASC
        ''', (session['user_id'],)).fetchall()
          # Get completed/cancelled sessions for history
        completed_sessions = conn.execute('''
            SELECT s.*, u.username as tutor_name, u.email as tutor_email, c.title as course_title,
                   r.rating, r.review_text
            FROM sessions s
            JOIN users u ON s.tutor_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN reviews r ON s.id = r.session_id AND r.student_id = ?
            WHERE s.student_id = ? AND s.status IN ('completed', 'cancelled')
            ORDER BY s.scheduled_date DESC LIMIT 20
        ''', (session['user_id'], session['user_id'])).fetchall()
        
        # Get available courses for session creation
        available_courses = conn.execute('''
            SELECT c.id, c.title, c.description FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = ? AND e.status = 'active'
            ORDER BY c.title
        ''', (session['user_id'],)).fetchall()
        
        # Get active tutors (distinct from all tutors who have courses)
        active_tutors = conn.execute('''
            SELECT DISTINCT u.id, u.username 
            FROM users u
            WHERE u.role = 'tutor'
            ORDER BY u.username
        ''').fetchall()
        
        # Calculate stats
        total_hours = conn.execute('''
            SELECT COALESCE(SUM(duration), 0) / 60.0 as hours
            FROM sessions 
            WHERE student_id = ? AND status = 'completed'
        ''', (session['user_id'],)).fetchone()['hours'] or 0
        return render_template('sessions.html', 
                             current_session=current_session,
                             current_sessions=current_sessions,
                             completed_sessions=completed_sessions,
                             available_courses=available_courses,
                             active_tutors=active_tutors,
                             total_hours=round(total_hours, 1))
    finally:
        conn.close()

@student_bp.route('/progress')
@login_required
@role_required('student')
def progress():
    """Progress page - dedicated progress tracking"""
    conn = get_db_connection()
    try:
        # Get overall stats
        total_courses = conn.execute('''
            SELECT COUNT(*) as count FROM enrollments 
            WHERE student_id = ? AND status IN ('active', 'completed', 'paused')
        ''', (session['user_id'],)).fetchone()['count']
        
        completed_courses_count = conn.execute('''
            SELECT COUNT(*) as count FROM enrollments 
            WHERE student_id = ? AND status = 'completed'
        ''', (session['user_id'],)).fetchone()['count']
        
        active_courses_count = conn.execute('''
            SELECT COUNT(*) as count FROM enrollments 
            WHERE student_id = ? AND status = 'active'
        ''', (session['user_id'],)).fetchone()['count']
        
        # Get current courses with progress
        current_courses = conn.execute('''
            SELECT c.*, e.enrolled_date,
                   COUNT(DISTINCT l.id) as total_lessons,
                   COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons,
                   MAX(p.updated_at) as last_activity
            FROM courses c 
            JOIN enrollments e ON c.id = e.course_id 
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            WHERE e.student_id = ? AND e.status = 'active'
            GROUP BY c.id
        ''', (session['user_id'], session['user_id'])).fetchall()
        
        # Calculate progress and add to current courses
        current_courses_with_progress = []
        total_progress = 0
        for course in current_courses:
            progress = 0
            if course['total_lessons'] > 0:
                progress = (course['completed_lessons'] / course['total_lessons']) * 100
            
            course_dict = dict(course)
            course_dict['progress'] = round(progress, 1)
            current_courses_with_progress.append(course_dict)
            total_progress += progress
        
        average_progress = round(total_progress / len(current_courses_with_progress)) if current_courses_with_progress else 0
        
        # Get completed courses
        completed_courses = conn.execute('''
            SELECT c.*, e.enrolled_date, e.completion_date,
                   COUNT(DISTINCT l.id) as total_lessons
            FROM courses c 
            JOIN enrollments e ON c.id = e.course_id 
            LEFT JOIN lessons l ON c.id = l.course_id
            WHERE e.student_id = ? AND e.status = 'completed'
            GROUP BY c.id
            ORDER BY e.completion_date DESC
        ''', (session['user_id'],)).fetchall()
        
        # Mock data for demo purposes
        learning_streak = 7  # Days
        weekly_lessons = 12
        weekly_hours = 8
        daily_activity = [3, 2, 4, 1, 3, 0, 2]  # Activity level for each day
        
        # Mock achievements
        achievements = [
            {'title': 'First Steps', 'description': 'Complete your first lesson', 'icon': 'baby', 'earned': True, 'date_earned': '2 weeks ago'},
            {'title': 'Consistent Learner', 'description': '7-day learning streak', 'icon': 'fire', 'earned': True, 'date_earned': '1 week ago'},
            {'title': 'Course Champion', 'description': 'Complete your first course', 'icon': 'trophy', 'earned': False, 'date_earned': None},
            {'title': 'Session Master', 'description': 'Attend 10 tutor sessions', 'icon': 'chalkboard-teacher', 'earned': False, 'date_earned': None}
        ]

        return render_template('progress.html',
                             total_courses=total_courses,
                             completed_courses=completed_courses_count,
                             active_courses=active_courses_count,
                             average_progress=average_progress,
                             current_courses=current_courses_with_progress,
                             completed_courses_list=completed_courses,
                             learning_streak=learning_streak,
                             weekly_lessons=weekly_lessons,
                             weekly_hours=weekly_hours,
                             daily_activity=daily_activity,
                             achievements=achievements)
    finally:
        conn.close()

# ========== JOIN SESSION ROUTES ==========

@student_bp.route('/session/<int:session_id>/join')
@login_required
@role_required('student')
def join_session(session_id):
    """Display join session page for students"""
    conn = get_db_connection()
    try:
        session_data = conn.execute('''
            SELECT s.*, u.username as tutor_name, c.title as course_title
            FROM sessions s
            JOIN users u ON s.tutor_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.id = ? AND s.student_id = ?
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_data:
            flash('Session not found or access denied.', 'error')
            return redirect(url_for('student.dashboard'))
            
        return render_template('join_session.html', session_data=session_data)
    finally:
        conn.close()


@student_bp.route('/api/join_session/<int:session_id>', methods=['POST'])
@login_required
@role_required('student')
def api_join_session(session_id):
    """API endpoint to join a session"""
    conn = get_db_connection()
    try:
        # Update session status to 'in_progress'
        conn.execute('''
            UPDATE sessions 
            SET status = 'in_progress'
            WHERE id = ? AND student_id = ?
        ''', (session_id, session['user_id']))
        
        conn.commit()
        flash('Successfully joined the session! Session is now in progress.', 'success')
        return redirect(url_for('student.dashboard'))
    finally:
        conn.close()

@student_bp.route('/api/end_session/<int:session_id>', methods=['POST'])
@login_required
@role_required('student')
def api_end_session(session_id):
    """API endpoint to end a session and mark it as completed"""
    conn = get_db_connection()
    try:
        # Verify the session belongs to this student and is in progress
        session_data = conn.execute('''
            SELECT id, status FROM sessions 
            WHERE id = ? AND student_id = ? AND status = 'in_progress'
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_data:
            return jsonify({'error': 'Session not found or not in progress'}), 404
        
        # Update session status to 'completed' and set end time
        conn.execute('''
            UPDATE sessions 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND student_id = ?
        ''', (session_id, session['user_id']))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Session ended successfully'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred'}), 500
    finally:
        conn.close()

# ========== API ENDPOINTS ==========

@student_bp.route('/api/courses/available', methods=['GET'])
@login_required
@role_required('student')
def get_available_courses():
    """Get courses available for discovery (not enrolled by current student)"""
    conn = get_db_connection()
    try:
        difficulty = request.args.get('difficulty', '')
        search = request.args.get('search', '')
        
        query = '''
            SELECT c.id, c.title, c.description, c.difficulty_level, c.estimated_duration,
                   u.username as instructor_name,
                   COUNT(DISTINCT l.id) as lesson_count,
                   COUNT(DISTINCT e.id) as enrolled_count
            FROM courses c
            LEFT JOIN users u ON c.created_by = u.id
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN enrollments e ON c.id = e.course_id AND e.status = 'active'
            WHERE c.id NOT IN (
                SELECT course_id FROM enrollments 
                WHERE student_id = ? AND status = 'active'
            )
        '''
        params = [session['user_id']]
        
        if difficulty:
            query += ' AND c.difficulty_level = ?'
            params.append(difficulty)
        if search:
            query += ' AND (c.title LIKE ? OR c.description LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += '''
            GROUP BY c.id, c.title, c.description, c.difficulty_level, c.estimated_duration, u.username
            ORDER BY c.title
        '''
        
        courses = conn.execute(query, params).fetchall()
        courses_list = [dict(course) for course in courses]
        
        return jsonify({'courses': courses_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/courses/<int:course_id>/enroll', methods=['POST'])
@login_required
@role_required('student')
def enroll_in_course(course_id):
    """Enroll current student in a course"""
    conn = get_db_connection()
    try:
        # Check if course exists
        course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if already enrolled
        existing_enrollment = conn.execute('''
            SELECT id FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id)).fetchone()
        
        if existing_enrollment:
            return jsonify({'error': 'Already enrolled in this course'}), 400
        
        # Create enrollment
        conn.execute('''
            INSERT INTO enrollments (student_id, course_id, enrolled_date, status)
            VALUES (?, ?, CURRENT_TIMESTAMP, 'active')
        ''', (session['user_id'], course_id))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully enrolled in course'
        }), 201
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/sessions/<int:session_id>/cancel', methods=['POST'])
@login_required
@role_required('student')
def cancel_session(session_id):
    """Cancel a scheduled session"""
    conn = get_db_connection()
    try:
        # Check if session belongs to student
        session_data = conn.execute('''
            SELECT id FROM sessions 
            WHERE id = ? AND student_id = ? AND status = 'scheduled'
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_data:
            return jsonify({'error': 'Session not found or cannot be cancelled'}), 404
        
        # Update session status
        conn.execute('''
            UPDATE sessions 
            SET status = 'cancelled'
            WHERE id = ? AND student_id = ?
        ''', (session_id, session['user_id']))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Session cancelled successfully'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

# ========== SESSION SCHEDULING API ENDPOINTS ==========

@student_bp.route('/api/sessions', methods=['POST'])
@login_required
@role_required('student')
def create_session():
    """Create a new tutoring session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['tutor_id', 'scheduled_date', 'scheduled_time', 'duration']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        try:
            # Check if tutor exists and is available
            tutor = conn.execute('SELECT id FROM users WHERE id = ? AND role = "tutor"', 
                               (data['tutor_id'],)).fetchone()
            if not tutor:
                return jsonify({'error': 'Invalid tutor selected'}), 400
            
            # Check tutor availability for the requested day and time
            from datetime import datetime
            scheduled_datetime = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
            day_of_week = scheduled_datetime.weekday() + 1  # Convert to 1-7 where Monday=1
            if day_of_week == 7:  # Sunday should be 0
                day_of_week = 0
                
            availability = conn.execute('''
                SELECT id FROM tutor_availability 
                WHERE tutor_id = ? AND day_of_week = ? 
                AND start_time <= ? AND end_time > ? AND is_available = 1
            ''', (data['tutor_id'], day_of_week, data['scheduled_time'], data['scheduled_time'])).fetchone()
            
            if not availability:
                return jsonify({'error': 'Tutor is not available at the requested time'}), 400
            
            # Check for scheduling conflicts
            existing_session = conn.execute('''
                SELECT id FROM sessions 
                WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
                AND status IN ('scheduled', 'rescheduled', 'in_progress')
            ''', (data['tutor_id'], data['scheduled_date'], data['scheduled_time'])).fetchone()
            
            if existing_session:
                return jsonify({'error': 'This time slot is already booked'}), 400
            
            # Create the session
            session_id = conn.execute('''
                INSERT INTO sessions (student_id, tutor_id, course_id, scheduled_date, 
                                    scheduled_time, duration, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', CURRENT_TIMESTAMP)
            ''', (session['user_id'], data['tutor_id'], data.get('course_id'),
                  data['scheduled_date'], data['scheduled_time'], data['duration'])).lastrowid
            
            conn.commit()
            
            # Create notification for tutor if notifications table exists
            try:
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, 'info')
                ''', (data['tutor_id'], 'New Session Scheduled', 
                      f'A new tutoring session has been scheduled for {data["scheduled_date"]} at {data["scheduled_time"]}'))
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

@student_bp.route('/api/tutors/available', methods=['GET'])
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

@student_bp.route('/api/tutors/<int:tutor_id>/availability', methods=['GET'])
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
                WHERE tutor_id = ? AND scheduled_date = ? AND status IN ('scheduled', 'rescheduled', 'in_progress')
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

# ========== MISSING API ENDPOINTS FOR SESSIONS ==========

@student_bp.route('/api/tutors-for-course/<int:course_id>', methods=['GET'])
@login_required
@role_required('student')
def get_tutors_for_course(course_id):
    """Get tutors who can teach a specific course"""
    conn = get_db_connection()    
    try:
        # First, get the course title for context
        course = conn.execute('SELECT title FROM courses WHERE id = ?', (course_id,)).fetchone()
        course_title = course['title'] if course else f"Course ID {course_id}"
          # Get tutors who have taught this course or are qualified for it
        tutors = conn.execute('''
            SELECT DISTINCT u.id, u.username, u.email,
                   COUNT(DISTINCT s.id) as sessions_count,
                   AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating END) as avg_rating,
                   COALESCE(GROUP_CONCAT(DISTINCT c.title), course_specific.title) as subjects
            FROM users u
            LEFT JOIN sessions s ON u.id = s.tutor_id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN reviews r ON s.id = r.session_id
            LEFT JOIN courses course_specific ON course_specific.id = ?
            WHERE u.role = 'tutor'
            GROUP BY u.id, u.username, u.email
            HAVING (
                COUNT(DISTINCT CASE WHEN s.course_id = ? THEN s.id END) > 0
                OR u.id IN (SELECT DISTINCT tutor_id FROM tutor_availability WHERE is_available = 1)
            )
            ORDER BY 
                COUNT(DISTINCT CASE WHEN s.course_id = ? THEN s.id END) DESC,
                avg_rating DESC, 
                sessions_count DESC, 
                u.username
        ''', (course_id, course_id, course_id)).fetchall()
        tutors_list = []
        for tutor in tutors:
            tutor_dict = dict(tutor)
            tutor_dict['avg_rating'] = round(tutor_dict['avg_rating'], 1) if tutor_dict['avg_rating'] else None
            tutors_list.append(tutor_dict)
        
        return jsonify({
            'status': 'success',
            'tutors': tutors_list
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/tutor-availability', methods=['GET'])
@login_required
@role_required('student')
def get_tutor_availability_slots():
    """Get available time slots for a tutor on a specific date"""
    tutor_id = request.args.get('tutor_id')
    date = request.args.get('date')  # YYYY-MM-DD format
    
    if not tutor_id or not date:
        return jsonify({'error': 'tutor_id and date are required'}), 400
    
    conn = get_db_connection()
    try:
        # Parse date to get day of week
        from datetime import datetime
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_of_week = date_obj.weekday() + 1  # Convert to 1-7 where Monday=1
        if day_of_week == 7:  # Sunday should be 0
            day_of_week = 0
        
        # Get tutor availability for the day
        availability_slots = conn.execute('''
            SELECT start_time, end_time
            FROM tutor_availability
            WHERE tutor_id = ? AND day_of_week = ? AND is_available = 1
            ORDER BY start_time
        ''', (tutor_id, day_of_week)).fetchall()
        
        # Get existing sessions for the date
        existing_sessions = conn.execute('''
            SELECT scheduled_time, duration
            FROM sessions
            WHERE tutor_id = ? AND scheduled_date = ? AND status IN ('scheduled', 'rescheduled', 'in_progress')
        ''', (tutor_id, date)).fetchall()
        
        # Generate available time slots (every 30 minutes)
        available_slots = []
        for slot in availability_slots:
            start_time = datetime.strptime(slot['start_time'], '%H:%M')
            end_time = datetime.strptime(slot['end_time'], '%H:%M')
            
            current_time = start_time
            while current_time < end_time:
                slot_time_str = current_time.strftime('%H:%M')
                
                # Check if this slot conflicts with existing sessions
                is_available = True
                for session in existing_sessions:
                    session_start = datetime.strptime(session['scheduled_time'], '%H:%M')
                    session_end = session_start.replace(minute=session_start.minute + session['duration'])
                    
                    if session_start <= current_time < session_end:
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot_time_str)
                
                # Move to next 30-minute slot
                if current_time.minute == 0:
                    current_time = current_time.replace(minute=30)
                else:
                    current_time = current_time.replace(hour=current_time.hour + 1, minute=0)
        
        return jsonify({'slots': available_slots})
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/schedule-session', methods=['POST'])
@login_required
@role_required('student')
def schedule_session():
    """Schedule a new tutoring session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['courseId', 'tutorId', 'date', 'time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        try:            # Check if tutor exists and is available
            tutor = conn.execute('SELECT id FROM users WHERE id = ? AND role = "tutor"', 
                               (data['tutorId'],)).fetchone()
            if not tutor:
                return jsonify({'error': 'Invalid tutor selected'}), 400
            
            # Check course enrollment - now required for all sessions
            enrollment = conn.execute('''
                SELECT id FROM enrollments 
                WHERE student_id = ? AND course_id = ? AND status = 'active'
            ''', (session['user_id'], data['courseId'])).fetchone()
            
            if not enrollment:
                return jsonify({'error': 'You are not enrolled in this course'}), 400
            
            # Check for scheduling conflicts
            existing_session = conn.execute('''
                SELECT id FROM sessions 
                WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
                AND status IN ('scheduled', 'rescheduled', 'in_progress')
            ''', (data['tutorId'], data['date'], data['time'])).fetchone()
            
            if existing_session:
                return jsonify({'error': 'This time slot is already booked'}), 400            # Create the session
            session_id = conn.execute('''
                INSERT INTO sessions (student_id, tutor_id, course_id, scheduled_date, 
                                    scheduled_time, duration, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', CURRENT_TIMESTAMP)
            ''', (session['user_id'], data['tutorId'], data['courseId'],
                  data['date'], data['time'], data.get('duration', 60))).lastrowid
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Session scheduled successfully',
                'session_id': session_id
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to schedule session: ' + str(e)}), 500

@student_bp.route('/api/session-details/<int:session_id>', methods=['GET'])
@login_required
@role_required('student')
def get_session_details(session_id):
    """Get detailed information about a session"""
    conn = get_db_connection()
    try:
        session_details = conn.execute('''
            SELECT s.*, u.username as tutor_name, u.email as tutor_email, 
                   c.title as course_title, c.description as course_description
            FROM sessions s
            JOIN users u ON s.tutor_id = u.id
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.id = ? AND s.student_id = ?
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_details:
            return jsonify({'error': 'Session not found'}), 404
        
        session_dict = dict(session_details)
        # For now, set notes as empty array since session_notes table doesn't exist
        session_dict['notes'] = []
        
        return jsonify({'session': session_dict})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/rate-session/<int:session_id>', methods=['POST'])
@login_required
@role_required('student')
def rate_session(session_id):
    """Submit a rating and review for a completed session"""
    try:
        data = request.get_json()
        rating = data.get('rating')
        review = data.get('review', '')
        
        if not rating or not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        conn = get_db_connection()
        try:
            # Check if session belongs to student and is completed
            session_data = conn.execute('''
                SELECT id FROM sessions 
                WHERE id = ? AND student_id = ? AND status = 'completed'
            ''', (session_id, session['user_id'])).fetchone()
            
            if not session_data:
                return jsonify({'error': 'Session not found or not completed'}), 404
            
            # Check if already rated
            existing_review = conn.execute('''
                SELECT id FROM reviews WHERE session_id = ? AND student_id = ?
            ''', (session_id, session['user_id'])).fetchone()
            
            if existing_review:
                # Update existing review
                conn.execute('''
                    UPDATE reviews 
                    SET rating = ?, review_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND student_id = ?
                ''', (rating, review, session_id, session['user_id']))
            else:
                # Create new review
                conn.execute('''
                    INSERT INTO reviews (session_id, student_id, rating, review_text, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (session_id, session['user_id'], rating, review))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Rating submitted successfully'
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Failed to submit rating: ' + str(e)}), 500

@student_bp.route('/api/cancel-session/<int:session_id>', methods=['POST'])
@login_required
@role_required('student')
def api_cancel_session(session_id):
    """Enhanced API endpoint to cancel a session with better response format"""
    conn = get_db_connection()
    try:
        # Check if session belongs to student and can be cancelled
        session_data = conn.execute('''
            SELECT id, status FROM sessions 
            WHERE id = ? AND student_id = ?
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_data:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Check if session can be cancelled
        if session_data['status'] in ('completed', 'cancelled'):
            return jsonify({'error': 'Session cannot be cancelled as it is already ' + session_data['status']}), 400
          # Update session status
        conn.execute('''
            UPDATE sessions 
            SET status = 'cancelled'
            WHERE id = ? AND student_id = ?
        ''', (session_id, session['user_id']))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Session cancelled successfully'
        })
        
    except sqlite3.Error as e:
        print(f"Database error in cancel_session: {e}")  # Debug log
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Unexpected error in cancel_session: {e}")  # Debug log
        return jsonify({'error': 'An unexpected error occurred'}), 500
    finally:
        conn.close()

@student_bp.route('/api/reschedule-session/<int:session_id>', methods=['POST'])
@login_required
@role_required('student')
def reschedule_session(session_id):
    """Reschedule a session (student version)"""
    try:
        data = request.get_json()
        new_date = data.get('date')
        new_time = data.get('time')
        reason = data.get('reason', 'Rescheduled by student')
        
        if not new_date or not new_time:
            return jsonify({'error': 'Date and time are required'}), 400
        
        conn = get_db_connection()
        try:
            # Check if session exists and belongs to student
            session_data = conn.execute('''
                SELECT s.*, u.username as tutor_name
                FROM sessions s
                JOIN users u ON s.tutor_id = u.id
                WHERE s.id = ? AND s.student_id = ?
            ''', (session_id, session['user_id'])).fetchone()
            
            if not session_data:
                return jsonify({'error': 'Session not found'}), 404
            
            # Check if session can be rescheduled (must be scheduled or already rescheduled)
            if session_data['status'] not in ['scheduled', 'rescheduled']:
                return jsonify({'error': 'Can only reschedule scheduled sessions'}), 400
            
            # Check if new time slot is available
            existing_session = conn.execute('''
                SELECT id FROM sessions 
                WHERE tutor_id = ? AND scheduled_date = ? AND scheduled_time = ?
                AND status IN ('scheduled', 'rescheduled', 'in_progress') AND id != ?
            ''', (session_data['tutor_id'], new_date, new_time, session_id)).fetchone()
            
            if existing_session:
                return jsonify({'error': 'The requested time slot is already booked'}), 400
            
            # Update the session
            conn.execute('''
                UPDATE sessions 
                SET scheduled_date = ?, scheduled_time = ?, status = 'rescheduled', 
                    reschedule_reason = ?, rescheduled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_date, new_time, reason, session_id))
            
            # Add notification for tutor (optional, if notifications table exists)
            try:
                conn.execute('''
                    INSERT INTO notifications (user_id, type, message, created_at)
                    VALUES (?, 'session_rescheduled', ?, CURRENT_TIMESTAMP)
                ''', (session_data['tutor_id'], 
                      f'Your session has been rescheduled by student to {new_date} at {new_time}'))
            except:
                pass  # Notifications table might not exist
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Session rescheduled successfully'
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({'error': 'Database error occurred'}), 500
            
    except Exception as e:
        return jsonify({'error': 'Failed to reschedule session: ' + str(e)}), 500
    finally:
        conn.close()

# ========== COURSE PROGRESS API ENDPOINTS ==========

@student_bp.route('/api/progress/update', methods=['POST'])
@login_required
@role_required('student')
def update_lesson_progress():
    """Update lesson progress - mark lesson as complete"""
    try:
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        completed = data.get('completed', 1)
        
        if not lesson_id:
            return jsonify({'status': 'error', 'error': 'Lesson ID is required'}), 400
        
        conn = get_db_connection()
        try:
            # First, get the course_id for this lesson
            lesson = conn.execute('''
                SELECT course_id FROM lessons WHERE id = ?
            ''', (lesson_id,)).fetchone()
            
            if not lesson:
                return jsonify({'status': 'error', 'error': 'Lesson not found'}), 404
            
            course_id = lesson['course_id']
            
            # Check if student is enrolled in this course
            enrollment = conn.execute('''
                SELECT id FROM enrollments 
                WHERE student_id = ? AND course_id = ? AND status = 'active'
            ''', (session['user_id'], course_id)).fetchone()
            
            if not enrollment:
                return jsonify({'status': 'error', 'error': 'Not enrolled in this course'}), 403
            
            # Update or insert progress record
            conn.execute('''
                INSERT OR REPLACE INTO progress 
                (user_id, course_id, lesson_id, completed, progress, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session['user_id'], course_id, lesson_id, completed, 100 if completed else 0))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Progress updated successfully'
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Database error in update_lesson_progress: {e}")
            return jsonify({'status': 'error', 'error': 'Database error occurred'}), 500
            
    except Exception as e:
        print(f"Error in update_lesson_progress: {e}")
        return jsonify({'status': 'error', 'error': 'Failed to update progress'}), 500
    finally:
        conn.close()

@student_bp.route('/api/courses/<int:course_id>/progress', methods=['GET'])
@login_required
@role_required('student')
def get_course_progress(course_id):
    """Get current progress for a specific course"""
    try:
        conn = get_db_connection()
        try:
            # Check if student is enrolled
            enrollment = conn.execute('''
                SELECT id FROM enrollments 
                WHERE student_id = ? AND course_id = ? AND status = 'active'
            ''', (session['user_id'], course_id)).fetchone()
            
            if not enrollment:
                return jsonify({'status': 'error', 'error': 'Not enrolled in this course'}), 403
            
            # Calculate progress
            progress_data = conn.execute('''
                SELECT 
                    COUNT(DISTINCT l.id) as total_lessons,
                    COUNT(DISTINCT CASE WHEN p.completed = 1 THEN p.lesson_id END) as completed_lessons
                FROM lessons l
                LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
                WHERE l.course_id = ?
            ''', (session['user_id'], course_id)).fetchone()
            
            total_lessons = progress_data['total_lessons'] or 0
            completed_lessons = progress_data['completed_lessons'] or 0
            progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons > 0 else 0
            
            return jsonify({
                'status': 'success',
                'progress': progress_percent,
                'completed_lessons': completed_lessons,
                'total_lessons': total_lessons
            })
            
        except sqlite3.Error as e:
            print(f"Database error in get_course_progress: {e}")
            return jsonify({'status': 'error', 'error': 'Database error occurred'}), 500
            
    except Exception as e:
        print(f"Error in get_course_progress: {e}")
        return jsonify({'status': 'error', 'error': 'Failed to get progress'}), 500
    finally:
        conn.close()

@student_bp.route('/api/courses/<int:course_id>/complete', methods=['POST'])
@login_required
@role_required('student')
def complete_course(course_id):
    """Mark entire course as complete"""
    try:
        conn = get_db_connection()
        try:
            # Check if student is enrolled
            enrollment = conn.execute('''
                SELECT id FROM enrollments 
                WHERE student_id = ? AND course_id = ? AND status = 'active'
            ''', (session['user_id'], course_id)).fetchone()
            
            if not enrollment:
                return jsonify({'status': 'error', 'error': 'Not enrolled in this course'}), 403
            
            # Get all lessons for this course
            lessons = conn.execute('''
                SELECT id FROM lessons WHERE course_id = ?
            ''', (course_id,)).fetchall()
            
            if not lessons:
                return jsonify({'status': 'error', 'error': 'No lessons found for this course'}), 404
            
            # Mark all lessons as complete
            for lesson in lessons:
                conn.execute('''
                    INSERT OR REPLACE INTO progress 
                    (user_id, course_id, lesson_id, completed, progress, updated_at)
                    VALUES (?, ?, ?, 1, 100, CURRENT_TIMESTAMP)
                ''', (session['user_id'], course_id, lesson['id']))
            
            # Update enrollment status
            conn.execute('''
                UPDATE enrollments 
                SET status = 'completed', completion_date = CURRENT_TIMESTAMP
                WHERE student_id = ? AND course_id = ?
            ''', (session['user_id'], course_id))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Course marked as complete! Congratulations!'
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Database error in complete_course: {e}")
            return jsonify({'status': 'error', 'error': 'Database error occurred'}), 500
            
    except Exception as e:
        print(f"Error in complete_course: {e}")
        return jsonify({'status': 'error', 'error': 'Failed to complete course'}), 500
    finally:
        conn.close()
