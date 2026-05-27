"""
Authentication routes - Login, Register, Logout, User Management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps

from .models import (
    authenticate_user, create_user, get_all_users, 
    delete_user, update_user_password, set_user_admin,
    get_user_by_id
)

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        success, user, message = authenticate_user(username, password)
        if success and user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash(message or 'Invalid username or password.', 'error')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and handler."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'error')
            return render_template('register.html')
        
        success, message = create_user(username, password, email)
        if success:
            flash('Account created! Please login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@admin_required
def users():
    """User management page (admin only)."""
    users = get_all_users()
    return render_template('users.html', users=users)


@auth_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user_route(user_id):
    """Delete a user (admin only)."""
    if session.get('user_id') == user_id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('auth.users'))
    
    success, message = delete_user(user_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/reset_password/<int:user_id>', methods=['POST'])
@admin_required
def reset_password_route(user_id):
    """Reset user password (admin only)."""
    new_password = request.form.get('new_password', '')
    if not new_password or len(new_password) < 4:
        flash('Password must be at least 4 characters.', 'error')
        return redirect(url_for('auth.users'))
    
    success, message = update_user_password(user_id, new_password)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/set_admin/<int:user_id>', methods=['POST'])
@admin_required
def set_admin_route(user_id):
    """Set user admin status (admin only)."""
    is_admin = request.form.get('is_admin') == 'on'
    success, message = set_user_admin(user_id, is_admin)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('auth.users'))


@auth_bp.route('/check')
def check_auth():
    """API endpoint to check authentication status."""
    return jsonify({
        'logged_in': 'user_id' in session,
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    })
