class APIClient:
    def __init__(self, api):
        self.api = api
    
    def request(self, method, endpoint, data=None, token=None):
        """
        Make a request to the API.
        Returns (status_code, response_dict)
        """
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        # Route the request to the appropriate API method based on endpoint
        if method == "POST" and endpoint == "/api/auth/login":
            return self.api.login(data.get("username"), data.get("password"))
        
        elif method == "POST" and endpoint == "/api/users":
            return self.api.create_user(data, token)
        
        elif method == "POST" and endpoint == "/api/sessions":
            return self.api.create_session(data, token)
        
        elif method == "POST" and endpoint == "/api/attendance":
            return self.api.mark_attendance(data, token)
        
        elif method == "GET" and endpoint == "/api/reports/attendance":
            return self.api.get_attendance_report(token)
        
        # Default response if endpoint not found
        return (404, {"error": "Endpoint not found"})
