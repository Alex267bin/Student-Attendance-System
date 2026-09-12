import unittest
from datetime import datetime, timedelta, timezone

from backend.api import AttendanceAPI
from backend.security import hash_password
from tests.test_api import APIClient


class TestNhanQAEdgeCases(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)

        # Use the same test users and credentials as tests/test_api.py
        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            (
                "admin-id",
                "admin",
                hash_password("admin-pass"),
                "System Admin",
                "admin@example.com",
                "Admin",
            ),
        )

        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            (
                "student-id",
                "student",
                hash_password("student-pass"),
                "A Student",
                "student@example.com",
                "Student",
            ),
        )

        self.api.connection.execute(
            "INSERT INTO Students VALUES (?, ?, ?)",
            ("ST01", "student-id", "C01"),
        )

        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            (
                "lecturer-id",
                "lecturer",
                hash_password("lecturer-pass"),
                "A Lecturer",
                "lecturer@example.com",
                "Lecturer",
            ),
        )

        self.api.connection.execute(
            "INSERT INTO Lecturers VALUES (?, ?, ?)",
            ("LE01", "lecturer-id", "Computer Science"),
        )

        self.api.connection.commit()

    def tearDown(self):
        self.api.connection.close()

    def login(self, username, password):
        return self.client.request(
            "POST",
            "/api/auth/login",
            {
                "username": username,
                "password": password,
            },
        )

    def test_student_cannot_access_reports(self):
        status, login = self.login("student", "student-pass")
        self.assertEqual(status, 200)

        status, _ = self.client.request(
            "GET",
            "/api/reports/attendance",
            token=login["token"],
        )

        self.assertEqual(status, 403)

    def test_attendance_with_invalid_session_code(self):
        status, login = self.login("student", "student-pass")
        self.assertEqual(status, 200)

        status, _ = self.client.request(
            "POST",
            "/api/attendance",
            {"session_code": "INVALID_CODE_999"},
            token=login["token"],
        )

        self.assertEqual(status, 404)

    def test_create_session_with_invalid_time_range(self):
        status, login = self.login("lecturer", "lecturer-pass")
        self.assertEqual(status, 200)

        now = datetime.now(timezone.utc)

        invalid_session = {
            "course_name": "Time Travel Class",
            "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now - timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        status, _ = self.client.request(
            "POST",
            "/api/sessions",
            invalid_session,
            token=login["token"],
        )

        self.assertEqual(status, 400)

    def test_create_user_missing_required_payload(self):
        status, login = self.login("admin", "admin-pass")
        self.assertEqual(status, 200)

        incomplete_data = {
            "username": "missing_fields_user",
            "full_name": "Incomplete User",
        }

        status, _ = self.client.request(
            "POST",
            "/api/users",
            incomplete_data,
            token=login["token"],
        )

        self.assertEqual(status, 400)

    def test_lecturer_can_create_session_and_student_can_attend(self):
        status, lecturer_login = self.login(
            "lecturer",
            "lecturer-pass",
        )
        self.assertEqual(status, 200)

        status, student_login = self.login(
            "student",
            "student-pass",
        )
        self.assertEqual(status, 200)

        now = datetime.now(timezone.utc)

        session_data = {
            "course_name": "QA Attendance Test",
            "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now + timedelta(hours=2)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        status, session = self.client.request(
            "POST",
            "/api/sessions",
            session_data,
            token=lecturer_login["token"],
        )

        self.assertEqual(status, 201)
        self.assertIn("session", session)
        self.assertIn("session_code", session["session"])

        status, attendance = self.client.request(
            "POST",
            "/api/attendance",
            {
                "session_code": session["session"]["session_code"],
            },
            token=student_login["token"],
        )

        self.assertEqual(status, 201)
        self.assertEqual(attendance["attendance"]["status"], "Present")

    def test_duplicate_attendance_is_rejected(self):
        status, lecturer_login = self.login(
            "lecturer",
            "lecturer-pass",
        )
        self.assertEqual(status, 200)

        status, student_login = self.login(
            "student",
            "student-pass",
        )
        self.assertEqual(status, 200)

        now = datetime.now(timezone.utc)

        session_data = {
            "course_name": "Duplicate Attendance Test",
            "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now + timedelta(hours=2)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        status, session = self.client.request(
            "POST",
            "/api/sessions",
            session_data,
            token=lecturer_login["token"],
        )

        self.assertEqual(status, 201)

        session_code = session["session"]["session_code"]

        status, _ = self.client.request(
            "POST",
            "/api/attendance",
            {"session_code": session_code},
            token=student_login["token"],
        )

        self.assertEqual(status, 201)

        status, _ = self.client.request(
            "POST",
            "/api/attendance",
            {"session_code": session_code},
            token=student_login["token"],
        )

        self.assertEqual(status, 409)

    def test_expired_session_rejects_attendance(self):
        status, lecturer_login = self.login(
            "lecturer",
            "lecturer-pass",
        )
        self.assertEqual(status, 200)

        status, student_login = self.login(
            "student",
            "student-pass",
        )
        self.assertEqual(status, 200)

        now = datetime.now(timezone.utc)

        expired_session = {
            "course_name": "Expired Class",
            "start_time": (now - timedelta(hours=3)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "end_time": (now - timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        status, session = self.client.request(
            "POST",
            "/api/sessions",
            expired_session,
            token=lecturer_login["token"],
        )

        self.assertEqual(status, 201)

        status, _ = self.client.request(
            "POST",
            "/api/attendance",
            {
                "session_code": session["session"]["session_code"],
            },
            token=student_login["token"],
        )

        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
