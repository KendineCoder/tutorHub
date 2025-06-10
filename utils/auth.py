"""
Authentication decorators and utilities
"""
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    """Decorator to require specific role for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator