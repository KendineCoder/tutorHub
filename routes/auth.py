"""
Authentication routes - login, register, logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from utils.database import get_db_connection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            # Check if account is active
            if not user['is_active']:
                flash('Account is deactivated. Please contact an administrator.', 'error')
                return render_template('login.html')
            
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
        finally:
            conn.close()

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))