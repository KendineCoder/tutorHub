"""
Modular Flask Application with Blueprint Structure
"""
from flask import Flask
import os
from utils.database import init_db
from routes.main import main_bp
from routes.auth import auth_bp
from routes.student import student_bp
from routes.tutor import tutor_bp
from routes.admin import admin_bp
from routes.parent import parent_bp
from routes.content import content_bp
from routes.api import api_bp


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-change-in-production'
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(api_bp)
    
    return app


# Create app instance
app = create_app()

# Initialize database if it doesn't exist
if __name__ == '__main__':
    if not os.path.exists('learning_hub.db'):
        init_db()
    app.run(debug=True)