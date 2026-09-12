import json
import os
import secrets
import sqlite3
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import parse_qs

from .database import connect, initialize
from .security import hash_password, verify_password


ROLES = {"Student", "Lecturer", "Admin"}
SESSION_TIMEOUT = 30 * 60


class AttendanceAPI:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = connect(database)
        initialize(self.connection)
        self.sessions: dict[str, tuple[str, float]] = {}

    def _user(self, user_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT user_id, username, full_name, email, role FROM Users WHERE user_id = ?", (user_id,)).fetchone()

    @staticmethod
    def _public_user(user: sqlite3.Row) -> dict[str, str]:
        return {key: user[key] for key in ("user_id", "username", "full_name", "email", "role")}

    def _session_user(self, environ: dict) -> sqlite3.Row | None:
        header = environ.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header[7:].strip()
        session = self.sessions.get(token)
        if session is None:
            return None
        user_id, last_used = session
        if time.monotonic() - last_used >= SESSION_TIMEOUT:
            self.sessions.pop(token, None)
            return None
        self.sessions[token] = (user_id, time.monotonic())
        return self._user(user_id)

    def _json(self, start_response: Callable, status: str, payload: dict, headers: list[tuple[str, str]] | None = None):
        body = json.dumps(payload).encode()
        response_headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body))), ("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "Authorization, Content-Type"), ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")]
        response_headers.extend(headers or [])
        start_response(status, response_headers)
        return [body]

    def _body(self, environ: dict) -> dict:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            value = json.loads(environ["wsgi.input"].read(length) or b"{}")
            return value if isinstance(value, dict) else {}
        except (ValueError, TypeError, json.JSONDecodeError, KeyError):
            return {}

    def __call__(self, environ: dict, start_response: Callable):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "")
        if method == "OPTIONS":
            return self._json(start_response, "204 No Content", {})
        if method == "POST" and path == "/api/auth/register":
            return self.register(self._body(environ), start_response)
        if method == "POST" and path == "/api/auth/login":
            return self.login(self._body(environ), start_response)
        user = self._session_user(environ)
        if method == "GET" and path == "/api/auth/me":
            return self._json(start_response, "200 OK", {"authenticated": bool(user), "user": self._public_user(user) if user else None})
        if path == "/api/users" or path.startswith("/api/users/"):
            if user is None:
                return self._json(start_response, "401 Unauthorized", {"error": "Authentication required"})
            if user["role"] != "Admin":
                return self._json(start_response, "403 Forbidden", {"error": "Admin role required"})
            return self.users(method, path, self._body(environ), start_response)
        if path == "/api/sessions" or path.startswith("/api/sessions/"):
            return self.sessions_api(method, self._body(environ), user, start_response)
        if path == "/api/attendance" or path == "/api/attendance/history":
            return self.attendance_api(method, path, self._body(environ), user, start_response)
        if path == "/api/reports/attendance":
            return self.attendance_report(environ, user, start_response)
        return self._json(start_response, "404 Not Found", {"error": "Not found"})

    def _require_role(self, user: sqlite3.Row | None, role: str, start_response: Callable):
        if user is None:
            return self._json(start_response, "401 Unauthorized", {"error": "Authentication required"})
        if user["role"] != role:
            return self._json(start_response, "403 Forbidden", {"error": f"{role} role required"})
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _session_json(row: sqlite3.Row) -> dict[str, str]:
        return {key: row[key] for key in ("session_id", "course_name", "lecturer_code", "start_time", "end_time", "session_code")}

    def sessions_api(self, method: str, data: dict, user: sqlite3.Row | None, start_response: Callable):
        denied = self._require_role(user, "Lecturer", start_response)
        if denied:
            return denied
        lecturer = self.connection.execute("SELECT lecturer_code FROM Lecturers WHERE user_id = ?", (user["user_id"],)).fetchone()
        if lecturer is None:
            return self._json(start_response, "403 Forbidden", {"error": "Lecturer profile required"})
        if method == "POST":
            course_name = data.get("course_name")
            start_time = self._parse_datetime(data.get("start_time"))
            end_time = self._parse_datetime(data.get("end_time"))
            if not isinstance(course_name, str) or not course_name.strip() or start_time is None or end_time is None or end_time <= start_time:
                return self._json(start_response, "400 Bad Request", {"error": "course_name, valid start_time, and end_time are required; end_time must be later"})
            if data.get("lecturer_code") not in (None, lecturer["lecturer_code"]):
                return self._json(start_response, "403 Forbidden", {"error": "Cannot create a session for another lecturer"})
            session_id = str(uuid.uuid4())
            session_code = secrets.token_urlsafe(6).replace("-", "A").replace("_", "B")[:10]
            try:
                self.connection.execute("INSERT INTO ClassSessions VALUES (?, ?, ?, ?, ?, ?)", (session_id, course_name.strip(), lecturer["lecturer_code"], start_time.isoformat(), end_time.isoformat(), session_code))
                self.connection.commit()
            except sqlite3.IntegrityError:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": "Session could not be created"})
            row = self.connection.execute("SELECT * FROM ClassSessions WHERE session_id = ?", (session_id,)).fetchone()
            return self._json(start_response, "201 Created", {"session": self._session_json(row)})
        if method == "GET":
            rows = self.connection.execute("SELECT * FROM ClassSessions WHERE lecturer_code = ? ORDER BY start_time", (lecturer["lecturer_code"],)).fetchall()
            return self._json(start_response, "200 OK", {"sessions": [self._session_json(row) for row in rows]})
        return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})

    def attendance_api(self, method: str, path: str, data: dict, user: sqlite3.Row | None, start_response: Callable):
        if path == "/api/attendance/history":
            denied = self._require_role(user, "Student", start_response)
            if denied:
                return denied
            if method != "GET":
                return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
            student = self.connection.execute("SELECT student_code FROM Students WHERE user_id = ?", (user["user_id"],)).fetchone()
            if student is None:
                return self._json(start_response, "403 Forbidden", {"error": "Student profile required"})
            rows = self.connection.execute("SELECT a.record_id, a.student_code, a.session_id, s.course_name, s.lecturer_code, a.timestamp, a.status FROM AttendanceRecord a JOIN ClassSessions s ON s.session_id = a.session_id WHERE a.student_code = ? ORDER BY a.timestamp DESC", (student["student_code"],)).fetchall()
            return self._json(start_response, "200 OK", {"attendance": [dict(row) for row in rows]})
        denied = self._require_role(user, "Student", start_response)
        if denied:
            return denied
        if method != "POST":
            return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
        student = self.connection.execute("SELECT student_code FROM Students WHERE user_id = ?", (user["user_id"],)).fetchone()
        if student is None:
            return self._json(start_response, "403 Forbidden", {"error": "Student profile required"})
        session_code = data.get("session_code")
        session = self.connection.execute("SELECT * FROM ClassSessions WHERE session_code = ?", (session_code,)).fetchone() if isinstance(session_code, str) else None
        now = self._now()
        if session is None:
            return self._json(start_response, "404 Not Found", {"error": "Session not found"})
        start_time = self._parse_datetime(session["start_time"])
        end_time = self._parse_datetime(session["end_time"])
        if start_time is None or end_time is None or not (start_time <= now <= end_time):
            return self._json(start_response, "400 Bad Request", {"error": "Session is not active"})
        if self.connection.execute("SELECT 1 FROM AttendanceRecord WHERE student_code = ? AND session_id = ?", (student["student_code"], session["session_id"])).fetchone():
            return self._json(start_response, "409 Conflict", {"error": "Attendance already submitted"})
        status = data.get("status", "Present")
        if status not in {"Present", "Late", "Absent"}:
            return self._json(start_response, "400 Bad Request", {"error": "status must be Present, Late, or Absent"})
        record_id = str(uuid.uuid4())
        try:
            self.connection.execute("INSERT INTO AttendanceRecord VALUES (?, ?, ?, ?, ?)", (record_id, student["student_code"], session["session_id"], now.isoformat(), status))
            self.connection.commit()
        except sqlite3.IntegrityError:
            self.connection.rollback()
            return self._json(start_response, "409 Conflict", {"error": "Attendance already submitted"})
        return self._json(start_response, "201 Created", {"attendance": {"record_id": record_id, "student_code": student["student_code"], "session_id": session["session_id"], "timestamp": now.isoformat(), "status": status}})

    def attendance_report(self, environ: dict, user: sqlite3.Row | None, start_response: Callable):
        denied = self._require_role(user, "Lecturer", start_response)
        if denied:
            return denied
        lecturer = self.connection.execute("SELECT lecturer_code FROM Lecturers WHERE user_id = ?", (user["user_id"],)).fetchone()
        if lecturer is None:
            return self._json(start_response, "403 Forbidden", {"error": "Lecturer profile required"})
        query = parse_qs(environ.get("QUERY_STRING", ""))
        session_id = query.get("session_id", [None])[0]
        sql = "SELECT s.session_id, s.course_name, s.lecturer_code, a.student_code, a.timestamp, a.status FROM ClassSessions s JOIN AttendanceRecord a ON a.session_id = s.session_id WHERE s.lecturer_code = ?"
        parameters: tuple[str, ...] = (lecturer["lecturer_code"],)
        if session_id:
            sql += " AND s.session_id = ?"
            parameters += (session_id,)
        sql += " ORDER BY a.timestamp"
        rows = self.connection.execute(sql, parameters).fetchall()
        return self._json(start_response, "200 OK", {"attendance": [dict(row) for row in rows]})

    def login(self, data: dict, start_response: Callable):
        username, password = data.get("username"), data.get("password")
        user = self.connection.execute("SELECT * FROM Users WHERE username = ?", (username,)).fetchone() if isinstance(username, str) else None
        if user is None or not isinstance(password, str) or not verify_password(password, user["password_hash"]):
            return self._json(start_response, "401 Unauthorized", {"error": "Invalid username or password"})
        token = secrets.token_urlsafe(32)
        self.sessions[token] = (user["user_id"], time.monotonic())
        public = self._public_user(user)
        return self._json(start_response, "200 OK", {"authenticated": True, "token": token, "user": public})

    def register(self, data: dict, start_response: Callable):
        required = ("name", "email", "username", "password")
        if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
            return self._json(start_response, "400 Bad Request", {"error": "name, email, username, and password are required"})
        username = data["username"].strip()
        if len(username) > 20:
            return self._json(start_response, "400 Bad Request", {"error": "username must be at most 20 characters"})
        user_id = str(uuid.uuid4())
        try:
            self.connection.execute(
                "INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, hash_password(data["password"]), data["name"].strip(), data["email"].strip(), "Student"),
            )
            self._insert_profile((username, "UNASSIGNED"), user_id, "Student")
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            return self._json(start_response, "409 Conflict", {"error": self._constraint_message(error)})
        return self._json(start_response, "201 Created", {"user": self._public_user(self._user(user_id))})

    def users(self, method: str, path: str, data: dict, start_response: Callable):
        user_id = path.removeprefix("/api/users/").strip("/") if path != "/api/users" else ""
        if method == "GET" and not user_id:
            rows = self.connection.execute("SELECT user_id, username, full_name, email, role FROM Users ORDER BY username").fetchall()
            return self._json(start_response, "200 OK", {"users": [self._public_user(row) for row in rows]})
        if method == "POST" and not user_id:
            required = ("username", "password", "full_name", "email", "role")
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required) or data["role"] not in ROLES:
                return self._json(start_response, "400 Bad Request", {"error": "username, password, full_name, email, and a valid role are required"})
            try:
                profile = self._profile_values(data, data["role"])
            except ValueError as error:
                return self._json(start_response, "400 Bad Request", {"error": str(error)})
            user_id = str(uuid.uuid4())
            try:
                self.connection.execute("INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)", (user_id, data["username"], hash_password(data["password"]), data["full_name"], data["email"], data["role"]))
                self._insert_profile(profile, user_id, data["role"])
                self.connection.commit()
            except sqlite3.IntegrityError as error:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": self._constraint_message(error)})
            return self._json(start_response, "201 Created", {"user": self._public_user(self._user(user_id))})
        if not user_id:
            return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
        if method == "DELETE":
            if self._user(user_id) is None:
                return self._json(start_response, "404 Not Found", {"error": "User not found"})
            try:
                self.connection.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
                self.connection.execute("DELETE FROM Lecturers WHERE user_id = ?", (user_id,))
                self.connection.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
                self.connection.commit()
            except sqlite3.IntegrityError:
                return self._json(start_response, "409 Conflict", {"error": "User is referenced by another record"})
            return self._json(start_response, "200 OK", {"deleted": True})
        if method == "PUT":
            existing = self._user(user_id)
            if existing is None:
                return self._json(start_response, "404 Not Found", {"error": "User not found"})
            fields = {key: data[key] for key in ("username", "full_name", "email", "role") if key in data}
            if any(not isinstance(value, str) or not value.strip() for value in fields.values()):
                return self._json(start_response, "400 Bad Request", {"error": "updated fields must be non-empty strings"})
            if "role" in fields and fields["role"] not in ROLES:
                return self._json(start_response, "400 Bad Request", {"error": "role must be Student, Lecturer, or Admin"})
            if "password" in data and (not isinstance(data["password"], str) or not data["password"].strip()):
                return self._json(start_response, "400 Bad Request", {"error": "password must be a non-empty string"})
            if not fields and "password" not in data:
                return self._json(start_response, "400 Bad Request", {"error": "No changes supplied"})
            target_role = fields.get("role", existing["role"])
            role_changed = target_role != existing["role"]
            try:
                profile = self._profile_values(data, target_role) if role_changed else None
            except ValueError as error:
                return self._json(start_response, "400 Bad Request", {"error": str(error)})
            try:
                if role_changed:
                    self.connection.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
                    self.connection.execute("DELETE FROM Lecturers WHERE user_id = ?", (user_id,))
                    self._insert_profile(profile, user_id, target_role)
                if fields:
                    assignments = ", ".join(f"{key} = ?" for key in fields)
                    self.connection.execute(f"UPDATE Users SET {assignments} WHERE user_id = ?", (*fields.values(), user_id))
                if "password" in data:
                    self.connection.execute("UPDATE Users SET password_hash = ? WHERE user_id = ?", (hash_password(data["password"]), user_id))
                self.connection.commit()
            except sqlite3.IntegrityError as error:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": self._constraint_message(error)})
            return self._json(start_response, "200 OK", {"user": self._public_user(self._user(user_id))})
        return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})

    @staticmethod
    def _profile_values(data: dict, role: str) -> tuple[str, ...]:
        if role == "Student":
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in ("student_code", "class_id")):
                raise ValueError("student_code and class_id are required for Student")
            return data["student_code"], data["class_id"]
        if role == "Lecturer":
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in ("lecturer_code", "department")):
                raise ValueError("lecturer_code and department are required for Lecturer")
            return data["lecturer_code"], data["department"]
        return ()

    def _insert_profile(self, profile: tuple[str, ...], user_id: str, role: str) -> None:
        if role == "Student":
            self.connection.execute("INSERT INTO Students VALUES (?, ?, ?)", (profile[0], user_id, profile[1]))
        elif role == "Lecturer":
            self.connection.execute("INSERT INTO Lecturers VALUES (?, ?, ?)", (profile[0], user_id, profile[1]))

    @staticmethod
    def _constraint_message(error: Exception) -> str:
        message = str(error)
        if "username" in message:
            return "username must be unique"
        if "email" in message:
            return "email must be unique"
        return message or "Request violates a database constraint"


