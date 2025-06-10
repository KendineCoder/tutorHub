"""
Student dashboard and functionality
"""
from flask import Blueprint, render_template, session, request, jsonify
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
    conn = get_db_connection()

    # Get enrolled courses with progress calculation
    courses = conn.execute('''
        SELECT c.*, e.enrolled_date, e.status
        FROM courses c 
        JOIN enrollments e ON c.id = e.course_id 
        WHERE e.student_id = ? AND e.status = 'active'
    ''', (session['user_id'],)).fetchall()
    
    # Calculate progress for each course
    courses_with_progress = []
    for course in courses:
        # Get total lessons in course
        total_lessons = conn.execute('''
            SELECT COUNT(*) as count FROM lessons WHERE course_id = ?
        ''', (course['id'],)).fetchone()['count']
        
        # Get completed lessons by student
        completed_lessons = conn.execute('''
            SELECT COUNT(*) as count FROM progress 
            WHERE user_id = ? AND lesson_id IN (
                SELECT id FROM lessons WHERE course_id = ?
            ) AND completed = 1
        ''', (session['user_id'], course['id'])).fetchone()['count']
        
        # Calculate progress percentage
        progress = 0
        if total_lessons > 0:
            progress = (completed_lessons / total_lessons) * 100
        
        # Convert course to dict and add progress
        course_dict = dict(course)
        course_dict['progress'] = round(progress, 1)
        courses_with_progress.append(course_dict)

    # Get recent sessions
    sessions = conn.execute('''
        SELECT s.*, u.username as tutor_name 
        FROM sessions s 
        JOIN users u ON s.tutor_id = u.id 
        WHERE s.student_id = ? 
        ORDER BY s.scheduled_date DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('student_dashboard.html', courses=courses_with_progress, sessions=sessions)

# ========== STUDENT DASHBOARD API ENDPOINTS ==========

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


@student_bp.route('/api/courses/<int:course_id>/unenroll', methods=['POST'])
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


@student_bp.route('/api/progress/update', methods=['POST'])
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


@student_bp.route('/api/courses/<int:course_id>/complete', methods=['POST'])
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


@student_bp.route('/api/students/stats', methods=['GET'])
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


@student_bp.route('/api/tutors/find', methods=['GET'])
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


@student_bp.route('/api/sessions/<int:session_id>/rate', methods=['POST'])
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


@student_bp.route('/api/courses/enrolled', methods=['GET'])
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


# Legacy progress update endpoint for backward compatibility
@student_bp.route('/api/update_progress_legacy', methods=['POST'])
@login_required
@role_required('student')
def update_progress_legacy():
    """Legacy API endpoint for updating progress - maintained for backward compatibility"""
    data = request.get_json()
    course_id = data.get('course_id')
    lesson_id = data.get('lesson_id') 
    progress = data.get('progress', 0)

    conn = get_db_connection()
    try:
        # If lesson_id is provided, use the new progress system
        if lesson_id:
            # Check if student is enrolled in the course
            lesson = conn.execute('''
                SELECT l.*, c.id as course_id
                FROM lessons l
                JOIN courses c ON l.course_id = c.id
                JOIN enrollments e ON c.id = e.course_id
                WHERE l.id = ? AND e.student_id = ? AND e.status = 'active'
            ''', (lesson_id, session['user_id'])).fetchone()
            
            if not lesson:
                return jsonify({'error': 'Lesson not found or not enrolled in course'}), 404
            
            # Mark lesson as completed if progress >= 100
            completed = 1 if progress >= 100 else 0
            
            # Check if progress already exists
            existing_progress = conn.execute('''
                SELECT id FROM progress 
                WHERE user_id = ? AND lesson_id = ?
            ''', (session['user_id'], lesson_id)).fetchone()
            
            if existing_progress:
                # Update existing progress
                conn.execute('''
                    UPDATE progress 
                    SET completed = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND lesson_id = ?
                ''', (completed, session['user_id'], lesson_id))
            else:
                # Create new progress entry
                conn.execute('''
                    INSERT INTO progress (user_id, lesson_id, completed, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (session['user_id'], lesson_id, completed))
        else:
            # Fallback to old course-based progress system
            conn.execute('''
                INSERT OR REPLACE INTO progress (user_id, course_id, progress, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session['user_id'], course_id, progress))
        
        conn.commit()
        return jsonify({'status': 'success'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()