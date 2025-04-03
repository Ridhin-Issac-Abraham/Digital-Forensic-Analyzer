from functools import wraps
from flask import session, redirect, url_for, flash
from web_app.auth.role_manager import RoleManager  # Change to absolute import
import os

# Define database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'database', 'users.db')

def role_required(required_permissions):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            
            role_manager = RoleManager(DB_PATH)
            user_permissions = role_manager.get_user_permissions(session['user_id'])
            
            if isinstance(required_permissions, str):
                required_permissions = [required_permissions]
            
            if not all(perm in user_permissions for perm in required_permissions):
                flash('Access denied: Insufficient permissions', 'error')
                return redirect(url_for('dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator