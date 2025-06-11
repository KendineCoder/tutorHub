#!/usr/bin/env python3
"""
Migration script to add reschedule columns to sessions table
"""
import sqlite3
import os
import sys

def add_reschedule_columns():
    """Add reschedule_reason and rescheduled_at columns to sessions table"""
      # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'learning_hub.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(sessions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns in sessions table: {existing_columns}")
        
        # Add reschedule_reason column if it doesn't exist
        if 'reschedule_reason' not in existing_columns:
            print("Adding reschedule_reason column...")
            cursor.execute("""
                ALTER TABLE sessions 
                ADD COLUMN reschedule_reason TEXT DEFAULT NULL
            """)
            print("✓ reschedule_reason column added")
        else:
            print("✓ reschedule_reason column already exists")
        
        # Add rescheduled_at column if it doesn't exist
        if 'rescheduled_at' not in existing_columns:
            print("Adding rescheduled_at column...")
            cursor.execute("""
                ALTER TABLE sessions 
                ADD COLUMN rescheduled_at TIMESTAMP DEFAULT NULL
            """)
            print("✓ rescheduled_at column added")
        else:
            print("✓ rescheduled_at column already exists")
        
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(sessions)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns in sessions table: {updated_columns}")
        
        conn.close()
        print("\n✅ Migration completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = add_reschedule_columns()
    sys.exit(0 if success else 1)
