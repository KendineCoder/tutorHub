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
    db = get_db_connection()
    with open('schema.sql', 'r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def init_db_with_app(app):
    """Initialize database with schema using Flask app context"""
    with app.app_context():
        db = get_db_connection()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()