"""
Tutor dashboard and functionality
"""
from flask import Blueprint, render_template, session
from utils.auth import login_required, role_required
from utils.database import get_db_connection

tutor_bp = Blueprint('tutor', __name__, url_prefix='/tutor')


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