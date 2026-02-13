"""Shared API client base class."""

import requests
from typing import Optional, Dict, Any
from shared.constants import API_BASE


class APIClient:
    """Base API client for making HTTP requests to the server."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     files: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                if files:
                    response = self.session.post(url, data=data, files=files)
                else:
                    response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def login(self, username: str, password: str, student_id: Optional[str] = None) -> Dict:
        """Login to the system."""
        data = {"username": username, "password": password}
        if student_id:
            data["student_id"] = student_id
        return self._make_request('POST', f"{API_BASE}/auth/login", data)
    
    def logout(self) -> Dict:
        """Logout from the system."""
        return self._make_request('POST', f"{API_BASE}/auth/logout")
    
    def get_current_user(self) -> Dict:
        """Get current user information."""
        return self._make_request('GET', f"{API_BASE}/auth/me")
    
    def get_tests(self) -> list:
        """Get all available tests."""
        return self._make_request('GET', f"{API_BASE}/tests")
    
    def get_test(self, test_id: int) -> Dict:
        """Get a specific test."""
        return self._make_request('GET', f"{API_BASE}/tests/{test_id}")
    
    def create_submission(self, test_id: int) -> Dict:
        """Create a new submission."""
        return self._make_request('POST', f"{API_BASE}/submissions", {"test_id": test_id})
    
    def get_submission(self, submission_id: int) -> Dict:
        """Get a submission."""
        return self._make_request('GET', f"{API_BASE}/submissions/{submission_id}")
    
    def save_answer(self, submission_id: int, question_id: int, answer_data: Dict) -> Dict:
        """Save an answer."""
        answer_data['question_id'] = question_id
        return self._make_request('POST', f"{API_BASE}/submissions/{submission_id}/answers", answer_data)
    
    def submit_submission(self, submission_id: int) -> Dict:
        """Submit a submission."""
        return self._make_request('POST', f"{API_BASE}/submissions/{submission_id}/submit")

