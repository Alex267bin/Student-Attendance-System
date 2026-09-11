import json
import io
from backend.security import hash_password


class APIClient:
    def __init__(self, api):
        self.api = api
    
    def request(self, method, endpoint, data=None, token=None):
        if data is None:
            data = {}
        
        body = json.dumps(data).encode() if data else b'{}'
        
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": endpoint,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
            "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
            "QUERY_STRING": ""
        }
        
        response_data = {"status": None}
        
        def start_response(status, headers):
            response_data["status"] = int(status.split()[0])
        
        result = self.api(environ, start_response)
        
        body_bytes = b''.join(result)
        response_body = json.loads(body_bytes) if body_bytes else {}
        
        return response_data["status"], response_body


def setup_default_users(api):
    try:
        api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("admin-id", "admin", hash_password("admin123"), "System Admin", "admin@example.com", "Admin")
        )
        
        api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("student-id", "student", hash_password("student123"), "A Student", "student@example.com", "Student")
        )
        api.connection.execute(
            "INSERT INTO Students VALUES (?, ?, ?)",
            ("ST01", "student-id", "C01")
        )
        
        api.connection.execute(
            "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
            ("lecturer-id", "lecturer", hash_password("lecturer123"), "A Lecturer", "lecturer@example.com", "Lecturer")
        )
        api.connection.execute(
            "INSERT INTO Lecturers VALUES (?, ?, ?)",
            ("LE01", "lecturer-id", "Computer Science")
        )
        
        api.connection.commit()
    except:
        api.connection.rollback()
