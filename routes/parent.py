"""
Parent dashboard and functionality
"""
from flask import Blueprint, render_template, session
from utils.auth import login_required, role_required
from utils.database import get_db_connection

parent_bp = Blueprint('parent', __name__, url_prefix='/parent')


@parent_bp.route('/')
@login_required
@role_required('parent')
def dashboard():
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