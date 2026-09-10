from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    user_id: str
    username: str
    password_hash: str
    full_name: str
    email: str
    role: str


@dataclass(frozen=True)
class Student:
    student_code: str
    user_id: str
    class_id: str


@dataclass(frozen=True)
class Lecturer:
    lecturer_code: str
    user_id: str
    department: str


@dataclass(frozen=True)
class ClassSession:
    session_id: str
    course_name: str
    lecturer_code: str
    start_time: datetime
    end_time: datetime
    session_code: str


@dataclass(frozen=True)
class AttendanceRecord:
    record_id: str
    student_code: str
    session_id: str
    timestamp: datetime
    status: str