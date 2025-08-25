import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the app and dependencies *after* path setup
from server.main import app
from server.dependencies import (
    get_database_dir,
    get_songs_dir,
    get_metadata_path,
    get_songs_pdf_dir,
)

# Test database paths
TEST_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_ROOM_DB_PATH = os.path.join(TEST_BASE_DIR, "test_room_database")
TEST_SONG_DB_PATH = os.path.join(TEST_BASE_DIR, "test_song_database")
TEST_SONGS_METADATA_PATH = os.path.join(TEST_SONG_DB_PATH, "songs_metadata.json")
TEST_SONGS_DIR = os.path.join(TEST_SONG_DB_PATH, "songs")
TEST_SONGS_PDF_DIR = os.path.join(TEST_SONG_DB_PATH, "songs_pdf")

# Override dependencies for testing
app.dependency_overrides[get_database_dir] = lambda: TEST_SONG_DB_PATH
app.dependency_overrides[get_songs_dir] = lambda: TEST_SONGS_DIR
app.dependency_overrides[get_metadata_path] = lambda: TEST_SONGS_METADATA_PATH
app.dependency_overrides[get_songs_pdf_dir] = lambda: TEST_SONGS_PDF_DIR

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create the test database and files before any tests run."""
    os.makedirs(TEST_SONG_DB_PATH, exist_ok=True)
    os.makedirs(TEST_SONGS_DIR, exist_ok=True)
    os.makedirs(TEST_SONGS_PDF_DIR, exist_ok=True)

    metadata = {
        "0001": "(Let Me Be Your) Teddy Bear - Elvis Presley.pro",
        "0002": "59th Street Bridge Song (Feelin' Groovy).pro"
    }
    with open(TEST_SONGS_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    song1_content = "{title: (Let Me Be Your) Teddy Bear}"
    with open(os.path.join(TEST_SONGS_DIR, "(Let Me Be Your) Teddy Bear - Elvis Presley.pro"), "w") as f:
        f.write(song1_content)

    song2_content = "{title: 59th Street Bridge Song (Feelin' Groovy)}"
    with open(os.path.join(TEST_SONGS_DIR, "59th Street Bridge Song (Feelin' Groovy).pro"), "w") as f:
        f.write(song2_content)

@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase authentication for all tests"""
    with patch('main.auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {
            "uid": "test_user_123",
            "email": "test@example.com"
        }
        yield mock_verify

@pytest.fixture
def mock_songs_data():
    """Mock songs data for testing"""
    return {
        "song1": "Amazing Grace.pro",
        "song2": "How Great Thou Art.pro",
        "song3": "Great Is Thy Faithfulness.pro"
    }

@pytest.fixture
def mock_room_data():
    """Mock room data for testing"""
    return {
        "room_id": "room123",
        "host_id": "test_user",
        "participants": ["test_user", "other_user"],
        "current_song": "song1",
        "current_page": 2
    }

@pytest.fixture
def auth_headers():
    """Authentication headers for testing"""
    return {"Authorization": "Bearer valid_token_here"}

@pytest.fixture
def test_client():
    """Test client for FastAPI app"""
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'FIREBASE_API_KEY': 'test_api_key',
        'FIREBASE_JSON': json.dumps({
            "type": "service_account",
            "project_id": "test_project",
            "private_key_id": "test_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test.com",
            "client_id": "test_client_id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test.com"
        })
    }):
        yield 