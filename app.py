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

    # Get enrolled courses with progress
    courses = conn.execute('''
        SELECT c.*, p.progress 
        FROM courses c 
        JOIN progress p ON c.id = p.course_id 
        WHERE p.user_id = ?
    ''', (session['user_id'],)).fetchall()

    # Get recent sessions with tutor names and course titles
    sessions = conn.execute('''
        SELECT s.*, u.username as tutor_name, c.title as course_title
        FROM sessions s 
        JOIN users u ON s.tutor_id = u.id 
        LEFT JOIN courses c ON s.course_id = c.id
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

    # Get current tutor ID
    current_tutor_id = session['user_id']

    # Get assigned students
    students = conn.execute('''
        SELECT DISTINCT u.id, u.username, u.email 
        FROM users u 
        JOIN sessions s ON u.id = s.student_id 
        WHERE s.tutor_id = ?
    ''', (current_tutor_id,)).fetchall()

    # Get sessions and manually join the data
    raw_sessions = conn.execute('''
        SELECT * FROM sessions WHERE tutor_id = ? 
        ORDER BY scheduled_date ASC, scheduled_time ASC
    ''', (current_tutor_id,)).fetchall()

    # Manually get student and course info for each session
    sessions = []
    for session_row in raw_sessions:
        # Get student name
        student = conn.execute('SELECT username FROM users WHERE id = ?', (session_row['student_id'],)).fetchone()
        student_name = student['username'] if student else f"Student ID {session_row['student_id']}"

        # Get course title
        course_title = "General Tutoring"
        if session_row['course_id']:
            course = conn.execute('SELECT title FROM courses WHERE id = ?', (session_row['course_id'],)).fetchone()
            course_title = course['title'] if course else f"Course ID {session_row['course_id']}"

        # Create session dict with all info
        session_dict = dict(session_row)
        session_dict['student_name'] = student_name
        session_dict['course_title'] = course_title
        sessions.append(session_dict)

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


# Tutor availability management
@app.route('/tutor/availability')
@login_required
@role_required('tutor')
def tutor_availability():
    conn = get_db_connection()

    # Get current availability
    availability = conn.execute('''
        SELECT * FROM tutor_availability 
        WHERE tutor_id = ? 
        ORDER BY day_of_week, start_time
    ''', (session['user_id'],)).fetchall()

    conn.close()

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    return render_template('tutor_availability.html', availability=availability, days=days)


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


# Student progress view for tutors
@app.route('/api/student_progress/<int:student_id>')
@login_required
@role_required('tutor')
def student_progress(student_id):
    conn = get_db_connection()

    # Get student info
    student = conn.execute('SELECT * FROM users WHERE id = ? AND role = "student"',
                           (student_id,)).fetchone()

    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404

    # Get student's course progress
    progress_data = conn.execute('''
        SELECT c.title, c.description, p.progress, p.updated_at
        FROM courses c
        JOIN progress p ON c.id = p.course_id
        WHERE p.user_id = ?
        ORDER BY p.updated_at DESC
    ''', (student_id,)).fetchall()

    conn.close()

    # Convert to list of dictionaries for JSON response
    progress_list = []
    for row in progress_data:
        progress_list.append({
            'title': row['title'],
            'description': row['description'],
            'progress': row['progress'],
            'updated_at': row['updated_at']
        })

    return jsonify({
        'student': {
            'id': student['id'],
            'username': student['username'],
            'email': student['email']
        },
        'progress': progress_list
    })


# API endpoints for session management
@app.route('/api/join_session/<int:session_id>', methods=['POST'])
@login_required
def join_session(session_id):
    conn = get_db_connection()

    # Update session status to 'in_progress'
    conn.execute('''
        UPDATE sessions 
        SET status = 'in_progress'
        WHERE id = ? AND student_id = ?
    ''', (session_id, session['user_id']))

    conn.commit()
    conn.close()

    flash('Successfully joined the session! Session is now in progress.', 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/api/start_session/<int:session_id>', methods=['POST'])
@login_required
@role_required('tutor')
def start_session(session_id):
    conn = get_db_connection()

    # Update session status to 'in_progress'
    conn.execute('''
        UPDATE sessions 
        SET status = 'in_progress'
        WHERE id = ? AND tutor_id = ?
    ''', (session_id, session['user_id']))

    conn.commit()
    conn.close()

    flash('Session started successfully! You are now teaching.', 'success')
    return redirect(url_for('tutor_dashboard'))


@app.route('/api/end_session/<int:session_id>', methods=['POST'])
@login_required
@role_required('tutor')
def end_session(session_id):
    notes = request.form.get('notes', '')
    rating = request.form.get('rating', '')

    conn = get_db_connection()

    # Update session status to 'completed'
    final_notes = f"{notes}"
    if rating:
        final_notes += f" | Rating: {rating}"

    conn.execute('''
        UPDATE sessions 
        SET status = 'completed', notes = ?
        WHERE id = ? AND tutor_id = ?
    ''', (final_notes, session_id, session['user_id']))

    conn.commit()
    conn.close()

    flash('Session completed successfully! Summary has been saved.', 'success')
    return redirect(url_for('tutor_dashboard'))


@app.route('/api/cancel_session/<int:session_id>', methods=['POST'])
@login_required
def cancel_session(session_id):
    conn = get_db_connection()

    # Update session status to 'cancelled'
    conn.execute('''
        UPDATE sessions 
        SET status = 'cancelled'
        WHERE id = ? AND (student_id = ? OR tutor_id = ?)
    ''', (session_id, session['user_id'], session['user_id']))

    conn.commit()
    conn.close()

    flash('Session has been cancelled.', 'warning')
    if session['user_role'] == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        return redirect(url_for('tutor_dashboard'))


# Session management pages
@app.route('/session/<int:session_id>/join')
@login_required
@role_required('student')
def join_session_page(session_id):
    conn = get_db_connection()

    # Get session details
    session_data = conn.execute('''
        SELECT s.*, u.username as tutor_name, c.title as course_title
        FROM sessions s
        JOIN users u ON s.tutor_id = u.id
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE s.id = ? AND s.student_id = ?
    ''', (session_id, session['user_id'])).fetchone()

    conn.close()

    if not session_data:
        flash('Session not found or access denied.', 'error')
        return redirect(url_for('student_dashboard'))

    return render_template('join_session.html', session_data=session_data)


@app.route('/session/<int:session_id>/start')
@login_required
@role_required('tutor')
def start_session_page(session_id):
    conn = get_db_connection()

    # Get session details
    session_data = conn.execute('''
        SELECT s.*, u.username as student_name, c.title as course_title
        FROM sessions s
        JOIN users u ON s.student_id = u.id
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE s.id = ? AND s.tutor_id = ?
    ''', (session_id, session['user_id'])).fetchone()

    conn.close()

    if not session_data:
        flash('Session not found or access denied.', 'error')
        return redirect(url_for('tutor_dashboard'))

    return render_template('start_session.html', session_data=session_data)


@app.route('/session/<int:session_id>/end')
@login_required
@role_required('tutor')
def end_session_page(session_id):
    conn = get_db_connection()

    # Get session details
    session_data = conn.execute('''
        SELECT s.*, u.username as student_name, c.title as course_title
        FROM sessions s
        JOIN users u ON s.student_id = u.id
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE s.id = ? AND s.tutor_id = ?
    ''', (session_id, session['user_id'])).fetchone()

    conn.close()

    if not session_data:
        flash('Session not found or access denied.', 'error')
        return redirect(url_for('tutor_dashboard'))

    return render_template('end_session.html', session_data=session_data)


if __name__ == '__main__':
    # Check if database exists, if not create it
    if not os.path.exists('learning_hub.db'):
        print("Creating new database...")
        init_db()
    else:
        # Update existing database with correct passwords
        print("Updating existing database...")
        conn = get_db_connection()
        try:
            # Update all existing demo users with simple passwords
            demo_users = [
                ('password123', 'admin@learninghub.edu'),
                ('password123', 'john.doe@student.edu'),
                ('password123', 'jane.smith@tutor.edu'),
                ('password123', 'parent@family.com'),
                ('password123', 'content@learninghub.edu')
            ]

            for password, email in demo_users:
                conn.execute('UPDATE users SET password = ? WHERE email = ?', (password, email))

            conn.commit()
            print("Demo user passwords updated to 'password123'")
        except Exception as e:
            print(f"Error updating passwords: {e}")
        finally:
            conn.close()

    app.run(debug=True)