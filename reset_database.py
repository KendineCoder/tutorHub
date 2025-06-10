#!/usr/bin/env python3
"""
Database Reset Script for Learning Hub
This script will delete the existing database and create a new one with simple passwords.
"""

import os
import sqlite3


def reset_database():
    """Delete existing database and create a new one"""

    # Remove existing database
    if os.path.exists('learning_hub.db'):
        os.remove('learning_hub.db')
        print("✅ Existing database deleted")

    # Create new database connection
    conn = sqlite3.connect('learning_hub.db')
    conn.row_factory = sqlite3.Row

    try:
        # Read and execute schema
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)

        print("✅ New database created with sample data")
        print("\n🔑 Demo Accounts (password: password123):")
        print("   • Admin: admin@learninghub.edu")
        print("   • Student: john.doe@student.edu")
        print("   • Tutor: jane.smith@tutor.edu")
        print("   • Parent: parent@family.com")
        print("   • Content Manager: content@learninghub.edu")
        print("\n🚀 Run 'python app.py' to start the application")

    except Exception as e:
        print(f"❌ Error creating database: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("🔄 Resetting Learning Hub Database...")
    reset_database()