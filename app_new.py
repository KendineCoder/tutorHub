"""
TutorHub - Learning Management System
Modular Flask Application using Blueprint Architecture
"""
from flask import Flask
import os

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Import and register blueprints
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.tutor import tutor_bp
    from routes.admin import admin_bp
    from routes.parent import parent_bp
    from routes.content import content_bp
    from routes.api import api_bp
    
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

# Create the app instance
app = create_app()

if __name__ == '__main__':
    # Initialize database on first run
    from utils.database import init_db
    init_db()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)