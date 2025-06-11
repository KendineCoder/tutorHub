-- schema.sql - SQLite Database Schema with Sample Data
-- Personalized Learning Hub Database

-- Users table (Students, Tutors, Admins, Parents, Content Managers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'tutor', 'admin', 'parent', 'content_manager')),
    parent_id INTEGER,
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES users (id)
);

-- Courses table
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    difficulty_level TEXT DEFAULT 'beginner',
    estimated_duration INTEGER, -- in hours
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- Lessons table
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    lesson_order INTEGER NOT NULL,
    duration INTEGER, -- in minutes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
);

-- User progress tracking
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    lesson_id INTEGER,
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    completed BOOLEAN DEFAULT FALSE,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, course_id, lesson_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE SET NULL
);

-- Tutoring sessions
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    tutor_id INTEGER NOT NULL,
    course_id INTEGER,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    duration INTEGER DEFAULT 60, -- in minutes
    status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'rescheduled')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (tutor_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE SET NULL
);

-- Tutor availability
CREATE TABLE IF NOT EXISTS tutor_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tutor_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Course enrollments
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrolled_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completion_date TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'dropped')),
    UNIQUE(student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
);

-- Notifications/Messages
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info' CHECK (type IN ('info', 'success', 'warning', 'error')),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Session reviews and ratings
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(session_id, student_id)
);

-- ==================== SAMPLE DATA ====================

-- Insert sample users with plain text passwords (using INSERT OR REPLACE to update existing users)
INSERT OR REPLACE INTO users (id, username, email, password, role) VALUES
(1, 'admin_user', 'admin@learninghub.edu', 'password123', 'admin'),
(2, 'john_student', 'john.doe@student.edu', 'password123', 'student'),
(3, 'jane_tutor', 'jane.smith@tutor.edu', 'password123', 'tutor'),
(4, 'parent_jones', 'parent@family.com', 'password123', 'parent'),
(5, 'content_manager', 'content@learninghub.edu', 'password123', 'content_manager'),
(6, 'sarah_student', 'sarah@student.edu', 'password123', 'student'),
(7, 'mike_tutor', 'mike@tutor.edu', 'password123', 'tutor');

-- Insert sample courses
INSERT OR IGNORE INTO courses (title, description, difficulty_level, estimated_duration, created_by) VALUES
('Introduction to Python Programming', 'Learn the fundamentals of Python programming language', 'beginner', 40, 5),
('Advanced Mathematics', 'Calculus, Algebra, and Statistics for advanced students', 'advanced', 60, 5),
('English Literature', 'Classic and modern literature analysis and writing', 'intermediate', 30, 5),
('Basic Physics', 'Fundamental concepts in physics with practical examples', 'beginner', 35, 5),
('Web Development Basics', 'HTML, CSS, and JavaScript fundamentals', 'beginner', 45, 5);

-- Insert sample lessons
INSERT OR IGNORE INTO lessons (course_id, title, content, lesson_order, duration) VALUES
-- Python Programming lessons
(1, 'Variables and Data Types', 'Understanding variables, strings, numbers, and basic data types in Python', 1, 45),
(1, 'Control Structures', 'If statements, loops, and conditional logic', 2, 60),
(1, 'Functions and Modules', 'Creating reusable code with functions and importing modules', 3, 75),
(1, 'Working with Lists and Dictionaries', 'Data structures and manipulation techniques', 4, 90),

-- Mathematics lessons
(2, 'Limits and Continuity', 'Introduction to calculus concepts', 1, 90),
(2, 'Derivatives', 'Understanding rates of change and differentiation', 2, 120),
(2, 'Integration', 'Finding areas under curves and antiderivatives', 3, 120),

-- English Literature lessons
(3, 'Poetry Analysis', 'Understanding meter, rhyme, and literary devices', 1, 60),
(3, 'Character Development', 'Analyzing character arcs in novels', 2, 75),
(3, 'Essay Writing Techniques', 'Structure and argumentation in academic writing', 3, 90);

-- Insert sample enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, status) VALUES
(2, 1, 'active'),  -- john_student enrolled in Python
(2, 4, 'active'),  -- john_student enrolled in Physics
(6, 1, 'active'),  -- sarah_student enrolled in Python
(6, 3, 'active'),  -- sarah_student enrolled in English
(6, 5, 'active');  -- sarah_student enrolled in Web Dev

-- Insert sample progress
INSERT OR IGNORE INTO progress (user_id, course_id, progress, completed) VALUES
(2, 1, 75, FALSE),  -- john_student 75% through Python
(2, 4, 30, FALSE),  -- john_student 30% through Physics
(6, 1, 50, FALSE),  -- sarah_student 50% through Python
(6, 3, 85, FALSE),  -- sarah_student 85% through English
(6, 5, 20, FALSE);  -- sarah_student 20% through Web Dev

-- Insert sample sessions
INSERT OR IGNORE INTO sessions (student_id, tutor_id, course_id, scheduled_date, scheduled_time, status) VALUES
(2, 3, 1, '2025-06-10', '14:00', 'scheduled'),  -- john with jane for Python
(2, 7, 4, '2025-06-12', '15:30', 'scheduled'),  -- john with mike for Physics
(6, 3, 3, '2025-06-11', '10:00', 'scheduled'),  -- sarah with jane for English
(6, 7, 5, '2025-06-13', '16:00', 'scheduled');  -- sarah with mike for Web Dev

-- Insert tutor availability
INSERT OR IGNORE INTO tutor_availability (tutor_id, day_of_week, start_time, end_time) VALUES
(3, 1, '09:00', '17:00'),  -- jane available Monday 9-5
(3, 2, '09:00', '17:00'),  -- jane available Tuesday 9-5
(3, 3, '09:00', '17:00'),  -- jane available Wednesday 9-5
(7, 1, '10:00', '18:00'),  -- mike available Monday 10-6
(7, 3, '10:00', '18:00'),  -- mike available Wednesday 10-6
(7, 5, '10:00', '18:00');  -- mike available Friday 10-6

-- Insert sample notifications
INSERT OR IGNORE INTO notifications (user_id, title, message, type) VALUES
(2, 'Welcome!', 'Welcome to the Learning Hub! Start exploring your courses.', 'info'),
(2, 'Session Reminder', 'You have a Python tutoring session tomorrow at 2:00 PM', 'warning'),
(6, 'Great Progress!', 'You have completed 85% of your English Literature course!', 'success'),
(3, 'New Student Assigned', 'You have been assigned a new student: Sarah', 'info');

-- Insert sample reviews
INSERT OR IGNORE INTO reviews (session_id, student_id, rating, review_text) VALUES
(1, 2, 5, 'Great session, learned a lot!'),
(2, 2, 4, 'Good session, but could be improved.'),
(3, 6, 5, 'Excellent explanation of concepts.'),
(4, 6, 3, 'The session was okay, not very engaging.');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_progress_user_course ON progress(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_tutor ON sessions(tutor_id);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_reviews_session_student ON reviews(session_id, student_id);