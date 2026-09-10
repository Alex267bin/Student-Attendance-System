import io
import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from backend.api import AttendanceAPI
from backend.security import hash_password


class APIClient:
    def __init__(self, api):
        self.api = api

    def request(self, method, path, payload=None, token=None):
        body = json.dumps(payload or {}).encode()
        environment = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        if token:
            environment["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        result = {}
        def start_response(status, headers):
            result["status"] = int(status.split()[0])
        result["body"] = json.loads(b"".join(self.api(environment, start_response)))
        return result["status"], result["body"]


class AttendanceAPITest(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)
        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("admin-id", "admin", hash_password("admin-pass"), "System Admin", "admin@example.com", "Admin"),
        )
        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("student-id", "student", hash_password("student-pass"), "A Student", "student@example.com", "Student"),
        )
        self.api.connection.execute("INSERT INTO Students VALUES (?, ?, ?)", ("ST01", "student-id", "C01"))
        self.api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("lecturer-id", "lecturer", hash_password("lecturer-pass"), "A Lecturer", "lecturer@example.com", "Lecturer"),
        )
        self.api.connection.execute("INSERT INTO Lecturers VALUES (?, ?, ?)", ("LE01", "lecturer-id", "Computer Science"))
        self.api.connection.commit()

    def login(self, username, password):
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": password})

    def test_login_returns_role_and_rejects_invalid_credentials(self):
        status, response = self.login("student", "student-pass")
        self.assertEqual(status, 200)
        self.assertEqual(response["user"]["role"], "Student")
        self.assertEqual(self.login("student", "wrong")[0], 401)
        self.assertEqual(self.login("missing", "wrong")[0], 401)

    def test_all_roles_me_and_invalid_tokens(self):
        for username, role, password in (("student", "Student", "student-pass"), ("lecturer", "Lecturer", "lecturer-pass"), ("admin", "Admin", "admin-pass")):
            status, response = self.login(username, password)
            self.assertEqual(status, 200)
            self.assertEqual(response["user"]["role"], role)
            self.assertNotIn("password_hash", response)
            status, me = self.client.request("GET", "/api/auth/me", token=response["token"])
            self.assertEqual(status, 200)
            self.assertTrue(me["authenticated"])
            self.assertEqual(me["user"]["role"], role)
        self.assertEqual(self.client.request("GET", "/api/auth/me")[1], {"authenticated": False, "user": None})
        self.assertEqual(self.client.request("GET", "/api/auth/me", token="invalid")[1]["authenticated"], False)

    def test_inactive_session_expires(self):
        with patch("backend.api.time.monotonic", side_effect=(100.0, 100.0, 100.0, 100.0 + 30 * 60)):
            _, response = self.login("student", "student-pass")
            self.assertTrue(self.client.request("GET", "/api/auth/me", token=response["token"])[1]["authenticated"])
            self.assertFalse(self.client.request("GET", "/api/auth/me", token=response["token"])[1]["authenticated"])

    def test_only_admin_can_manage_users_and_password_is_hashed(self):
        _, student_login = self.login("student", "student-pass")
        _, lecturer_login = self.login("lecturer", "lecturer-pass")
        _, admin_login = self.login("admin", "admin-pass")
        self.assertEqual(self.client.request("GET", "/api/users", token=student_login["token"])[0], 403)
        self.assertEqual(self.client.request("GET", "/api/users", token=lecturer_login["token"])[0], 403)
        self.assertEqual(self.client.request("GET", "/api/users")[0], 401)
        status, created = self.client.request("POST", "/api/users", {
            "username": "new-user", "password": "new-pass", "full_name": "New User",
            "email": "new@example.com", "role": "Admin",
        }, admin_login["token"])
        self.assertEqual(status, 201)
        stored = self.api.connection.execute("SELECT password_hash FROM Users WHERE username = 'new-user'").fetchone()[0]
        self.assertNotEqual(stored, "new-pass")
        self.assertEqual(self.client.request("POST", "/api/users", {
            "username": "new-user", "password": "other", "full_name": "Other", "email": "other@example.com", "role": "Admin",
        }, admin_login["token"])[0], 409)
        self.assertEqual(self.client.request("PUT", f"/api/users/{created['user']['user_id']}", {"full_name": "Updated"}, admin_login["token"])[0], 200)
        self.assertEqual(self.client.request("DELETE", f"/api/users/{created['user']['user_id']}", token=admin_login["token"])[0], 200)

    def test_user_listing_never_exposes_password_hash(self):
        _, admin_login = self.login("admin", "admin-pass")
        status, response = self.client.request("GET", "/api/users", token=admin_login["token"])
        self.assertEqual(status, 200)
        self.assertTrue(response["users"])
        self.assertTrue(all("password_hash" not in user for user in response["users"]))

    def test_duplicate_email_and_foreign_keys_are_rejected(self):
        _, admin_login = self.login("admin", "admin-pass")
        status, _ = self.client.request("POST", "/api/users", {
            "username": "another-user", "password": "pass", "full_name": "Another",
            "email": "student@example.com", "role": "Admin",
        }, admin_login["token"])
        self.assertEqual(status, 409)
        with self.assertRaises(sqlite3.IntegrityError):
            self.api.connection.execute("INSERT INTO Students VALUES (?, ?, ?)", ("ST02", "missing-user", "C01"))

    def test_create_profiles_and_validate_requests(self):
        _, login = self.login("admin", "admin-pass")
        token = login["token"]
        student_data = {"username": "created-student", "password": "pass", "full_name": "Created Student", "email": "created-student@example.com", "role": "Student", "student_code": "ST02", "class_id": "C02"}
        lecturer_data = {"username": "created-lecturer", "password": "pass", "full_name": "Created Lecturer", "email": "created-lecturer@example.com", "role": "Lecturer", "lecturer_code": "LE02", "department": "Math"}
        for data, table, code in ((student_data, "Students", "ST02"), (lecturer_data, "Lecturers", "LE02")):
            status, response = self.client.request("POST", "/api/users", data, token)
            self.assertEqual(status, 201)
            self.assertIsNotNone(self.api.connection.execute(f"SELECT 1 FROM {table} WHERE user_id = ? AND {table[:-1].lower()}_code = ?", (response["user"]["user_id"], code)).fetchone())
        for data in ({"role": "Invalid"}, {"role": "Student"}, {"role": "Lecturer"}):
            self.assertEqual(self.client.request("POST", "/api/users", data, token)[0], 400)

    def test_role_transitions_replace_profiles_and_roll_back(self):
        _, login = self.login("admin", "admin-pass")
        token = login["token"]
        status, response = self.client.request("PUT", "/api/users/student-id", {"role": "Lecturer", "lecturer_code": "LE03", "department": "Physics"}, token)
        self.assertEqual(status, 200)
        self.assertIsNone(self.api.connection.execute("SELECT 1 FROM Students WHERE user_id = 'student-id'").fetchone())
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'student-id' AND lecturer_code = 'LE03'").fetchone())
        self.assertEqual(response["user"]["role"], "Lecturer")
        status, _ = self.client.request("PUT", "/api/users/lecturer-id", {"role": "Student", "student_code": "ST03", "class_id": "C03"}, token)
        self.assertEqual(status, 200)
        self.assertIsNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'lecturer-id'").fetchone())
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Students WHERE user_id = 'lecturer-id' AND student_code = 'ST03'").fetchone())
        status, new_admin = self.client.request("POST", "/api/users", {"username": "transition-admin", "password": "pass", "full_name": "Transition Admin", "email": "transition-admin@example.com", "role": "Admin"}, token)
        self.assertEqual(status, 201)
        transition_token = new_admin["user"]
        self.assertEqual(self.client.request("PUT", "/api/users/student-id", {"role": "Admin"}, token)[0], 200)
        self.assertIsNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'student-id'").fetchone())
        token = self.login("transition-admin", "pass")[1]["token"]
        self.assertEqual(self.client.request("PUT", "/api/users/admin-id", {"role": "Student", "student_code": "ST04", "class_id": "C04"}, token)[0], 200)
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Students WHERE user_id = 'admin-id'").fetchone())
        self.assertEqual(self.client.request("PUT", "/api/users/admin-id", {"role": "Lecturer", "lecturer_code": "LE04", "department": "History"}, token)[0], 200)
        self.assertIsNone(self.api.connection.execute("SELECT 1 FROM Students WHERE user_id = 'admin-id'").fetchone())
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'admin-id'").fetchone())
        status, _ = self.client.request("PUT", "/api/users/admin-id", {"role": "Student", "student_code": "ST03", "class_id": "duplicate"}, token)
        self.assertEqual(status, 409)
        self.assertEqual(self.api.connection.execute("SELECT role FROM Users WHERE user_id = 'admin-id'").fetchone()[0], "Lecturer")
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'admin-id' AND lecturer_code = 'LE04'").fetchone())

    def test_delete_profiles_and_preserve_attendance_references(self):
        _, login = self.login("admin", "admin-pass")
        token = login["token"]
        self.api.connection.execute("INSERT INTO ClassSessions VALUES ('session-1', 'Course', 'LE01', '2026-01-01', '2026-01-01', 'S01')")
        self.api.connection.execute("INSERT INTO AttendanceRecord VALUES ('record-1', 'ST01', 'session-1', '2026-01-01', 'Present')")
        self.api.connection.commit()
        self.assertEqual(self.client.request("DELETE", "/api/users/student-id", token=token)[0], 409)
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM AttendanceRecord WHERE record_id = 'record-1'").fetchone())
        self.assertEqual(self.client.request("DELETE", "/api/users/lecturer-id", token=token)[0], 409)
        self.assertIsNotNone(self.api.connection.execute("SELECT 1 FROM Lecturers WHERE user_id = 'lecturer-id'").fetchone())
        status, created_lecturer = self.client.request("POST", "/api/users", {"username": "deletable-lecturer", "password": "pass", "full_name": "Deletable Lecturer", "email": "deletable-lecturer@example.com", "role": "Lecturer", "lecturer_code": "LE05", "department": "Art"}, token)
        self.assertEqual(status, 201)
        self.assertEqual(self.client.request("DELETE", f"/api/users/{created_lecturer['user']['user_id']}", token=token)[0], 200)
        status, created = self.client.request("POST", "/api/users", {"username": "deletable", "password": "pass", "full_name": "Deletable", "email": "deletable@example.com", "role": "Student", "student_code": "ST05", "class_id": "C05"}, token)
        self.assertEqual(status, 201)
        self.assertEqual(self.client.request("DELETE", f"/api/users/{created['user']['user_id']}", token=token)[0], 200)
        self.assertIsNone(self.api.connection.execute("SELECT 1 FROM Students WHERE student_code = 'ST05'").fetchone())

    def test_attendance_session_flow_and_ownership(self):
        _, lecturer_login = self.login("lecturer", "lecturer-pass")
        _, student_login = self.login("student", "student-pass")
        now = datetime.now(timezone.utc)
        session_data = {
            "course_name": "Distributed Systems",
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(minutes=5)).isoformat(),
            "lecturer_code": "LE99",
        }
        self.assertEqual(self.client.request("POST", "/api/sessions", session_data)[0], 401)
        self.assertEqual(self.client.request("POST", "/api/sessions", session_data, student_login["token"])[0], 403)
        status, response = self.client.request("POST", "/api/sessions", session_data, lecturer_login["token"])
        self.assertEqual(status, 403)
        session_data["lecturer_code"] = "LE01"
        status, response = self.client.request("POST", "/api/sessions", session_data, lecturer_login["token"])
        self.assertEqual(status, 201)
        session = response["session"]
        self.assertTrue(session["session_id"])
        self.assertTrue(session["session_code"])
        self.assertEqual(self.client.request("POST", "/api/attendance", {"session_code": session["session_code"], "timestamp": "2000-01-01", "status": "Present"}, lecturer_login["token"])[0], 403)
        status, attendance = self.client.request("POST", "/api/attendance", {"session_code": session["session_code"], "timestamp": "2000-01-01"}, student_login["token"])
        self.assertEqual(status, 201)
        self.assertEqual(attendance["attendance"]["student_code"], "ST01")
        self.assertEqual(attendance["attendance"]["session_id"], session["session_id"])
        self.assertNotEqual(attendance["attendance"]["timestamp"], "2000-01-01")
        self.assertEqual(self.client.request("POST", "/api/attendance", {"session_code": session["session_code"]}, student_login["token"])[0], 409)
        status, report = self.client.request("GET", "/api/reports/attendance", token=lecturer_login["token"])
        self.assertEqual(status, 200)
        self.assertEqual(report["attendance"][0]["student_code"], "ST01")
        self.assertEqual(self.client.request("GET", "/api/attendance/history", token=student_login["token"])[1]["attendance"][0]["session_id"], session["session_id"])

    def test_attendance_database_duplicate_constraint_and_expired_session(self):
        now = datetime.now(timezone.utc)
        self.api.connection.execute("INSERT INTO ClassSessions VALUES (?, ?, ?, ?, ?, ?)", ("expired", "Old Course", "LE01", (now - timedelta(hours=2)).isoformat(), (now - timedelta(hours=1)).isoformat(), "EXPIRED"))
        self.api.connection.commit()
        _, student_login = self.login("student", "student-pass")
        self.assertEqual(self.client.request("POST", "/api/attendance", {"session_code": "EXPIRED"}, student_login["token"])[0], 400)
        with self.assertRaises(sqlite3.IntegrityError):
            self.api.connection.execute("INSERT INTO AttendanceRecord VALUES (?, ?, ?, ?, ?)", ("one", "ST01", "expired", now.isoformat(), "Present"))
            self.api.connection.execute("INSERT INTO AttendanceRecord VALUES (?, ?, ?, ?, ?)", ("two", "ST01", "expired", now.isoformat(), "Present"))


if __name__ == "__main__":
    unittest.main()