import sqlite3
import os

DB_PATH = "F:/MSCAIML/S6/digital_forensics/src/database/users.db"

if os.path.exists(DB_PATH):
    print(f"✅ Database found at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    print("\nUsers in database:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[3]}")
    conn.close()
else:
    print(f"❌ Database not found at: {DB_PATH}")