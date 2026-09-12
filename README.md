# Student Attendance System

## Backend

The shared backend uses SQLite and Python's standard library. Initialize a persistent database with:

```sh
python3 -c "from backend.database import connect, initialize; c=connect('attendance.db'); initialize(c)"
```

Run the API with `python3 -m backend.api`. The five shared entities are defined in [migrations/001_initial.sql](migrations/001_initial.sql), and typed model definitions are in [backend/models.py](backend/models.py).

### Authentication

`POST /api/auth/login` accepts `{"username":"...","password":"..."}` and returns a bearer `token` plus the authenticated `user` object (`user_id`, `username`, `full_name`, `email`, and `role`). Invalid credentials always return the same `401` error. `GET /api/auth/me` accepts `Authorization: Bearer <token>` and returns the current authentication state. Tokens expire after 30 minutes of inactivity.

### User management

All `/api/users` endpoints require an authenticated Admin token. `GET /api/users` lists users. `POST /api/users` creates a user with `username`, `password`, `full_name`, `email`, and `role`; Student users additionally require `student_code` and `class_id`, while Lecturer users require `lecturer_code` and `department`. `PUT /api/users/<user_id>` updates user fields and optionally `password`. `DELETE /api/users/<user_id>` removes the user and its profile. Duplicate usernames/emails return `409`; non-Admin callers return `403`.

Run the focused test suite with `python3 -m unittest discover -s tests -v`.

### Requirement traceability

- UC01 User Authentication: `POST /api/auth/login`, `GET /api/auth/me`
- UC04 User Management: `GET /api/users`, `POST /api/users`, `PUT /api/users/<user_id>`, `DELETE /api/users/<user_id>`
- Roles: `Student`, `Lecturer`, `Admin`; only Admin may use UC04.
- Passwords use scrypt hashes and are never returned by the API.
- Bearer sessions expire after 30 minutes of inactivity.
- Shared entities: `Users`, `Students`, `Lecturers`, `ClassSessions`, `AttendanceRecord`.

### Attendance and reports

All attendance endpoints use the bearer token returned by login. A Lecturer creates sessions with `POST /api/sessions` using `course_name`, `start_time`, and `end_time` in ISO 8601 format. The server assigns `session_id` and an unpredictable `session_code`; `GET /api/sessions` lists only that lecturer's sessions.

A Student submits attendance with `POST /api/attendance` and `{"session_code":"..."}`. The server resolves the student's profile, checks the session window, records the server timestamp, and accepts `Present`, `Late`, or `Absent` (default `Present`). A student can submit only once per session. `GET /api/attendance/history` returns only the authenticated student's records.

`GET /api/reports/attendance` is restricted to Lecturers and returns attendance for their own sessions. Add `?session_id=...` to limit the report to one owned session. Unauthenticated requests return `401`; authenticated users with the wrong role return `403`.

Run all tests with:

```sh
python3 -m unittest discover -s tests -v
```