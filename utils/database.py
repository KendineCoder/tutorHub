"""
Database connection utilities
"""
import sqlite3
from flask import current_app


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect('learning_hub.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with schema"""
    with current_app.app_context():
        db = get_db_connection()
        with current_app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()