from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.session import router


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestSessionRouter:
    @patch('routers.session.create_new_session')
    @patch('routers.session.delete_session')
    def test_set_session_with_valid_existing_session(self, mock_delete, mock_create):
        """Test setting session with valid existing session"""
        from utils.session import get_session_id, validate_session_id, get_session_storage
        
        # Mock dependencies
        mock_storage = MagicMock()
        mock_create.return_value = "new_session_456"
        
        # Override dependencies for this test
        app.dependency_overrides[get_session_storage] = lambda: mock_storage
        app.dependency_overrides[get_session_id] = lambda: "old_session_123"
        app.dependency_overrides[validate_session_id] = lambda: True
        
        try:
            response = client.post("/session/")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["session_id"] == "new_session_456"
            assert response_data["valid_session"] is True
            
            # Verify old session was deleted
            mock_delete.assert_called_once()
            # Verify new session was created
            mock_create.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @patch('routers.session.create_new_session')
    @patch('routers.session.delete_session')
    @patch('routers.session.validate_session_id')
    @patch('routers.session.get_session_id')
    @patch('routers.session.get_session_storage')
    def test_set_session_with_invalid_existing_session(
        self, mock_get_storage, mock_get_id, mock_validate, mock_delete, mock_create
    ):
        """Test setting session with invalid existing session"""
        # Mock dependencies
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_get_id.return_value = "invalid_session"
        mock_validate.return_value = False
        mock_create.return_value = "new_session_456"
        
        response = client.post("/session/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == "new_session_456"
        assert response_data["valid_session"] is True
        
        # Verify old session was NOT deleted (since it was invalid)
        mock_delete.assert_not_called()
        # Verify new session was created
        mock_create.assert_called_once()

    def test_get_session_status_valid(self):
        """Test getting status of valid session"""
        from utils.session import get_session_id, validate_session_id
        
        # Override dependencies for this test
        app.dependency_overrides[get_session_id] = lambda: "session_123"
        app.dependency_overrides[validate_session_id] = lambda: True
        
        try:
            response = client.get("/session/")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["session_id"] == "session_123"
            assert response_data["valid_session"] is True
        finally:
            app.dependency_overrides.clear()

    def test_get_session_status_invalid(self):
        """Test getting status of invalid session"""
        from utils.session import get_session_id, validate_session_id
        
        # Override dependencies for this test
        app.dependency_overrides[get_session_id] = lambda: "invalid_session"
        app.dependency_overrides[validate_session_id] = lambda: False
        
        try:
            response = client.get("/session/")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["session_id"] == "invalid_session"
            assert response_data["valid_session"] is False
        finally:
            app.dependency_overrides.clear()

    @patch('routers.session.delete_session')
    @patch('routers.session.get_session_id')
    @patch('routers.session.get_session_storage')
    def test_end_session_success(self, mock_get_storage, mock_get_id, mock_delete):
        """Test successful session termination"""
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_get_id.return_value = "session_123"
        
        response = client.delete("/session/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Session ended successfully"
        
        # Verify session was deleted
        mock_delete.assert_called_once()

    @patch('routers.session.create_new_session')
    @patch('routers.session.validate_session_id')
    @patch('routers.session.get_session_id')  
    @patch('routers.session.get_session_storage')
    def test_set_session_no_existing_session(
        self, mock_get_storage, mock_get_id, mock_validate, mock_create
    ):
        """Test setting session with no existing session"""
        # Mock dependencies
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_get_id.return_value = None
        mock_validate.return_value = False
        mock_create.return_value = "new_session_123"
        
        response = client.post("/session/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == "new_session_123"
        assert response_data["valid_session"] is True
        
        # Verify new session was created
        mock_create.assert_called_once()

    @patch('routers.session.get_session_id')
    @patch('routers.session.get_session_storage')
    def test_end_session_with_none_session_id(self, mock_get_storage, mock_get_id):
        """Test ending session with None session_id"""
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        mock_get_id.return_value = None
        
        with patch('routers.session.delete_session') as mock_delete:
            response = client.delete("/session/")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["message"] == "Session ended successfully"
            
            # delete_session should still be called even with None session_id
            mock_delete.assert_called_once()
