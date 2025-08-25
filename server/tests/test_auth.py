import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the directory where main.py lives to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import main  # noqa

class TestAuthEndpoints:
    """Test authentication-related endpoints"""
    
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
    
    @patch('main.auth.verify_id_token')
    def test_protected_route_success(self, mock_verify_token):
        """Test protected route with valid token"""
        # Mock successful token verification
        mock_verify_token.return_value = {
            "uid": "test_user_123",
            "email": "test@example.com"
        }
        
        headers = {"Authorization": "Bearer valid_token_here"}
        response = self.client.get("/protected", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Access granted to protected route!"
        assert data["user"]["uid"] == "test_user_123"
        assert data["user"]["email"] == "test@example.com"
        
    def test_protected_route_no_token(self):
        """Test protected route without token"""
        response = self.client.get("/protected")
        assert response.status_code == 403  # Forbidden
        
    def test_protected_route_invalid_token_format(self):
        """Test protected route with invalid token format"""
        headers = {"Authorization": "InvalidFormat token_here"}
        response = self.client.get("/protected", headers=headers)
        assert response.status_code == 403  # Forbidden
        
    @patch('main.auth.verify_id_token')
    def test_protected_route_expired_token(self, mock_verify_token):
        """Test protected route with expired token"""
        # Mock expired token error
        from firebase_admin.auth import InvalidIdTokenError
        mock_verify_token.side_effect = InvalidIdTokenError("Token has expired")
        
        headers = {"Authorization": "Bearer expired_token_here"}
        response = self.client.get("/protected", headers=headers)
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
        
    @patch('main.auth.verify_id_token')
    def test_protected_route_invalid_token(self, mock_verify_token):
        """Test protected route with invalid token"""
        # Mock invalid token error
        from firebase_admin.auth import InvalidIdTokenError
        mock_verify_token.side_effect = InvalidIdTokenError("Invalid ID token")
        
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = self.client.get("/protected", headers=headers)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() 