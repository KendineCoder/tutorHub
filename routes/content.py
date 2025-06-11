"""
Content manager dashboard and functionality
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
from utils.auth import login_required, role_required
from utils.database import get_db_connection
from datetime import datetime
import sqlite3
import os
from werkzeug.utils import secure_filename
from flask import current_app

content_bp = Blueprint('content', __name__, url_prefix='/content')

# ========== DASHBOARD ROUTES ==========

@content_bp.route('/')
@login_required
@role_required('content_manager')
def dashboard():
    conn = get_db_connection()

    # Get statistics for overview
    stats = {}
    
    # Total courses created by this content manager
    stats['total_courses'] = conn.execute(
        'SELECT COUNT(*) as count FROM courses WHERE created_by = ?', 
        (session['user_id'],)
    ).fetchone()['count']
    
    # Total lessons across all courses
    stats['total_lessons'] = conn.execute('''
        SELECT COUNT(*) as count FROM lessons l 
        JOIN courses c ON l.course_id = c.id 
        WHERE c.created_by = ?
    ''', (session['user_id'],)).fetchone()['count']
    
    # Students enrolled in courses
    stats['students_enrolled'] = conn.execute('''
        SELECT COUNT(DISTINCT e.student_id) as count FROM enrollments e
        JOIN courses c ON e.course_id = c.id 
        WHERE c.created_by = ? AND e.status = 'active'
    ''', (session['user_id'],)).fetchone()['count']
    
    # Recent courses (last 5)
    recent_courses = conn.execute('''
        SELECT * FROM courses 
        WHERE created_by = ? 
        ORDER BY created_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    # Get course enrollments for recent courses
    course_enrollments = {}
    if recent_courses:
        course_ids = [str(course['id']) for course in recent_courses]
        enrollments = conn.execute(f'''
            SELECT course_id, COUNT(*) as count 
            FROM enrollments 
            WHERE course_id IN ({','.join('?' * len(course_ids))}) 
            AND status = 'active'
            GROUP BY course_id
        ''', course_ids).fetchall()
        
        for enrollment in enrollments:
            course_enrollments[enrollment['course_id']] = enrollment['count']

    conn.close()
    return render_template('content_dashboard.html', 
                         stats=stats, 
                         recent_courses=recent_courses,
                         course_enrollments=course_enrollments)


@content_bp.route('/courses')
@login_required
@role_required('content_manager')
def courses():
    conn = get_db_connection()

    # Get all courses with enrollment counts
    courses = conn.execute('''
        SELECT c.*, COUNT(e.id) as enrollment_count
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id AND e.status = 'active'
        WHERE c.created_by = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('content_courses.html', courses=courses)


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
    lesson_progress = []
    if session['user_role'] == 'student':
        # Check if student is enrolled
        enrollment = conn.execute('''
            SELECT * FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND status = 'active'
        ''', (session['user_id'], course_id)).fetchone()
        
        if enrollment:
            # Get lesson-specific progress
            lesson_progress = conn.execute('''
                SELECT lesson_id, completed FROM progress 
                WHERE user_id = ? AND lesson_id IN (
                    SELECT id FROM lessons WHERE course_id = ?
                )
            ''', (session['user_id'], course_id)).fetchall()
            
            # Calculate overall progress based on completed lessons
            total_lessons = len(lessons)
            if total_lessons > 0:
                completed_lessons = conn.execute('''
                    SELECT COUNT(*) as count FROM progress 
                    WHERE user_id = ? AND lesson_id IN (
                        SELECT id FROM lessons WHERE course_id = ?
                    ) AND completed = 1
                ''', (session['user_id'], course_id)).fetchone()['count']
                
                progress_percentage = (completed_lessons / total_lessons) * 100
                progress = {
                    'progress': round(progress_percentage, 1),
                    'completed_lessons': completed_lessons,
                    'total_lessons': total_lessons
                }

    conn.close()
    return render_template('course_view.html', course=course, lessons=lessons, progress=progress, lesson_progress=lesson_progress)


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


# ========== MATERIALS MANAGEMENT ROUTES ==========

@content_bp.route('/materials')
@login_required
@role_required('content_manager')
def materials():
    conn = get_db_connection()
    
    # Get all materials for courses created by this content manager
    materials = conn.execute('''
        SELECT m.*, c.title as course_title
        FROM materials m
        JOIN courses c ON m.course_id = c.id
        WHERE c.created_by = ?
        ORDER BY m.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get courses for the dropdown
    courses = conn.execute('''
        SELECT id, title FROM courses 
        WHERE created_by = ? 
        ORDER BY title
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('content_materials.html', materials=materials, courses=courses)


@content_bp.route('/materials/upload', methods=['POST'])
@login_required
@role_required('content_manager')
def upload_material():
    # Get form data
    course_id = request.form.get('course_id')
    title = request.form.get('title')
    description = request.form.get('description', '')
    
    if not course_id or not title:
        flash('Course and title are required', 'error')
        return redirect(url_for('content.materials'))
    
    # Check if file was uploaded
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('content.materials'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('content.materials'))
    
    conn = get_db_connection()
    try:
        # Verify course exists and user has permission
        course = conn.execute(
            'SELECT * FROM courses WHERE id = ? AND created_by = ?', 
            (course_id, session['user_id'])
        ).fetchone()
        
        if not course:
            flash('Course not found or permission denied', 'error')
            return redirect(url_for('content.materials'))
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'materials')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Secure the filename and save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        file_path = os.path.join(upload_dir, unique_filename)
        
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
        
        # Store relative path for database
        relative_path = f'uploads/materials/{unique_filename}'
        
        # Insert material record
        conn.execute('''
            INSERT INTO materials (course_id, title, description, file_name, file_path, 
                                 file_size, file_type, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course_id, title, description, filename, relative_path, 
              file_size, file_type, session['user_id']))
        
        conn.commit()
        flash('Material uploaded successfully', 'success')
        
    except Exception as e:
        flash(f'Error uploading material: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('content.materials'))


@content_bp.route('/materials/<int:material_id>/delete', methods=['POST'])
@login_required
@role_required('content_manager')
def delete_material(material_id):
    conn = get_db_connection()
    try:
        # Get material and verify permissions
        material = conn.execute('''
            SELECT m.*, c.created_by
            FROM materials m
            JOIN courses c ON m.course_id = c.id
            WHERE m.id = ?
        ''', (material_id,)).fetchone()
        
        if not material:
            flash('Material not found', 'error')
            return redirect(url_for('content.materials'))
        
        if material['created_by'] != session['user_id'] and session['user_role'] != 'admin':
            flash('Permission denied', 'error')
            return redirect(url_for('content.materials'))
        
        # Delete file from filesystem
        file_path = os.path.join(current_app.root_path, 'static', material['file_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        conn.execute('DELETE FROM materials WHERE id = ?', (material_id,))
        conn.commit()
        
        flash('Material deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting material: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('content.materials'))


# ========== MATERIALS API ENDPOINTS ==========

@content_bp.route('/api/materials/<int:course_id>')
@login_required
def get_course_materials(course_id):
    conn = get_db_connection()
    try:
        # Check if user has access to this course
        if session['user_role'] == 'content_manager':
            course = conn.execute(
                'SELECT * FROM courses WHERE id = ? AND created_by = ?',
                (course_id, session['user_id'])
            ).fetchone()
        elif session['user_role'] == 'student':
            # Check if student is enrolled
            course = conn.execute('''
                SELECT c.* FROM courses c
                JOIN enrollments e ON c.id = e.course_id
                WHERE c.id = ? AND e.student_id = ? AND e.status = 'active'
            ''', (course_id, session['user_id'])).fetchone()
        else:
            course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        
        if not course:
            return jsonify({'error': 'Course not found or access denied'}), 404
        
        materials = conn.execute('''
            SELECT id, title, description, file_name, file_type, file_size, created_at
            FROM materials 
            WHERE course_id = ?
            ORDER BY created_at DESC
        ''', (course_id,)).fetchall()
        
        materials_list = [dict(material) for material in materials]
        return jsonify({'materials': materials_list})
        
    except Exception as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()