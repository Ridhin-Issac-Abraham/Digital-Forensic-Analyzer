import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def update_database():
    # SQL statements to update the table
    update_sql = '''
    ALTER TABLE users 
    ADD COLUMN permissions TEXT DEFAULT '[]';
    
    ALTER TABLE users 
    ADD COLUMN last_login DATETIME;
    
    ALTER TABLE users 
    ADD COLUMN active BOOLEAN DEFAULT 1;
    '''
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Execute the SQL statements
        cursor.executescript(update_sql)

        # Commit the changes
        conn.commit()
        print("✅ Database updated successfully!")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()