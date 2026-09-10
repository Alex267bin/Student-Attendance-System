import unittest
from datetime import datetime, timedelta, timezone
from backend.api import AttendanceAPI
from tests.test_api import APIClient

class TestNhanQAEdgeCases(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)

    def auto_login(self, username):
        passwords = [f"{username}-pass", f"{username}pass", "123456"]
        for pwd in passwords:
            status, res = self.client.request("POST", "/api/auth/login", {"username": username, "password": pwd})
            if status == 200 and "token" in res:
                return status, res
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": f"{username}-pass"})

    def test_student_cannot_access_reports(self):
        _, stu_login = self.auto_login("student")
        status, _ = self.client.request("GET", "/api/reports/attendance", token=stu_login.get("token"))
        self.assertEqual(status, 403)

    def test_attendance_with_invalid_session_code(self):
        _, stu_login = self.auto_login("student")
        status, _ = self.client.request("POST", "/api/attendance", {"session_code": "INVALID_CODE_999"}, token=stu_login.get("token"))
        self.assertEqual(status, 404)

    def test_create_session_with_invalid_time_range(self):
        _, lec_login = self.auto_login("lecturer")
        now = datetime.now(timezone.utc)
        invalid_session = {
            "course_name": "Time Travel Class",
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
            "lecturer_code": "LEC01"
        }
        status, _ = self.client.request("POST", "/api/sessions", invalid_session, token=lec_login.get("token"))
        self.assertEqual(status, 400)

    def test_create_user_missing_required_payload(self):
        _, admin_login = self.auto_login("admin")
        incomplete_data = {
            "username": "missing_fields_user",
            "full_name": "Incomplete User"
        }
        status, _ = self.client.request("POST", "/api/users", incomplete_data, token=admin_login.get("token"))
        self.assertEqual(status, 400)

if __name__ == "__main__":
    unittest.main()
