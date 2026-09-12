CREATE TABLE IF NOT EXISTS Users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('Student', 'Lecturer', 'Admin'))
);

CREATE TABLE IF NOT EXISTS Students (
    student_code VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    class_id VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE IF NOT EXISTS Lecturers (
    lecturer_code VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE IF NOT EXISTS ClassSessions (
    session_id VARCHAR(36) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    lecturer_code VARCHAR(20) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    session_code VARCHAR(10) UNIQUE NOT NULL,
    FOREIGN KEY (lecturer_code) REFERENCES Lecturers(lecturer_code)
);

CREATE TABLE IF NOT EXISTS AttendanceRecord (
    record_id VARCHAR(36) PRIMARY KEY,
    student_code VARCHAR(20) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    timestamp DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Present', 'Late', 'Absent')),
    FOREIGN KEY (student_code) REFERENCES Students(student_code),
    FOREIGN KEY (session_id) REFERENCES ClassSessions(session_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_student_session
    ON AttendanceRecord(student_code, session_id);