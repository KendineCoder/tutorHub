"""
Admin dashboard and user management
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
import sqlite3
from utils.auth import login_required, role_required
from utils.database import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ========== DASHBOARD ROUTES ==========

@admin_bp.route('/')
@login_required
@role_required('admin')
def dashboard():
    conn = get_db_connection()

    # Get statistics
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    total_courses = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()['count']
    total_sessions = conn.execute('SELECT COUNT(*) as count FROM sessions').fetchone()['count']
    
    # Get recent registrations
    recent_users = conn.execute('''
        SELECT id, username, email, role, created_at, is_active 
        FROM users 
        ORDER BY created_at DESC LIMIT 10
    ''').fetchall()

    conn.close()
    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_courses=total_courses,
                           total_sessions=total_sessions,
                           recent_users=recent_users)


@admin_bp.route('/users')
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
        return redirect(url_for('admin.dashboard'))
    finally:
        conn.close()


# ========== USER MANAGEMENT API ENDPOINTS ==========

@admin_bp.route('/api/users', methods=['GET'])
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


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
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


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
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


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
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


@admin_bp.route('/api/users/<int:user_id>/hard-delete', methods=['DELETE'])
@login_required
@role_required('admin')
def hard_delete_user(user_id):
    """Permanently delete a user account and all associated data"""
    # Prevent admin from deleting their own account
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 403
    
    conn = get_db_connection()
    try:
        # Check if user exists
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Hard delete - permanently remove user and cascade delete related data
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'User {user["username"]} has been permanently deleted'})
        
    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


@admin_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
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


@admin_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
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