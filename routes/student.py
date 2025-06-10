"""
Student dashboard and functionality
"""
from flask import Blueprint, render_template, session
from utils.auth import login_required, role_required
from utils.database import get_db_connection

student_bp = Blueprint('student', __name__, url_prefix='/student')


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