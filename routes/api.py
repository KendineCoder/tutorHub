"""
API routes for courses, lessons, and sessions
"""
from flask import Blueprint, jsonify, request, session
from utils.auth import login_required, role_required
from utils.database import get_db_connection
from datetime import datetime
import sqlite3

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ========== COURSE MANAGEMENT API ENDPOINTS ==========

@api_bp.route('/courses', methods=['POST'])
@login_required
@role_required('content_manager')
def create_course():
    data = request.get_json()
    
    # Validation
    required_fields = ['title', 'description', 'difficulty_level', 'estimated_duration']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO courses (title, description, difficulty_level, estimated_duration, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['title'], data['description'], data['difficulty_level'], 
              data['estimated_duration'], session['user_id']))
        
        course_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'status': 'success', 
            'course_id': course_id, 
            'message': 'Course created successfully'
        }), 201
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/<int:course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    conn = get_db_connection()
    try:
        course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Convert Row object to dict
        course_dict = dict(course)
        return jsonify(course_dict)
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/<int:course_id>', methods=['PUT'])
@login_required
@role_required('content_manager')
def update_course(course_id):
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Check if course exists and user has permission
        course = conn.execute('SELECT created_by FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update course
        conn.execute('''
            UPDATE courses 
            SET title = ?, description = ?, difficulty_level = ?, estimated_duration = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['title'], data['description'], data['difficulty_level'],
              data['estimated_duration'], course_id))
        
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Course updated successfully'})
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/<int:course_id>', methods=['DELETE'])
@login_required
@role_required('content_manager')
def delete_course(course_id):
    conn = get_db_connection()
    try:
        # Check if course exists and user has permission
        course = conn.execute('SELECT created_by FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete course (lessons will be deleted due to CASCADE)
        conn.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Course deleted successfully'})
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/enrolled', methods=['GET'])
@login_required
@role_required('student')
def get_enrolled_courses():
    """Get courses the current student is enrolled in"""
    conn = get_db_connection()
    try:
        courses = conn.execute('''
            SELECT c.id, c.title, c.description, e.enrolled_date
            FROM courses c
            JOIN enrollments e ON c.id = e.course_id
            WHERE e.student_id = ? AND e.status = 'active'
            ORDER BY c.title
        ''', (session['user_id'],)).fetchall()
        
        courses_list = [dict(course) for course in courses]
        return jsonify({'courses': courses_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


# ========== LESSON MANAGEMENT API ENDPOINTS ==========

@api_bp.route('/lessons', methods=['POST'])
@login_required
@role_required('content_manager')
def create_lesson():
    data = request.get_json()
    
    # Validation
    required_fields = ['course_id', 'title', 'content', 'lesson_order']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    try:
        # Check if course exists and user has permission
        course = conn.execute('SELECT created_by FROM courses WHERE id = ?', (data['course_id'],)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        if course['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            return jsonify({'error': 'Permission denied'}), 403
        
        # Check if lesson order already exists
        existing_lesson = conn.execute(
            'SELECT id FROM lessons WHERE course_id = ? AND lesson_order = ?',
            (data['course_id'], data['lesson_order'])
        ).fetchone()
        
        if existing_lesson:
            return jsonify({'error': 'Lesson order already exists for this course'}), 400
        
        cursor = conn.execute('''
            INSERT INTO lessons (course_id, title, content, lesson_order, duration)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['course_id'], data['title'], data['content'], 
              data['lesson_order'], data.get('duration', 60)))
        
        lesson_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'status': 'success', 
            'lesson_id': lesson_id, 
            'message': 'Lesson created successfully'
        }), 201
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/lessons/<int:lesson_id>', methods=['GET'])
@login_required
def get_lesson(lesson_id):
    conn = get_db_connection()
    try:
        lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Convert Row object to dict
        lesson_dict = dict(lesson)
        return jsonify(lesson_dict)
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/<int:course_id>/lessons', methods=['GET'])
@login_required
def get_course_lessons(course_id):
    conn = get_db_connection()
    try:
        # Check if course exists
        course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        lessons = conn.execute(
            'SELECT * FROM lessons WHERE course_id = ? ORDER BY lesson_order',
            (course_id,)
        ).fetchall()
        
        # Convert Row objects to dicts
        lessons_list = [dict(lesson) for lesson in lessons]
        return jsonify({'lessons': lessons_list})
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/lessons/<int:lesson_id>', methods=['PUT'])
@login_required
@role_required('content_manager')
def update_lesson(lesson_id):
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Get lesson and check permissions
        lesson = conn.execute('''
            SELECT l.*, c.created_by 
            FROM lessons l
            JOIN courses c ON l.course_id = c.id
            WHERE l.id = ?
        ''', (lesson_id,)).fetchone()
        
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        if lesson['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            return jsonify({'error': 'Permission denied'}), 403
        
        # Check if new lesson order conflicts with existing lessons
        if 'lesson_order' in data and data['lesson_order'] != lesson['lesson_order']:
            existing_lesson = conn.execute(
                'SELECT id FROM lessons WHERE course_id = ? AND lesson_order = ? AND id != ?',
                (lesson['course_id'], data['lesson_order'], lesson_id)
            ).fetchone()
            
            if existing_lesson:
                return jsonify({'error': 'Lesson order already exists for this course'}), 400
        
        # Update lesson
        conn.execute('''
            UPDATE lessons 
            SET title = ?, content = ?, lesson_order = ?, duration = ?
            WHERE id = ?
        ''', (
            data.get('title', lesson['title']),
            data.get('content', lesson['content']),
            data.get('lesson_order', lesson['lesson_order']),
            data.get('duration', lesson['duration']),
            lesson_id
        ))
        
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Lesson updated successfully'})
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/lessons/<int:lesson_id>', methods=['DELETE'])
@login_required
@role_required('content_manager')
def delete_lesson(lesson_id):
    conn = get_db_connection()
    try:
        # Get lesson and check permissions
        lesson = conn.execute('''
            SELECT l.*, c.created_by 
            FROM lessons l
            JOIN courses c ON l.course_id = c.id
            WHERE l.id = ?
        ''', (lesson_id,)).fetchone()
        
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        if lesson['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete lesson
        conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Lesson deleted successfully'})
    
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


# ========== SESSION SCHEDULING API ENDPOINTS ==========

@api_bp.route('/tutors/available', methods=['GET'])
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


@api_bp.route('/tutors/<int:tutor_id>/availability', methods=['GET'])
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


@api_bp.route('/sessions', methods=['POST'])
@login_required
@role_required('student')
def create_session():
    """Create a new tutoring session"""
    data = request.get_json()
    
    required_fields = ['tutor_id', 'scheduled_date', 'scheduled_time', 'duration'
                       ]
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


@api_bp.route('/sessions/<int:session_id>', methods=['PUT'])
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


@api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
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


@api_bp.route('/users/<int:user_id>/sessions', methods=['GET'])
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


# ========== STUDENT DASHBOARD API ENDPOINTS ==========

@api_bp.route('/courses/available', methods=['GET'])
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


@api_bp.route('/courses/<int:course_id>/enroll', methods=['POST'])
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


@api_bp.route('/courses/<int:course_id>/unenroll', methods=['POST'])
@login_required
@role_required('student')
def unenroll_from_course(course_id):
    """Unenroll current student from a course"""
    conn = get_db_connection()
    try:
        # Check if enrolled
        enrollment = conn.execute('''
            SELECT id FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id)).fetchone()
        
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 400
        
        # Update enrollment status
        conn.execute('''
            UPDATE enrollments 
            SET status = 'dropped', completion_date = CURRENT_TIMESTAMP
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully unenrolled from course'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/progress/update', methods=['POST'])
@login_required
@role_required('student')
def update_progress():
    """Update student progress on a lesson"""
    data = request.get_json()
    
    required_fields = ['lesson_id', 'completed']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    try:
        # Check if student is enrolled in the course
        lesson = conn.execute('''
            SELECT l.*, c.id as course_id
            FROM lessons l
            JOIN courses c ON l.course_id = c.id
            JOIN enrollments e ON c.id = e.course_id
            WHERE l.id = ? AND e.student_id = ? AND e.status = 'active'
        ''', (data['lesson_id'], session['user_id'])).fetchone()
        
        if not lesson:
            return jsonify({'error': 'Lesson not found or not enrolled in course'}), 404
          # Check if progress already exists
        existing_progress = conn.execute('''
            SELECT id FROM progress 
            WHERE user_id = ? AND lesson_id = ?
        ''', (session['user_id'], data['lesson_id'])).fetchone()
        
        if existing_progress:
            # Update existing progress
            conn.execute('''
                UPDATE progress 
                SET completed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND lesson_id = ?
            ''', (data['completed'], session['user_id'], data['lesson_id']))
        else:
            # Create new progress entry
            conn.execute('''
                INSERT INTO progress (user_id, lesson_id, completed, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session['user_id'], data['lesson_id'], data['completed']))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Progress updated successfully'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/courses/<int:course_id>/complete', methods=['POST'])
@login_required
@role_required('student')
def complete_course(course_id):
    """Mark a course as completed for the current student"""
    conn = get_db_connection()
    try:
        # Check if student is enrolled
        enrollment = conn.execute('''
            SELECT id FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id)).fetchone()
        
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 400
          # Check if all lessons are completed
        incomplete_lessons = conn.execute('''
            SELECT l.id
            FROM lessons l
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            WHERE l.course_id = ? AND (p.completed IS NULL OR p.completed = 0)
        ''', (session['user_id'], course_id)).fetchall()
        
        if incomplete_lessons:
            return jsonify({
                'error': 'Cannot complete course. Some lessons are not yet completed.',
                'incomplete_lessons': len(incomplete_lessons)
            }), 400
        
        # Update enrollment status
        conn.execute('''
            UPDATE enrollments 
            SET status = 'completed', completion_date = CURRENT_TIMESTAMP
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Course completed successfully!'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/students/stats', methods=['GET'])
@login_required
@role_required('student')
def get_student_stats():
    """Get dashboard statistics for current student"""
    conn = get_db_connection()
    try:
        # Get enrolled courses count
        enrolled_courses = conn.execute('''
            SELECT COUNT(*) as count FROM enrollments 
            WHERE student_id = ? AND status = 'active'
        ''', (session['user_id'],)).fetchone()
        
        # Get completed courses count
        completed_courses = conn.execute('''
            SELECT COUNT(*) as count FROM enrollments 
            WHERE student_id = ? AND status = 'completed'
        ''', (session['user_id'],)).fetchone()
        
        # Get upcoming sessions count
        upcoming_sessions = conn.execute('''
            SELECT COUNT(*) as count FROM sessions 
            WHERE student_id = ? AND status = 'scheduled' 
            AND scheduled_date >= date('now')
        ''', (session['user_id'],)).fetchone()
          # Get completed lessons count
        completed_lessons = conn.execute('''
            SELECT COUNT(*) as count FROM progress 
            WHERE user_id = ? AND completed = 1
        ''', (session['user_id'],)).fetchone()
        
        # Get recent progress
        recent_progress = conn.execute('''
            SELECT l.title as lesson_title, c.title as course_title, p.updated_at
            FROM progress p
            JOIN lessons l ON p.lesson_id = l.id
            JOIN courses c ON l.course_id = c.id
            WHERE p.user_id = ? AND p.completed = 1
            ORDER BY p.updated_at DESC
            LIMIT 5
        ''', (session['user_id'],)).fetchall()
        
        stats = {
            'enrolled_courses': enrolled_courses['count'],
            'completed_courses': completed_courses['count'],
            'upcoming_sessions': upcoming_sessions['count'],
            'completed_lessons': completed_lessons['count'],
            'recent_progress': [dict(item) for item in recent_progress]
        }
        
        return jsonify(stats)
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/tutors/find', methods=['GET'])
@login_required
@role_required('student')
def find_tutors():
    """Find tutors with filtering options"""
    conn = get_db_connection()
    try:
        subject = request.args.get('subject', '')
        availability = request.args.get('availability', '')
        
        query = '''
            SELECT DISTINCT u.id, u.username, u.email,
                   GROUP_CONCAT(DISTINCT c.title) as subjects,
                   AVG(sr.rating) as avg_rating,
                   COUNT(DISTINCT sr.id) as rating_count
            FROM users u
            LEFT JOIN sessions s ON u.id = s.tutor_id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN session_ratings sr ON s.id = sr.session_id
            WHERE u.role = 'tutor' AND u.is_active = 1
        '''
        params = []
        
        if subject:
            query += ' AND c.title LIKE ?'
            params.append(f'%{subject}%')
        
        query += '''
            GROUP BY u.id, u.username, u.email
            ORDER BY avg_rating DESC NULLS LAST, u.username
        '''
        
        tutors = conn.execute(query, params).fetchall()
        tutors_list = [dict(tutor) for tutor in tutors]
        
        return jsonify({'tutors': tutors_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/sessions/<int:session_id>/rate', methods=['POST'])
@login_required
@role_required('student')
def rate_session(session_id):
    """Rate a completed session"""
    data = request.get_json()
    
    if 'rating' not in data or not (1 <= data['rating'] <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    conn = get_db_connection()
    try:
        # Check if session exists and belongs to student
        session_data = conn.execute('''
            SELECT * FROM sessions 
            WHERE id = ? AND student_id = ? AND status = 'completed'
        ''', (session_id, session['user_id'])).fetchone()
        
        if not session_data:
            return jsonify({'error': 'Session not found or not completed'}), 404
        
        # Check if already rated
        existing_rating = conn.execute('''
            SELECT id FROM session_ratings 
            WHERE session_id = ? AND student_id = ?
        ''', (session_id, session['user_id'])).fetchone()
        
        if existing_rating:
            # Update existing rating
            conn.execute('''
                UPDATE session_ratings 
                SET rating = ?, comment = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ? AND student_id = ?
            ''', (data['rating'], data.get('comment', ''), session_id, session['user_id']))
        else:
            # Create new rating
            conn.execute('''
                INSERT INTO session_ratings (session_id, student_id, tutor_id, rating, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, session['user_id'], session_data['tutor_id'], 
                  data['rating'], data.get('comment', '')))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Session rated successfully'
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


# ========== USER MANAGEMENT API ENDPOINTS (ADMIN) ==========

@api_bp.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def get_users():
    """Get all users with filtering options"""
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 100))
    
    conn = get_db_connection()
    try:
        query = 'SELECT id, username, email, role, created_at, is_active FROM users WHERE 1=1'
        params = []
        
        if role_filter != 'all':
            query += ' AND role = ?'
            params.append(role_filter)
        if status_filter == 'active':
            query += ' AND is_active = 1'
        elif status_filter == 'inactive':
            query += ' AND is_active = 0'
        
        if search_query:
            query += ' AND (username LIKE ? OR email LIKE ?)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        users = conn.execute(query, params).fetchall()
        users_list = [dict(user) for user in users]
        
        return jsonify({'users': users_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_user_details(user_id):
    """Get detailed user information"""
    conn = get_db_connection()
    try:
        user = conn.execute('''
            SELECT id, username, email, role, created_at, is_active
            FROM users WHERE id = ?
        ''', (user_id,)).fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
          # Get user statistics
        stats = {
            'enrolled_courses': conn.execute(
                'SELECT COUNT(*) as count FROM enrollments WHERE student_id = ?', 
                (user_id,)).fetchone()['count'],
            'completed_sessions': conn.execute(
                'SELECT COUNT(*) as count FROM sessions WHERE (student_id = ? OR tutor_id = ?) AND status = "completed"', 
                (user_id, user_id)).fetchone()['count'],
            'progress_records': conn.execute(
                'SELECT COUNT(*) as count FROM progress WHERE user_id = ?', 
                (user_id,)).fetchone()['count']
        }
        
        user_data = dict(user)
        user_data['stats'] = stats
        
        return jsonify({'user': user_data})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_user(user_id):
    """Update user information"""
    data = request.get_json()
    
    # Prevent admin from editing their own account to avoid lockout
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot edit your own account'}), 403
    
    conn = get_db_connection()
    try:
        # Check if user exists
        user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check for email uniqueness if email is being changed
        if 'email' in data:
            existing_email = conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?', 
                (data['email'], user_id)).fetchone()
            if existing_email:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Update user fields
        update_fields = []
        update_values = []
        
        if 'username' in data:
            update_fields.append('username = ?')
            update_values.append(data['username'])
        
        if 'email' in data:
            update_fields.append('email = ?')
            update_values.append(data['email'])
        
        if 'role' in data and data['role'] in ['student', 'tutor', 'content_manager', 'parent', 'admin']:
            update_fields.append('role = ?')
            update_values.append(data['role'])
        
        if 'is_active' in data:
            update_fields.append('is_active = ?')
            update_values.append(1 if data['is_active'] else 0)
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        update_values.append(user_id)
        
        conn.execute(f'''
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)
        
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'User updated successfully'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_user(user_id):
    """Delete a user account (soft delete by deactivating)"""
    # Prevent admin from deleting their own account
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 403
    
    conn = get_db_connection()
    try:
        # Check if user exists
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Soft delete by deactivating instead of hard delete to preserve data integrity
        conn.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'User {user["username"]} has been deactivated'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>/hard-delete', methods=['DELETE'])
@login_required
@role_required('admin')
def hard_delete_user(user_id):
    """Permanently delete a user account and all associated data"""
    # Prevent admin from deleting their own account
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 403
    
    conn = get_db_connection()
    try:
        # Check if user exists
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Hard delete - permanently remove user and cascade delete related data
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'User {user["username"]} has been permanently deleted'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    """Toggle user active/inactive status"""
    # Prevent admin from deactivating their own account
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot modify your own account status'}), 403
    
    conn = get_db_connection()
    try:
        # Get current status
        user = conn.execute('SELECT is_active, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Toggle status
        new_status = 0 if user['is_active'] else 1
        conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        
        status_text = 'activated' if new_status else 'deactivated'
        return jsonify({
            'status': 'success', 
            'message': f'User {user["username"]} has been {status_text}',
            'new_status': bool(new_status)
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@api_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_user_password(user_id):
    """Reset user password to a default value"""
    data = request.get_json()
    new_password = data.get('new_password', 'password123')  # Default password
    
    # Prevent admin from resetting their own password this way
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot reset your own password through this method'}), 403
    
    conn = get_db_connection()
    try:
        # Check if user exists
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password (in production, this should be hashed)
        conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
        conn.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f'Password reset for user {user["username"]}',
            'new_password': new_password
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


# ========== LEGACY API ENDPOINT ==========

@api_bp.route('/update_progress', methods=['POST'])
@login_required
def update_progress_legacy():
    """Legacy API endpoint for updating progress"""
    data = request.get_json()
    course_id = data['course_id']
    progress = data['progress']

    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO progress (user_id, course_id, progress, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], course_id, progress, datetime.now()))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})