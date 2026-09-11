import json
import io
from unittest.mock import MagicMock

class APIClient:
    def __init__(self, api):
        self.api = api
    
    def request(self, method, endpoint, data=None, token=None):
        """
        Gọi API WSGI và trả về (status_code, response_dict)
        """
        if data is None:
            data = {}
        
        # Chuẩn bị body
        body = json.dumps(data).encode() if data else b'{}'
        
        # Tạo environ dict
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": endpoint,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
            "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
            "QUERY_STRING": ""
        }
        
        # Lưu response status
        response_data = {"status": None}
        
        def start_response(status, headers):
            response_data["status"] = int(status.split()[0])
        
        # Gọi API
        result = self.api(environ, start_response)
        
        # Parse kết quả
        body_bytes = b''.join(result)
        response_body = json.loads(body_bytes) if body_bytes else {}
        
        return response_data["status"], response_body
