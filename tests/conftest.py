"""
Pytest configuration and shared fixtures
"""
import pytest
from unittest.mock import Mock, patch
from app import app, EaseeAPI

@pytest.fixture
def client():
    """Create a test client for Flask app"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def mock_requests():
    """Mock requests library - patches requests module used in app"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        mock_obj = type('MockRequests', (), {'get': mock_get, 'post': mock_post})()
        yield mock_obj

@pytest.fixture
def easee_api():
    """Create an EaseeAPI instance"""
    return EaseeAPI()

@pytest.fixture
def mock_auth_response():
    """Mock successful authentication response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "accessToken": "test-access-token-12345",
        "expiresIn": 3600
    }
    return mock_response

@pytest.fixture
def mock_sites_response():
    """Mock sites API response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "name": "Site 1", "address": "Address 1"},
        {"id": 2, "name": "Site 2", "address": "Address 2"}
    ]
    return mock_response

@pytest.fixture
def mock_chargers_response():
    """Mock chargers API response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": "CH1", "name": "Charger 1", "siteId": 1},
        {"id": "CH2", "name": "Charger 2", "siteId": 1}
    ]
    return mock_response

@pytest.fixture
def mock_consumption_response():
    """Mock consumption API response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "consumption": 5000,  # 5 kWh in Wh
            "chargerId": "CH1"
        },
        {
            "timestamp": "2024-01-01T01:00:00Z",
            "consumption": 3000,  # 3 kWh in Wh
            "chargerId": "CH1"
        },
        {
            "timestamp": "2024-01-01T02:00:00Z",
            "consumption": 2000,  # 2 kWh in Wh
            "chargerId": "CH1"
        }
    ]
    return mock_response

@pytest.fixture
def authenticated_session(client):
    """Create an authenticated session"""
    with client.session_transaction() as sess:
        sess['access_token'] = 'test-access-token-12345'
        sess['username'] = 'testuser'
    return sess

