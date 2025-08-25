import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add the directory where main.py lives to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import main  # noqa

class TestBasicEndpoints:
    """Test basic endpoints that don't require authentication"""
    
    def setup_method(self):
        """Setup test client for each test"""
        self.client = TestClient(main.app)
    
    def test_root_route(self):
        """Test the root endpoint (no auth required)"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "FastAPI server is online. No authentication needed."
        }
    
    def test_root_route_response_structure(self):
        """Test that root endpoint returns expected structure"""
        response = self.client.get("/")
        data = response.json()
        
        # Check that response has the expected structure
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0
    
    def test_root_route_multiple_requests(self):
        """Test that root endpoint works consistently across multiple requests"""
        for _ in range(3):
            response = self.client.get("/")
            assert response.status_code == 200
            assert response.json() == {
                "message": "FastAPI server is online. No authentication needed."
            }
