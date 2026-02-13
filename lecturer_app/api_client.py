"""API client for lecturer app."""

from shared.api_client import APIClient
from shared.constants import API_BASE


class LecturerAPIClient(APIClient):
    """Extended API client for lecturer with additional methods."""
    
    # Topics
    def get_topics(self):
        """Get all topics."""
        return self._make_request('GET', f"{API_BASE}/topics")
    
    def create_topic(self, name, description=""):
        """Create a topic."""
        return self._make_request('POST', f"{API_BASE}/topics", {"name": name, "description": description})
    
    def update_topic(self, topic_id, name=None, description=None):
        """Update a topic."""
        data = {}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        return self._make_request('PUT', f"{API_BASE}/topics/{topic_id}", data)
    
    def delete_topic(self, topic_id):
        """Delete a topic."""
        return self._make_request('DELETE', f"{API_BASE}/topics/{topic_id}")
    
    # Questions
    def get_questions(self, topic_id=None):
        """Get questions, optionally filtered by topic."""
        params = {}
        if topic_id:
            params['topic_id'] = topic_id
        return self._make_request('GET', f"{API_BASE}/questions", params)
    
    def create_question(self, question_data):
        """Create a question."""
        return self._make_request('POST', f"{API_BASE}/questions", question_data)
    
    def update_question(self, question_id, question_data):
        """Update a question."""
        return self._make_request('PUT', f"{API_BASE}/questions/{question_id}", question_data)
    
    def delete_question(self, question_id):
        """Delete a question."""
        return self._make_request('DELETE', f"{API_BASE}/questions/{question_id}")
    
    # Tests
    def create_test(self, test_data):
        """Create a test."""
        return self._make_request('POST', f"{API_BASE}/tests", test_data)
    
    def update_test(self, test_id, test_data):
        """Update a test."""
        return self._make_request('PUT', f"{API_BASE}/tests/{test_id}", test_data)
    
    def delete_test(self, test_id):
        """Delete a test."""
        return self._make_request('DELETE', f"{API_BASE}/tests/{test_id}")
    
    # Submissions & Grading
    def get_submissions(self, test_id=None):
        """Get submissions."""
        params = {}
        if test_id:
            params['test_id'] = test_id
        return self._make_request('GET', f"{API_BASE}/submissions", params)
    
    def get_submission_for_grading(self, submission_id):
        """Get submission details for grading."""
        return self._make_request('GET', f"{API_BASE}/grading/submissions/{submission_id}")
    
    def grade_answer(self, answer_id, score=None, feedback=None):
        """Grade an answer."""
        data = {}
        if score is not None:
            data['score'] = score
        if feedback is not None:
            data['feedback'] = feedback
        return self._make_request('PUT', f"{API_BASE}/grading/answers/{answer_id}", data)
    
    def finalize_grading(self, submission_id):
        """Finalize grading for a submission."""
        return self._make_request('POST', f"{API_BASE}/grading/submissions/{submission_id}/finalize")
    
    # Statistics
    def get_statistics_overview(self):
        """Get overview statistics."""
        return self._make_request('GET', f"{API_BASE}/statistics/overview")
    
    def get_topic_statistics(self):
        """Get topic statistics."""
        return self._make_request('GET', f"{API_BASE}/statistics/topics")
    
    def get_student_statistics(self):
        """Get student statistics."""
        return self._make_request('GET', f"{API_BASE}/statistics/students")
    
    def get_test_statistics(self, test_id):
        """Get test statistics."""
        return self._make_request('GET', f"{API_BASE}/statistics/tests/{test_id}")
    
    # Students
    def get_students(self):
        """Get all students."""
        return self._make_request('GET', f"{API_BASE}/students")
    
    def create_student(self, username, password, student_id=None):
        """Create a student."""
        data = {"username": username, "password": password}
        if student_id:
            data["student_id"] = student_id
        return self._make_request('POST', f"{API_BASE}/students", data)
    
    def import_students_csv(self, file_path):
        """Import students from CSV."""
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.split('/')[-1], f, 'text/csv')}
            # Need to use requests directly for file upload
            url = f"{self.base_url}{API_BASE}/students/import"
            response = self.session.post(url, files=files)
            response.raise_for_status()
            return response.json() if response.content else {}

