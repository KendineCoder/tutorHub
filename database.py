import sqlite3
from datetime import datetime


def create_connection():
    """Create a database connection to SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect('learning_hub.db')
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"Error connecting to database: {e}")
    return conn


def create_tables():
    """Create tables in the database"""
    conn = create_connection()
    if conn is not None:
        try:
            with open('schema.sql', 'r') as sql_file:
                sql_script = sql_file.read()
                conn.executescript(sql_script)
                conn.commit()
                print("Tables created successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create database connection")


def insert_sample_data():
    """Insert sample data into the database"""
    conn = create_connection()
    if conn is not None:
        try:
            # Sample users with plain text passwords
            users = [
                ('admin', 'admin@learninghub.edu', 'admin', 'password123'),
                ('john_student', 'john.doe@student.edu', 'student', 'password123'),
                ('jane_tutor', 'jane.smith@tutor.edu', 'tutor', 'password123'),
                ('parent1', 'parent@family.com', 'parent', 'password123'),
                ('content_mgr', 'content@learninghub.edu', 'content_manager', 'password123')
            ]

            for user in users:
                conn.execute('''INSERT INTO users (username, email, role, password) 
                               VALUES (?, ?, ?, ?)''', user)

            conn.commit()
            print("Sample data inserted successfully")
        except Exception as e:
            print(f"Error inserting sample data: {e}")
        finally:
            conn.close()