def create_app(database: str = ":memory:") -> AttendanceAPI:
    return AttendanceAPI(database)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    database_path = os.environ.get("DATABASE_PATH", "attendance.db")
    with make_server("0.0.0.0", 8000, create_app(database_path)) as server:
        print("Attendance API listening on http://127.0.0.1:8000")
        server.serve_forever()
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import parse_qs

from .database import connect, initialize
from .security import hash_password, verify_password


ROLES = {"Student", "Lecturer", "Admin"}
SESSION_TIMEOUT = 30 * 60


class AttendanceAPI:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = connect(database)
        initialize(self.connection)
        self.sessions: dict[str, tuple[str, float]] = {}

    def _user(self, user_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT user_id, username, full_name, email, role FROM Users WHERE user_id = ?", (user_id,)).fetchone()

    @staticmethod
    def _public_user(user: sqlite3.Row) -> dict[str, str]:
        return {key: user[key] for key in ("user_id", "username", "full_name", "email", "role")}

    def _session_user(self, environ: dict) -> sqlite3.Row | None:
        header = environ.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header[7:].strip()
        session = self.sessions.get(token)
        if session is None:
            return None
        user_id, last_used = session
        if time.monotonic() - last_used >= SESSION_TIMEOUT:
            self.sessions.pop(token, None)
            return None
        self.sessions[token] = (user_id, time.monotonic())
        return self._user(user_id)

    def _json(self, start_response: Callable, status: str, payload: dict, headers: list[tuple[str, str]] | None = None):
        body = json.dumps(payload).encode()
        response_headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body))), ("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "Authorization, Content-Type"), ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")]
        response_headers.extend(headers or [])
        start_response(status, response_headers)
        return [body]

    def _body(self, environ: dict) -> dict:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            value = json.loads(environ["wsgi.input"].read(length) or b"{}")
            return value if isinstance(value, dict) else {}
        except (ValueError, TypeError, json.JSONDecodeError, KeyError):
            return {}

    def __call__(self, environ: dict, start_response: Callable):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "")
        if method == "OPTIONS":
            return self._json(start_response, "204 No Content", {})
        if method == "POST" and path == "/api/auth/login":
            return self.login(self._body(environ), start_response)
        user = self._session_user(environ)
        if method == "GET" and path == "/api/auth/me":
            return self._json(start_response, "200 OK", {"authenticated": bool(user), "user": self._public_user(user) if user else None})
        if path == "/api/users" or path.startswith("/api/users/"):
            if user is None:
                return self._json(start_response, "401 Unauthorized", {"error": "Authentication required"})
            if user["role"] != "Admin":
                return self._json(start_response, "403 Forbidden", {"error": "Admin role required"})
            return self.users(method, path, self._body(environ), start_response)
        if path == "/api/sessions" or path.startswith("/api/sessions/"):
            return self.sessions_api(method, self._body(environ), user, start_response)
        if path == "/api/attendance" or path == "/api/attendance/history":
            return self.attendance_api(method, path, self._body(environ), user, start_response)
        if path == "/api/reports/attendance":
            return self.attendance_report(environ, user, start_response)
        return self._json(start_response, "404 Not Found", {"error": "Not found"})

    def _require_role(self, user: sqlite3.Row | None, role: str, start_response: Callable):
        if user is None:
            return self._json(start_response, "401 Unauthorized", {"error": "Authentication required"})
        if user["role"] != role:
            return self._json(start_response, "403 Forbidden", {"error": f"{role} role required"})
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _session_json(row: sqlite3.Row) -> dict[str, str]:
        return {key: row[key] for key in ("session_id", "course_name", "lecturer_code", "start_time", "end_time", "session_code")}

    def sessions_api(self, method: str, data: dict, user: sqlite3.Row | None, start_response: Callable):
        denied = self._require_role(user, "Lecturer", start_response)
        if denied:
            return denied
        lecturer = self.connection.execute("SELECT lecturer_code FROM Lecturers WHERE user_id = ?", (user["user_id"],)).fetchone()
        if lecturer is None:
            return self._json(start_response, "403 Forbidden", {"error": "Lecturer profile required"})
        if method == "POST":
            course_name = data.get("course_name")
            start_time = self._parse_datetime(data.get("start_time"))
            end_time = self._parse_datetime(data.get("end_time"))
            if not isinstance(course_name, str) or not course_name.strip() or start_time is None or end_time is None or end_time <= start_time:
                return self._json(start_response, "400 Bad Request", {"error": "course_name, valid start_time, and end_time are required; end_time must be later"})
            if data.get("lecturer_code") not in (None, lecturer["lecturer_code"]):
                return self._json(start_response, "403 Forbidden", {"error": "Cannot create a session for another lecturer"})
            session_id = str(uuid.uuid4())
            session_code = secrets.token_urlsafe(6).replace("-", "A").replace("_", "B")[:10]
            try:
                self.connection.execute("INSERT INTO ClassSessions VALUES (?, ?, ?, ?, ?, ?)", (session_id, course_name.strip(), lecturer["lecturer_code"], start_time.isoformat(), end_time.isoformat(), session_code))
                self.connection.commit()
            except sqlite3.IntegrityError:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": "Session could not be created"})
            row = self.connection.execute("SELECT * FROM ClassSessions WHERE session_id = ?", (session_id,)).fetchone()
            return self._json(start_response, "201 Created", {"session": self._session_json(row)})
        if method == "GET":
            rows = self.connection.execute("SELECT * FROM ClassSessions WHERE lecturer_code = ? ORDER BY start_time", (lecturer["lecturer_code"],)).fetchall()
            return self._json(start_response, "200 OK", {"sessions": [self._session_json(row) for row in rows]})
        return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})

    def attendance_api(self, method: str, path: str, data: dict, user: sqlite3.Row | None, start_response: Callable):
        if path == "/api/attendance/history":
            denied = self._require_role(user, "Student", start_response)
            if denied:
                return denied
            if method != "GET":
                return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
            student = self.connection.execute("SELECT student_code FROM Students WHERE user_id = ?", (user["user_id"],)).fetchone()
            if student is None:
                return self._json(start_response, "403 Forbidden", {"error": "Student profile required"})
            rows = self.connection.execute("SELECT a.record_id, a.student_code, a.session_id, s.course_name, s.lecturer_code, a.timestamp, a.status FROM AttendanceRecord a JOIN ClassSessions s ON s.session_id = a.session_id WHERE a.student_code = ? ORDER BY a.timestamp DESC", (student["student_code"],)).fetchall()
            return self._json(start_response, "200 OK", {"attendance": [dict(row) for row in rows]})
        denied = self._require_role(user, "Student", start_response)
        if denied:
            return denied
        if method != "POST":
            return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
        student = self.connection.execute("SELECT student_code FROM Students WHERE user_id = ?", (user["user_id"],)).fetchone()
        if student is None:
            return self._json(start_response, "403 Forbidden", {"error": "Student profile required"})
        session_code = data.get("session_code")
        session = self.connection.execute("SELECT * FROM ClassSessions WHERE session_code = ?", (session_code,)).fetchone() if isinstance(session_code, str) else None
        now = self._now()
        if session is None:
            return self._json(start_response, "404 Not Found", {"error": "Session not found"})
        start_time = self._parse_datetime(session["start_time"])
        end_time = self._parse_datetime(session["end_time"])
        if start_time is None or end_time is None or not (start_time <= now <= end_time):
            return self._json(start_response, "400 Bad Request", {"error": "Session is not active"})
        if self.connection.execute("SELECT 1 FROM AttendanceRecord WHERE student_code = ? AND session_id = ?", (student["student_code"], session["session_id"])).fetchone():
            return self._json(start_response, "409 Conflict", {"error": "Attendance already submitted"})
        status = data.get("status", "Present")
        if status not in {"Present", "Late", "Absent"}:
            return self._json(start_response, "400 Bad Request", {"error": "status must be Present, Late, or Absent"})
        record_id = str(uuid.uuid4())
        try:
            self.connection.execute("INSERT INTO AttendanceRecord VALUES (?, ?, ?, ?, ?)", (record_id, student["student_code"], session["session_id"], now.isoformat(), status))
            self.connection.commit()
        except sqlite3.IntegrityError:
            self.connection.rollback()
            return self._json(start_response, "409 Conflict", {"error": "Attendance already submitted"})
        return self._json(start_response, "201 Created", {"attendance": {"record_id": record_id, "student_code": student["student_code"], "session_id": session["session_id"], "timestamp": now.isoformat(), "status": status}})

    def attendance_report(self, environ: dict, user: sqlite3.Row | None, start_response: Callable):
        denied = self._require_role(user, "Lecturer", start_response)
        if denied:
            return denied
        lecturer = self.connection.execute("SELECT lecturer_code FROM Lecturers WHERE user_id = ?", (user["user_id"],)).fetchone()
        if lecturer is None:
            return self._json(start_response, "403 Forbidden", {"error": "Lecturer profile required"})
        query = parse_qs(environ.get("QUERY_STRING", ""))
        session_id = query.get("session_id", [None])[0]
        sql = "SELECT s.session_id, s.course_name, s.lecturer_code, a.student_code, a.timestamp, a.status FROM ClassSessions s JOIN AttendanceRecord a ON a.session_id = s.session_id WHERE s.lecturer_code = ?"
        parameters: tuple[str, ...] = (lecturer["lecturer_code"],)
        if session_id:
            sql += " AND s.session_id = ?"
            parameters += (session_id,)
        sql += " ORDER BY a.timestamp"
        rows = self.connection.execute(sql, parameters).fetchall()
        return self._json(start_response, "200 OK", {"attendance": [dict(row) for row in rows]})

    def login(self, data: dict, start_response: Callable):
        username, password = data.get("username"), data.get("password")
        user = self.connection.execute("SELECT * FROM Users WHERE username = ?", (username,)).fetchone() if isinstance(username, str) else None
        if user is None or not isinstance(password, str) or not verify_password(password, user["password_hash"]):
            return self._json(start_response, "401 Unauthorized", {"error": "Invalid username or password"})
        token = secrets.token_urlsafe(32)
        self.sessions[token] = (user["user_id"], time.monotonic())
        public = self._public_user(user)
        return self._json(start_response, "200 OK", {"authenticated": True, "token": token, "user": public})

    def users(self, method: str, path: str, data: dict, start_response: Callable):
        user_id = path.removeprefix("/api/users/").strip("/") if path != "/api/users" else ""
        if method == "GET" and not user_id:
            rows = self.connection.execute("SELECT user_id, username, full_name, email, role FROM Users ORDER BY username").fetchall()
            return self._json(start_response, "200 OK", {"users": [self._public_user(row) for row in rows]})
        if method == "POST" and not user_id:
            required = ("username", "password", "full_name", "email", "role")
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required) or data["role"] not in ROLES:
                return self._json(start_response, "400 Bad Request", {"error": "username, password, full_name, email, and a valid role are required"})
            try:
                profile = self._profile_values(data, data["role"])
            except ValueError as error:
                return self._json(start_response, "400 Bad Request", {"error": str(error)})
            user_id = str(uuid.uuid4())
            try:
                self.connection.execute("INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?)", (user_id, data["username"], hash_password(data["password"]), data["full_name"], data["email"], data["role"]))
                self._insert_profile(profile, user_id, data["role"])
                self.connection.commit()
            except sqlite3.IntegrityError as error:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": self._constraint_message(error)})
            return self._json(start_response, "201 Created", {"user": self._public_user(self._user(user_id))})
        if not user_id:
            return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})
        if method == "DELETE":
            if self._user(user_id) is None:
                return self._json(start_response, "404 Not Found", {"error": "User not found"})
            try:
                self.connection.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
                self.connection.execute("DELETE FROM Lecturers WHERE user_id = ?", (user_id,))
                self.connection.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
                self.connection.commit()
            except sqlite3.IntegrityError:
                return self._json(start_response, "409 Conflict", {"error": "User is referenced by another record"})
            return self._json(start_response, "200 OK", {"deleted": True})
        if method == "PUT":
            existing = self._user(user_id)
            if existing is None:
                return self._json(start_response, "404 Not Found", {"error": "User not found"})
            fields = {key: data[key] for key in ("username", "full_name", "email", "role") if key in data}
            if any(not isinstance(value, str) or not value.strip() for value in fields.values()):
                return self._json(start_response, "400 Bad Request", {"error": "updated fields must be non-empty strings"})
            if "role" in fields and fields["role"] not in ROLES:
                return self._json(start_response, "400 Bad Request", {"error": "role must be Student, Lecturer, or Admin"})
            if "password" in data and (not isinstance(data["password"], str) or not data["password"].strip()):
                return self._json(start_response, "400 Bad Request", {"error": "password must be a non-empty string"})
            if not fields and "password" not in data:
                return self._json(start_response, "400 Bad Request", {"error": "No changes supplied"})
            target_role = fields.get("role", existing["role"])
            role_changed = target_role != existing["role"]
            try:
                profile = self._profile_values(data, target_role) if role_changed else None
            except ValueError as error:
                return self._json(start_response, "400 Bad Request", {"error": str(error)})
            try:
                if role_changed:
                    self.connection.execute("DELETE FROM Students WHERE user_id = ?", (user_id,))
                    self.connection.execute("DELETE FROM Lecturers WHERE user_id = ?", (user_id,))
                    self._insert_profile(profile, user_id, target_role)
                if fields:
                    assignments = ", ".join(f"{key} = ?" for key in fields)
                    self.connection.execute(f"UPDATE Users SET {assignments} WHERE user_id = ?", (*fields.values(), user_id))
                if "password" in data:
                    self.connection.execute("UPDATE Users SET password_hash = ? WHERE user_id = ?", (hash_password(data["password"]), user_id))
                self.connection.commit()
            except sqlite3.IntegrityError as error:
                self.connection.rollback()
                return self._json(start_response, "409 Conflict", {"error": self._constraint_message(error)})
            return self._json(start_response, "200 OK", {"user": self._public_user(self._user(user_id))})
        return self._json(start_response, "405 Method Not Allowed", {"error": "Method not allowed"})

    @staticmethod
    def _profile_values(data: dict, role: str) -> tuple[str, ...]:
        if role == "Student":
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in ("student_code", "class_id")):
                raise ValueError("student_code and class_id are required for Student")
            return data["student_code"], data["class_id"]
        if role == "Lecturer":
            if any(not isinstance(data.get(field), str) or not data[field].strip() for field in ("lecturer_code", "department")):
                raise ValueError("lecturer_code and department are required for Lecturer")
            return data["lecturer_code"], data["department"]
        return ()

    def _insert_profile(self, profile: tuple[str, ...], user_id: str, role: str) -> None:
        if role == "Student":
            self.connection.execute("INSERT INTO Students VALUES (?, ?, ?)", (profile[0], user_id, profile[1]))
        elif role == "Lecturer":
            self.connection.execute("INSERT INTO Lecturers VALUES (?, ?, ?)", (profile[0], user_id, profile[1]))

    @staticmethod
    def _constraint_message(error: Exception) -> str:
        message = str(error)
        if "username" in message:
            return "username must be unique"
        if "email" in message:
            return "email must be unique"
        return message or "Request violates a database constraint"


def create_app(database: str = ":memory:") -> AttendanceAPI:
    return AttendanceAPI(database)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    database_path = os.environ.get("DATABASE_PATH", "attendance.db")
    with make_server("0.0.0.0", 8000, create_app(database_path)) as server:
        print("Attendance API listening on http://127.0.0.1:8000")
        server.serve_forever()
