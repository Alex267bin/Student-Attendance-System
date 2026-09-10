import unittest
from backend.api import AttendanceAPI
from tests.test_api import APIClient

class TestAlexAuth(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)

    def login(self, username, password):
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": password})

    def test_admin_login_success(self):
        status, response = self.login("admin", "adminpass")
        self.assertEqual(status, 200)
        self.assertIn("token", response)

    def test_login_invalid_password(self):
        status, response = self.login("admin", "wrong-pass")
        self.assertEqual(status, 401)

    def test_create_user_by_admin(self):
        _, login_res = self.login("admin", "adminpass")
        token = login_res.get("token")
        user_data = {
            "username": "new_lecturer",
            "password": "pass123",
            "full_name": "New Lecturer",
            "email": "lecturer@test.com",
            "role": "Lecturer"
        }
        status, response = self.client.request("POST", "/api/users", user_data, token=token)
        self.assertEqual(status, 201)

    def test_create_user_forbidden_for_student(self):
        _, login_res = self.login("student", "studentpass")
        token = login_res.get("token")
        user_data = {
            "username": "unauthorized_user",
            "password": "pass123",
            "full_name": "Bad User",
            "email": "bad@test.com",
            "role": "Student"
        }
        status, response = self.client.request("POST", "/api/users", user_data, token=token)
        self.assertEqual(status, 403)

if __name__ == "__main__":
    unittest.main()
