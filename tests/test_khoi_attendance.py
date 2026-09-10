import unittest
from datetime import datetime, timedelta, timezone
from backend.api import AttendanceAPI
from tests.test_api import APIClient

class TestKhoiAttendance(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)

    def login(self, username, password):
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": password})

    def test_create_session_and_attendance_flow(self):
        _, lec_login = self.login("lecturer", "lecturer-pass")
        now = datetime.now(timezone.utc)
        session_data = {
            "course_name": "Software Architecture",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "lecturer_code": "LEC01"
        }
        status, session_res = self.client.request("POST", "/api/sessions", session_data, token=lec_login["token"])
        self.assertEqual(status, 201)
        session_code = session_res["session_code"]

        _, stu_login = self.login("student", "student-pass")
        status, att_res = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login["token"])
        self.assertEqual(status, 201)

    def test_duplicate_attendance_rejected(self):
        _, lec_login = self.login("lecturer", "lecturer-pass")
        now = datetime.now(timezone.utc)
        session_data = {
            "course_name": "Database Testing",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "lecturer_code": "LEC01"
        }
        _, session_res = self.client.request("POST", "/api/sessions", session_data, token=lec_login["token"])
        session_code = session_res["session_code"]

        _, stu_login = self.login("student", "student-pass")
        self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login["token"])
        status, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login["token"])
        self.assertEqual(status, 409)

    def test_attendance_expired_session_rejected(self):
        _, lec_login = self.login("lecturer", "lecturer-pass")
        now = datetime.now(timezone.utc)
        expired_session = {
            "course_name": "Expired Class",
            "start_time": (now - timedelta(hours=3)).isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
            "lecturer_code": "LEC01"
        }
        _, session_res = self.client.request("POST", "/api/sessions", expired_session, token=lec_login["token"])
        session_code = session_res["session_code"]

        _, stu_login = self.login("student", "student-pass")
        status, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login["token"])
        self.assertEqual(status, 400)

if __name__ == "__main__":
    unittest.main()
