"""
Content manager dashboard and functionality
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
from utils.auth import login_required, role_required
from utils.database import get_db_connection
from datetime import datetime
import sqlite3

content_bp = Blueprint('content', __name__, url_prefix='/content')

# ========== DASHBOARD ROUTES ==========

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

# ========== COURSE MANAGEMENT API ENDPOINTS ==========

@content_bp.route('/api/courses', methods=['POST'])
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


@content_bp.route('/api/courses/<int:course_id>', methods=['GET'])
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


@content_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
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


@content_bp.route('/api/courses/<int:course_id>', methods=['DELETE'])
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


# ========== LESSON MANAGEMENT API ENDPOINTS ==========

@content_bp.route('/api/lessons', methods=['POST'])
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


@content_bp.route('/api/lessons/<int:lesson_id>', methods=['GET'])
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


@content_bp.route('/api/courses/<int:course_id>/lessons', methods=['GET'])
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


@content_bp.route('/api/lessons/<int:lesson_id>', methods=['PUT'])
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


@content_bp.route('/api/lessons/<int:lesson_id>', methods=['DELETE'])
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