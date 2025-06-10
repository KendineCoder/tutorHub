from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'


# Database helper function
def get_db_connection():
    conn = sqlite3.connect('learning_hub.db')
    conn.row_factory = sqlite3.Row
    return conn


# Initialize database
def init_db():
    with app.app_context():
        db = get_db_connection()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()


# Authentication decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(role):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        role = session['user_role']
        if role == 'student':
            return redirect(url_for('student_dashboard'))
        elif role == 'tutor':
            return redirect(url_for('tutor_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'parent':
            return redirect(url_for('parent_dashboard'))
        elif role == 'content_manager':
            return redirect(url_for('content_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        try:
            conn.execute('''INSERT INTO users (username, email, password, role) 
                           VALUES (?, ?, ?, ?)''',
                         (username, email, password, role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# Student Dashboard
@app.route('/student')
@login_required
@role_required('student')
def student_dashboard():
    conn = get_db_connection()

    # Get enrolled courses
    courses = conn.execute('''
        SELECT c.*, p.progress 
        FROM courses c 
        JOIN progress p ON c.id = p.course_id 
        WHERE p.user_id = ?
    ''', (session['user_id'],)).fetchall()

    # Get recent sessions
    sessions = conn.execute('''
        SELECT s.*, u.username as tutor_name 
        FROM sessions s 
        JOIN users u ON s.tutor_id = u.id 
        WHERE s.student_id = ? 
        ORDER BY s.scheduled_date DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('student_dashboard.html', courses=courses, sessions=sessions)


# Tutor Dashboard
@app.route('/tutor')
@login_required
@role_required('tutor')
def tutor_dashboard():
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


# Admin Dashboard
@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    conn = get_db_connection()

    # Get statistics
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    total_courses = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()['count']
    total_sessions = conn.execute('SELECT COUNT(*) as count FROM sessions').fetchone()['count']

    # Get recent registrations
    recent_users = conn.execute('''
        SELECT username, email, role, created_at 
        FROM users 
        ORDER BY created_at DESC LIMIT 10
    ''').fetchall()

    conn.close()
    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_courses=total_courses,
                           total_sessions=total_sessions,
                           recent_users=recent_users)


# Parent Dashboard
@app.route('/parent')
@login_required
@role_required('parent')
def parent_dashboard():
    conn = get_db_connection()

    # Get children's progress (simplified - assumes parent_id field exists)
    children_progress = conn.execute('''
        SELECT u.username, c.title, p.progress 
        FROM users u 
        JOIN progress p ON u.id = p.user_id 
        JOIN courses c ON p.course_id = c.id 
        WHERE u.parent_id = ?
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('parent_dashboard.html', children_progress=children_progress)


# Content Manager Dashboard
@app.route('/content')
@login_required
@role_required('content_manager')
def content_dashboard():
    conn = get_db_connection()

    courses = conn.execute('SELECT * FROM courses ORDER BY created_at DESC').fetchall()

    conn.close()
    return render_template('content_dashboard.html', courses=courses)


# Course Management
@app.route('/course/<int:course_id>')
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


@app.route('/course/create')
@login_required
@role_required('content_manager')
def course_create():
    return render_template('course_create.html')


# API endpoints for AJAX
@app.route('/api/update_progress', methods=['POST'])
@login_required
def update_progress():
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


# ========== COURSE MANAGEMENT API ENDPOINTS ==========

@app.route('/api/courses', methods=['POST'])
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


@app.route('/api/courses/<int:course_id>', methods=['GET'])
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


@app.route('/api/courses/<int:course_id>', methods=['PUT'])
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


@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
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

@app.route('/api/lessons', methods=['POST'])
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


@app.route('/api/lessons/<int:lesson_id>', methods=['GET'])
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


@app.route('/api/courses/<int:course_id>/lessons', methods=['GET'])
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


@app.route('/api/lessons/<int:lesson_id>', methods=['PUT'])
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


@app.route('/api/lessons/<int:lesson_id>', methods=['DELETE'])
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


# ========== LESSON CREATION ROUTE ==========

@app.route('/lesson/create/<int:course_id>')
@login_required
@role_required('content_manager')
def lesson_create(course_id):
    # Verify user has permission to add lessons to this course
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('content_dashboard'))
    
    if course['created_by'] != session['user_id'] and session['user_role'] != 'admin':
        flash('Permission denied', 'error')
        return redirect(url_for('content_dashboard'))
    
    # Get existing lessons to determine next lesson order
    lessons = conn.execute(
        'SELECT lesson_order FROM lessons WHERE course_id = ? ORDER BY lesson_order DESC LIMIT 1',
        (course_id,)
    ).fetchone()
    
    next_order = (lessons['lesson_order'] + 1) if lessons else 1
    
    conn.close()
    return render_template('lesson_create.html', course=course, next_order=next_order)


# ========== SESSION SCHEDULING API ENDPOINTS ==========

@app.route('/api/tutors/available', methods=['GET'])
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


@app.route('/api/tutors/<int:tutor_id>/availability', methods=['GET'])
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


@app.route('/api/sessions', methods=['POST'])
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


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
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


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
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


@app.route('/api/users/<int:user_id>/sessions', methods=['GET'])
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


@app.route('/api/courses/enrolled', methods=['GET'])
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


# ========== USER MANAGEMENT API ENDPOINTS (ADMIN) ==========

@app.route('/admin/users')
@login_required
@role_required('admin')
def user_management():
    """User management page for admins"""
    conn = get_db_connection()
    try:
        # Get all users with additional details
        users = conn.execute('''
            SELECT id, username, email, role, created_at, is_active
            FROM users 
            ORDER BY created_at DESC
        ''').fetchall()
          # Get statistics
        stats = {
            'total_users': len(users),
            'active_users': len([u for u in users if u['is_active']]),
            'students': len([u for u in users if u['role'] == 'student']),
            'tutors': len([u for u in users if u['role'] == 'tutor']),
            'content_managers': len([u for u in users if u['role'] == 'content_manager']),
            'parents': len([u for u in users if u['role'] == 'parent']),
            'admins': len([u for u in users if u['role'] == 'admin'])
        }
        
        return render_template('user_management.html', users=users, stats=stats)
        
    except sqlite3.Error as e:
        flash('Error loading user data', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/api/users', methods=['GET'])
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

@app.route('/api/users/<int:user_id>', methods=['GET'])
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

@app.route('/api/users/<int:user_id>', methods=['PUT'])
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

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
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

@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
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

@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
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

# ========== END USER MANAGEMENT API ENDPOINTS ==========


if __name__ == '__main__':
    if not os.path.exists('learning_hub.db'):
        init_db()
    app.run(debug=True)