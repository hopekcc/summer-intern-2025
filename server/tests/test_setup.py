import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import main  # noqa
from server.scripts.database_models import init_database, get_room
from server.scripts.utils import ConnectionManager

class TestSetup:
    """Test that the basic setup is working correctly"""
    
    def setup_method(self):
        """Setup test client for each test"""
        self.client = TestClient(main.app)
    
    def test_app_imports_correctly(self):
        """Test that the main app can be imported without errors"""
        assert main.app is not None
        assert hasattr(main.app, 'routes')
    
    def test_scripts_imports_work(self):
        """Test that scripts modules can be imported"""
        try:
            # Imports are now at the top level, so if we reach here, they worked.
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    def test_root_endpoint_accessible(self):
        """Test that the root endpoint is accessible"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
    
    @pytest.mark.unit
    def test_connection_manager_creation(self):
        """Test that ConnectionManager can be created"""
        manager = ConnectionManager()
        assert manager is not None
        assert hasattr(manager, 'active_connections')
        assert isinstance(manager.active_connections, dict) 