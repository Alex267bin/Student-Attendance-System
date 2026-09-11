import unittest
from backend.api import AttendanceAPI
from backend.database import connect, initialize
from tests.test_api import APIClient

class TestAlexAuth(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        initialize(self.conn)
        self.api = AttendanceAPI(self.conn)
        self.client = APIClient(self.api)

    def tearDown(self):
        self.conn.close()

    def test_admin_login_success(self):
        status, res = self.client.request("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
        self.assertTrue(status in [200, 201])
        self.assertIn("token", res)

    def test_create_user_by_admin(self):
        _, login_res = self.client.request("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
        token = login_res.get("token")
        
        new_user = {
            "username": "new_student_01",
            "password": "password123",
            "role": "student",
            "full_name": "New Student"
        }
        status, _ = self.client.request("POST", "/api/users", new_user, token=token)
        self.assertTrue(status in [200, 201])

    def test_create_user_forbidden_for_student(self):
        _, login_res = self.client.request("POST", "/api/auth/login", {"username": "student", "password": "student123"})
        token = login_res.get("token")
        
        new_user = {
            "username": "hacker",
            "password": "123",
            "role": "admin",
            "full_name": "Hacker"
        }
        status, _ = self.client.request("POST", "/api/users", new_user, token=token)
        self.assertIn(status, [403, 401])

    def test_login_invalid_password(self):
        status, _ = self.client.request("POST", "/api/auth/login", {"username": "admin", "password": "wrongpassword"})
        self.assertIn(status, [401, 400])

if __name__ == "__main__":
    unittest.main()
