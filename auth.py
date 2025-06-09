from flask import session, flash, redirect, url_for
from functools import wraps
import sqlite3


def authenticate_user(email, password):
    """Authenticate user credentials"""
    conn = sqlite3.connect('learning_hub.db')
    conn.row_factory = sqlite3.Row

    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and user['password'] == password:
        return user
    return None


def create_user(username, email, password, role):
    """Create a new user account"""
    conn = sqlite3.connect('learning_hub.db')
    try:
        conn.execute('''INSERT INTO users (username, email, password, role) 
                       VALUES (?, ?, ?, ?)''',
                     (username, email, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(user):
    """Log in a user by setting session variables"""
    session['user_id'] = user['id']
    session['user_role'] = user['role']
    session['username'] = user['username']


def logout_user():
    """Log out the current user"""
    session.clear()


def require_role(role):
    """Decorator to require specific user role"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_login(f):
    """Decorator to require user login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function