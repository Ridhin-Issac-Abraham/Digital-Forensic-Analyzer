import sqlite3
from datetime import datetime
import json
import os
from web_app.config.roles import ROLE_PERMISSIONS  # Change to absolute import

class RoleManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_user_permissions(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role, permissions FROM users WHERE id = ?', (user_id,))
            role, permissions = cursor.fetchone()
            return json.loads(permissions) if permissions else []

    def update_user_role(self, user_id, new_role):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            permissions = json.dumps(ROLE_PERMISSIONS.get(new_role, []))
            cursor.execute('''
                UPDATE users 
                SET role = ?, permissions = ?, updated_at = ? 
                WHERE id = ?
            ''', (new_role, permissions, datetime.now(), user_id))
            conn.commit()