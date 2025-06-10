# API Endpoints Restructured

## Overview

The API endpoints have been split from the monolithic `routes/api.py` into organized blueprint-based modules for better maintainability and logical separation.

## New API Structure

### Content Management APIs (`/content/api/`)

**File**: `routes/content.py`

**Course Management:**

- `POST /content/api/courses` - Create course
- `GET /content/api/courses/<id>` - Get course details
- `PUT /content/api/courses/<id>` - Update course
- `DELETE /content/api/courses/<id>` - Delete course

**Lesson Management:**

- `POST /content/api/lessons` - Create lesson
- `GET /content/api/lessons/<id>` - Get lesson details
- `GET /content/api/courses/<id>/lessons` - Get course lessons
- `PUT /content/api/lessons/<id>` - Update lesson
- `DELETE /content/api/lessons/<id>` - Delete lesson

### Student Dashboard APIs (`/student/api/`)

**File**: `routes/student.py`

**Course Discovery & Enrollment:**

- `GET /student/api/courses/available` - Get available courses for discovery
- `GET /student/api/courses/enrolled` - Get enrolled courses
- `POST /student/api/courses/<id>/enroll` - Enroll in course
- `POST /student/api/courses/<id>/unenroll` - Unenroll from course
- `POST /student/api/courses/<id>/complete` - Mark course as completed

**Progress Tracking:**

- `POST /student/api/progress/update` - Update lesson progress
- `GET /student/api/students/stats` - Get dashboard statistics

**Tutor Discovery & Session Rating:**

- `GET /student/api/tutors/find` - Find tutors with filtering
- `POST /student/api/sessions/<id>/rate` - Rate completed session

### Tutor Management APIs (`/tutor/api/`)

**File**: `routes/tutor.py`

**Tutor Discovery:**

- `GET /tutor/api/tutors/available` - Get available tutors
- `GET /tutor/api/tutors/<id>/availability` - Get tutor availability

**Session Management:**

- `POST /tutor/api/sessions` - Create session
- `PUT /tutor/api/sessions/<id>` - Update session
- `DELETE /tutor/api/sessions/<id>` - Cancel session
- `GET /tutor/api/users/<id>/sessions` - Get user sessions

### Admin Management APIs (`/admin/api/`)

**File**: `routes/admin.py`

**User Management:**

- `GET /admin/api/users` - Get all users with filtering
- `GET /admin/api/users/<id>` - Get user details
- `PUT /admin/api/users/<id>` - Update user
- `DELETE /admin/api/users/<id>` - Soft delete user
- `DELETE /admin/api/users/<id>/hard-delete` - Hard delete user
- `POST /admin/api/users/<id>/toggle-status` - Toggle user status
- `POST /admin/api/users/<id>/reset-password` - Reset user password

### Legacy/Shared APIs (`/api/`)

**File**: `routes/api.py`

**Legacy Endpoints:**

- `POST /api/update_progress` - Legacy progress update endpoint

## Updated JavaScript Files

### Frontend Integration Updates:

1. **lesson-management.js**: Updated baseUrl to `/content/api`
2. **user-management.js**: Updated baseUrl to `/admin/api`
3. **course_create.html**: Updated to use `/content/api/courses`
4. **lesson_create.html**: Updated to use `/content/api/lessons`

### Unchanged:

- **main.js**: Still uses `/api/update_progress` (legacy endpoint maintained)

## Benefits of This Structure:

1. **Logical Separation**: APIs are organized by user role and functionality
2. **Better Permissions**: Each blueprint can have role-specific authentication
3. **Maintainability**: Easier to find and update specific functionality
4. **Modularity**: Each module is self-contained with its own concerns
5. **Scalability**: Easy to add new features to specific user roles
6. **Security**: Role-based API access is more explicit

## Migration Notes:

- All existing functionality is preserved
- Legacy endpoint maintained for backward compatibility
- JavaScript files updated to use new endpoints
- Template files updated to use appropriate blueprint APIs
- No breaking changes for end users

## Testing Required:

- [ ] Course creation and management (Content Manager)
- [ ] Lesson creation and management (Content Manager)
- [ ] Student dashboard functionality
- [ ] User management (Admin)
- [ ] Session scheduling (Tutor/Student)
- [ ] Legacy progress update endpoint
