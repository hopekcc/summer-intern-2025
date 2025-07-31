import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
import json

from server.dependencies import get_database_dir

# Add the directory where main.py lives to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import main  # noqa

# Override the database directory for testing
def get_test_database_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "test_song_database"))

main.app.dependency_overrides[get_database_dir] = get_test_database_dir


class TestSongEndpoints:
    """Test song-related endpoints"""
    
    def setup_method(self):
        """Setup test client for each test"""
        self.client = TestClient(main.app)
        self.auth_headers = {"Authorization": "Bearer valid_token_here"}
        
    @patch('main.auth.verify_id_token')
    def test_get_songs_list(self, mock_verify_token):
        """Test getting list of all songs"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        # Use real test database files - no mocking needed
        response = self.client.get("/songs/list", headers=self.auth_headers)
                
        assert response.status_code == 200
        data = response.json()
        assert "0001" in data
        assert "0002" in data
        
    @patch('main.auth.verify_id_token')
    def test_get_songs_no_auth(self, mock_verify_token):
        """Test getting songs without authentication"""
        response = self.client.get("/songs/list")
        assert response.status_code == 403  # Forbidden
        
    @patch('main.auth.verify_id_token')
    def test_get_specific_song(self, mock_verify_token):
        """Test getting a specific song by ID"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        response = self.client.get("/songs/0001", headers=self.auth_headers)
                
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "0001"
        assert "title" in data
        assert data["title"] == "(Let Me Be Your) Teddy Bear - Elvis Presley"
        assert "content" not in data # Ensure full content is not returned

    @patch('main.auth.verify_id_token')
    def test_get_specific_song_not_found(self, mock_verify_token):
        """Test getting a song that doesn't exist"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        response = self.client.get("/songs/nonexistent", headers=self.auth_headers)
                
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]
        
    @patch('main.auth.verify_id_token')
    def test_get_song_pdf(self, mock_verify_token):
        """Test getting song PDF"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        # Use real test database files - no mocking needed
        response = self.client.get("/songs/0001/pdf", headers=self.auth_headers)
                
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        
    @patch('main.auth.verify_id_token')
    def test_get_song_pdf_not_found(self, mock_verify_token):
        """Test getting PDF for song that doesn't exist"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        response = self.client.get("/songs/nonexistent/pdf", headers=self.auth_headers)
                
        assert response.status_code == 404
        assert "song not found" in response.json()["detail"].lower()
        
    @patch('main.auth.verify_id_token')
    def test_search_songs(self, mock_verify_token):
        """Test searching songs with fuzzy search"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        # Use real test database files - no mocking needed
        response = self.client.get("/songs/search/Feelin' Groovy", headers=self.auth_headers)
                
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "59th Street Bridge Song (Feelin' Groovy)"
        
    @patch('main.auth.verify_id_token')
    def test_search_songs_no_results(self, mock_verify_token):
        """Test searching songs with no results"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        
        response = self.client.get("/songs/search/nonexistent", headers=self.auth_headers)
                
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0 