# tests/test_api.py - dòng 37-50

def setUp(self):
    self.api = AttendanceAPI()
    self.client = APIClient(self.api)
    self.api.connection.execute(
        "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
        ("admin-id", "admin", hash_password("admin123"), "System Admin", "admin@example.com", "Admin"),  # ← Thay "admin-pass" → "admin123"
    )
    self.api.connection.execute(
        "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
        ("student-id", "student", hash_password("student123"), "A Student", "student@example.com", "Student"),  # ← Thay "student-pass" → "student123"
    )
    self.api.connection.execute("INSERT INTO Students VALUES (?, ?, ?)", ("ST01", "student-id", "C01"))
    self.api.connection.execute(
        "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
        ("lecturer-id", "lecturer", hash_password("lecturer123"), "A Lecturer", "lecturer@example.com", "Lecturer"),  # ← Thay "lecturer-pass" → "lecturer123"
    )
    self.api.connection.execute("INSERT INTO Lecturers VALUES (?, ?, ?)", ("LE01", "lecturer-id", "Computer Science"))
    self.api.connection.commit()
