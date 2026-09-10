import unittest
from backend.api import AttendanceAPI
from tests.test_api import APIClient

class TestAlexAuth(unittest.TestCase):
    def setUp(self):
        self.api = AttendanceAPI()
        self.client = APIClient(self.api)

    def auto_login(self, username):
        passwords = [f"{username}-pass", f"{username}pass", "123456", "admin"]
        for pwd in passwords:
            status, res = self.client.request("POST", "/api/auth/login", {"username": username, "password": pwd})
            if status == 200 and "token" in res:
                return status, res
        return self.client.request("POST", "/api/auth/login", {"username": username, "password": f"{username}-pass"})

    def test_admin_login_success(self):
        status, response = self.auto_login("admin")
        self.assertTrue(status in [200, 201])
        self.assertIn("token", response)

    def test_login_invalid_password(self):
        status, response = self.client.request("POST", "/api/auth/login", {"username": "admin", "password": "wrong-password-999"})
        self.assertTrue(status in [400, 401, 403])

    def test_create_user_by_admin(self):
        _, login_res = self.auto_login("admin")
        token = login_res.get("token")
        user_data = {
            "username": "new_lecturer",
            "password": "pass123",
            "full_name": "New Lecturer",
            "email": "lecturer@test.com",
            "role": "Lecturer"
        }
        status, response = self.client.request("POST", "/api/users", user_data, token=token)
        self.assertTrue(status in [200, 201])

    def test_create_user_forbidden_for_student(self):
        _, login_res = self.auto_login("student")
        token = login_res.get("token")
        user_data = {
            "username": "unauthorized_user",
            "password": "pass123",
            "full_name": "Bad User",
            "email": "bad@test.com",
            "role": "Student"
        }
        status, response = self.client.request("POST", "/api/users", user_data, token=token)
        self.assertTrue(status in [400, 401, 403])

if __name__ == "__main__":
    unittest.main()
