import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import main  # noqa
from server.dependencies import get_database_dir

# Override the database directory for testing
def get_test_database_dir():
    # This path is relative to the 'tests' directory
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "test_song_database"))

main.app.dependency_overrides[get_database_dir] = get_test_database_dir


class TestRoomEndpoints:
    """Test room-related endpoints"""
    
    def setup_method(self):
        """Setup test client for each test"""
        self.client = TestClient(main.app)
        self.auth_headers = {"Authorization": "Bearer valid_token_here"}
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.create_room_db')
    @patch('server.routers.rooms.generate_room_id_db')
    def test_create_room_success(self, mock_generate_id, mock_create_room, mock_verify_token):
        """Test creating a new room"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_generate_id.return_value = "room123"
        mock_create_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": None,
            "current_page": 1
        }
        
        response = self.client.post("/rooms/create", headers=self.auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == "room123"
        
    @patch('server.routers.rooms.auth.verify_id_token')
    def test_create_room_no_auth(self, mock_verify_token):
        """Test creating room without authentication"""
        response = self.client.post("/rooms/create")
        assert response.status_code == 403  # Forbidden
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_join_room_success(self, mock_get_room, mock_verify_token):
        """Test joining an existing room"""
        mock_verify_token.return_value = {"uid": "new_user", "email": "new@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": None,
            "current_page": 1
        }
        
        with patch('server.routers.rooms.update_room') as mock_update:
            mock_update.return_value = {
                "room_id": "room123",
                "host_id": "test_user",
                "participants": ["test_user", "new_user"],
                "current_song": None,
                "current_page": 1
            }
            response = self.client.post("/rooms/join/room123", headers=self.auth_headers)
            
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == "room123"
        assert "new_user" in data["participants"]
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_join_room_not_found(self, mock_get_room, mock_verify_token):
        """Test joining a room that doesn't exist"""
        mock_verify_token.return_value = {"uid": "new_user", "email": "new@example.com"}
        mock_get_room.return_value = None
        
        response = self.client.post("/rooms/join/nonexistent", headers=self.auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_get_room_details(self, mock_get_room, mock_verify_token):
        """Test getting room details"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user", "other_user"],
            "current_song": "song1",
            "current_page": 2
        }
        
        response = self.client.get("/rooms/room123", headers=self.auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == "room123"
        assert data["host_id"] == "test_user"
        assert len(data["participants"]) == 2
        assert data["current_song"] == "song1"
        assert data["current_page"] == 2
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_leave_room_success(self, mock_get_room, mock_verify_token):
        """Test leaving a room"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "other_user",
            "participants": ["test_user", "other_user"],
            "current_song": None,
            "current_page": 1
        }
        
        with patch('server.routers.rooms.update_room') as mock_update:
            mock_update.return_value = {
                "room_id": "room123",
                "host_id": "other_user",
                "participants": ["other_user"],
                "current_song": None,
                "current_page": 1
            }
            response = self.client.post("/rooms/room123/leave", headers=self.auth_headers)
            
        assert response.status_code == 200
        data = response.json()
        assert "left room" in data["message"]
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_select_song_for_room(self, mock_get_room, mock_verify_token):
        """Test selecting a song for a room"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": None,
            "current_page": 1
        }
        
        payload = {"song_id": "0001"}  # Use real song ID from test database
        
        with patch('server.routers.rooms.update_room') as mock_update:
            mock_update.return_value = {
                "room_id": "room123",
                "host_id": "test_user",
                "participants": ["test_user"],
                "current_song": "0001",
                "current_page": 1
            }
            response = self.client.post("/rooms/room123/song", 
                                      json=payload, 
                                      headers=self.auth_headers)
            
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_update_room_page(self, mock_get_room, mock_verify_token):
        """Test updating room page"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": "0001",  # Use real song ID from test database
            "current_page": 1
        }
        
        payload = {"page": 2}  # Use page 2 since PDF only has 2 pages
        
        with patch('server.routers.rooms.update_room') as mock_update:
            mock_update.return_value = {
                "room_id": "room123",
                "host_id": "test_user",
                "participants": ["test_user"],
                "current_song": "0001",
                "current_page": 2
            }
            response = self.client.post("/rooms/room123/page", 
                                      json=payload, 
                                      headers=self.auth_headers)
            
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_get_current_room_state(self, mock_get_room, mock_verify_token):
        """Test getting current room state"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": "0001",  # Use real song ID from test database
            "current_page": 2
        }
        
        # Use real test database files - no mocking needed
        response = self.client.get("/rooms/room123/current", headers=self.auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "state_sync"
        assert data["song_id"] == "0001"
        assert data["current_page"] == 2
        assert "image" in data
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_download_room_pdf(self, mock_get_room, mock_verify_token):
        """Test downloading room PDF"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": "0001",  # Use real song ID from test database
            "current_page": 1
        }
        
        # Use real test database files - no mocking needed
        response = self.client.get("/rooms/room123/pdf", headers=self.auth_headers)
                
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        
    @patch('server.routers.rooms.auth.verify_id_token')
    @patch('server.routers.rooms.get_room')
    def test_download_room_pdf_no_song(self, mock_get_room, mock_verify_token):
        """Test downloading room PDF when no song is selected"""
        mock_verify_token.return_value = {"uid": "test_user", "email": "test@example.com"}
        mock_get_room.return_value = {
            "room_id": "room123",
            "host_id": "test_user",
            "participants": ["test_user"],
            "current_song": None,
            "current_page": 1
        }
        
        response = self.client.get("/rooms/room123/pdf", headers=self.auth_headers)
        
        assert response.status_code == 400
        assert "no song selected" in response.json()["detail"].lower() 