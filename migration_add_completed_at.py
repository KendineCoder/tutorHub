"""
Migration script to add completed_at column to sessions table
"""
import sqlite3
from utils.database import get_db_connection

def add_completed_at_column():
    """Add completed_at column to sessions table if it doesn't exist"""
    conn = get_db_connection()
    try:
        # Check if column already exists
        cursor = conn.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'completed_at' not in columns:
            print("Adding completed_at column to sessions table...")
            conn.execute('''
                ALTER TABLE sessions 
                ADD COLUMN completed_at TIMESTAMP DEFAULT NULL
            ''')
            conn.commit()
            print("Column added successfully!")
        else:
            print("completed_at column already exists.")
            
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_completed_at_column()
