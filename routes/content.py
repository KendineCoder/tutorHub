"""
Content manager dashboard and functionality
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for
from utils.auth import login_required, role_required
from utils.database import get_db_connection

content_bp = Blueprint('content', __name__, url_prefix='/content')


@content_bp.route('/')
@login_required
@role_required('content_manager')
def dashboard():
    conn = get_db_connection()

    courses = conn.execute('SELECT * FROM courses ORDER BY created_at DESC').fetchall()

    conn.close()
    return render_template('content_dashboard.html', courses=courses)


@content_bp.route('/course/create')
@login_required
@role_required('content_manager')
def course_create():
    return render_template('course_create.html')


@content_bp.route('/course/<int:course_id>')
@login_required
def course_view(course_id):
    conn = get_db_connection()

    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    lessons = conn.execute('SELECT * FROM lessons WHERE course_id = ? ORDER BY lesson_order',
                           (course_id,)).fetchall()

    # Get user progress if student
    progress = None
    if session['user_role'] == 'student':
        progress = conn.execute('SELECT * FROM progress WHERE user_id = ? AND course_id = ?',
                                (session['user_id'], course_id)).fetchone()

    conn.close()
    return render_template('course_view.html', course=course, lessons=lessons, progress=progress)


@content_bp.route('/lesson/create/<int:course_id>')
@login_required
@role_required('content_manager')
def lesson_create(course_id):
    # Verify user has permission to add lessons to this course
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('content.dashboard'))
    
    if course['created_by'] != session['user_id'] and session['user_role'] != 'admin':
        flash('Permission denied', 'error')
        return redirect(url_for('content.dashboard'))
    
    # Get existing lessons to determine next lesson order
    lessons = conn.execute(
        'SELECT lesson_order FROM lessons WHERE course_id = ? ORDER BY lesson_order DESC LIMIT 1',
        (course_id,)
    ).fetchone()
    
    next_order = (lessons['lesson_order'] + 1) if lessons else 1
    
    conn.close()
    return render_template('lesson_create.html', course=course, next_order=next_order)