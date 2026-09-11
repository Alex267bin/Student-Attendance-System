import unittest
from datetime import datetime, timedelta, timezone
from backend.api import AttendanceAPI
from backend.database import connect, initialize
from tests.test_api import APIClient

class TestKhoiAttendance(unittest.TestCase):

    def setUp(self):
        self.conn = connect(":memory:")
        initialize(self.conn)
        self.api = AttendanceAPI(self.conn)
        self.client = APIClient(self.api)

    def tearDown(self):
        self.conn.close()

    def auto_login(self, username):
        passwords = [f"{username}123", f"{username}-pass", "123456"]
        for pwd in passwords:
            status, res = self.client.request("POST", "/api/auth/login", {"username": username, "password": pwd})
            if status == 200 and "token" in res:
                return status, res
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": f"{username}123"})

    def test_create_session_and_attendance_flow(self):
        _, lec_login = self.auto_login("lecturer")
        now = datetime.now(timezone.utc)
        
        session_data = {
            "course_name": "Software Architecture",
            "course_code": "SA101",
            "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        status, session_res = self.client.request("POST", "/api/sessions", session_data, token=lec_login.get("token"))
        self.assertTrue(status in [200, 201], f"Cannot create session: {status}")
        
        session_code = session_res.get("session_code")
        self.assertIsNotNone(session_code, "Session code is None")
        
        _, stu_login = self.auto_login("student")
        status, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login.get("token"))
        self.assertTrue(status in [200, 201], f"Attendance failed: {status}")

    def test_duplicate_attendance_rejected(self):
        _, lec_login = self.auto_login("lecturer")
        now = datetime.now(timezone.utc)
        session_data = {
            "course_name": "Database Testing",
            "course_code": "DB101",
            "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        }
        status_sec, session_res = self.client.request("POST", "/api/sessions", session_data, token=lec_login.get("token"))
        self.assertTrue(status_sec in [200, 201], "Setup session failed")
        
        session_code = session_res.get("session_code")
        self.assertIsNotNone(session_code)
        
        _, stu_login = self.auto_login("student")
        stu_token = stu_login.get("token")
        
        status1, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_token)
        self.assertTrue(status1 in [200, 201], f"First attendance failed with status {status1}")
        
        status2, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_token)
        self.assertTrue(status2 in [400, 409, 403], f"Duplicate not rejected, got {status2}")

    def test_attendance_expired_session_rejected(self):
        _, lec_login = self.auto_login("lecturer")
        now = datetime.now(timezone.utc)
        expired_session = {
            "course_name": "Expired Class",
            "course_code": "EX101",
            "start_time": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        }
        status_exp, session_res = self.client.request("POST", "/api/sessions", expired_session, token=lec_login.get("token"))
        
        if status_exp in [200, 201]:
            session_code = session_res.get("session_code")
            _, stu_login = self.auto_login("student")
            status, _ = self.client.request("POST", "/api/attendance", {"session_code": session_code}, token=stu_login.get("token"))
            self.assertTrue(status in [400, 404, 409, 403, 401], f"Expired session allowed attendance: {status}")

if __name__ == "__main__":
    unittest.main()
