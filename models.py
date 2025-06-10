
class User:
    def __init__(self, id, username, email, role, created_at):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.created_at = created_at

class Course:
    def __init__(self, id, title, description, created_at):
        self.id = id
        self.title = title
        self.description = description
        self.created_at = created_at

class Lesson:
    def __init__(self, id, course_id, title, content, lesson_order):
        self.id = id
        self.course_id = course_id
        self.title = title
        self.content = content
        self.lesson_order = lesson_order

class Progress:
    def __init__(self, id, user_id, course_id, progress, updated_at):
        self.id = id
        self.user_id = user_id
        self.course_id = course_id
        self.progress = progress
        self.updated_at = updated_at