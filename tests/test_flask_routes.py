"""
Integration tests for Flask routes
"""
import pytest
from unittest.mock import patch, Mock
import json

class TestLoginRoutes:
    """Test login and authentication routes"""
    
    def test_login_page_get(self, client):
        """Test login page loads"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'EV Charging Invoicing' in response.data
        assert b'Sign in' in response.data
    
    def test_login_success(self, client, mock_requests, mock_auth_response):
        """Test successful login"""
        mock_requests.post.return_value = mock_auth_response
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to dashboard
        assert b'Select Site' in response.data or b'Site' in response.data or b'EV Charging Invoicing' in response.data
    
    def test_login_failure(self, client, mock_requests):
        """Test login with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_requests.post.return_value = mock_response
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        })
        
        assert response.status_code == 200
        assert b'Authentication failed' in response.data
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post('/login', data={})
        assert response.status_code == 200
        assert b'Please provide both username and password' in response.data
    
    def test_logout(self, client, authenticated_session):
        """Test logout functionality"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Sign in' in response.data
        
        # Session should be cleared
        with client.session_transaction() as sess:
            assert 'access_token' not in sess

class TestDashboardRoutes:
    """Test dashboard routes"""
    
    def test_dashboard_requires_auth(self, client):
        """Test dashboard redirects when not authenticated"""
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'Sign in' in response.data
    
    def test_dashboard_authenticated(self, client, authenticated_session):
        """Test dashboard loads when authenticated"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Select Site' in response.data or b'Site' in response.data
    
    def test_index_redirects_to_login(self, client):
        """Test index route redirects to login"""
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert b'Sign in' in response.data
    
    def test_index_redirects_to_dashboard_when_authenticated(self, client, authenticated_session):
        """Test index redirects to dashboard when authenticated"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert b'Select Site' in response.data or b'Site' in response.data

class TestAPIRoutes:
    """Test API endpoints"""
    
    def test_api_sites_requires_auth(self, client):
        """Test sites API requires authentication"""
        response = client.get('/api/sites')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_api_sites_success(self, client, mock_requests, mock_sites_response):
        """Test successful sites API call"""
        mock_requests.get.return_value = mock_sites_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/sites')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['sites']) == 2
    
    def test_api_sites_failure(self, client, mock_requests):
        """Test sites API failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'invalid-token'
        
        response = client.get('/api/sites')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_api_chargers_requires_auth(self, client):
        """Test chargers API requires authentication"""
        response = client.get('/api/chargers/1')
        assert response.status_code == 401
    
    def test_api_chargers_success(self, client, mock_requests, mock_chargers_response):
        """Test successful chargers API call"""
        mock_requests.get.return_value = mock_chargers_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/chargers/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['chargers']) == 2
    
    def test_api_consumption_requires_auth(self, client):
        """Test consumption API requires authentication"""
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        assert response.status_code == 401
    
    def test_api_consumption_missing_params(self, client, authenticated_session):
        """Test consumption API with missing parameters"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_api_consumption_success(self, client, mock_requests, mock_consumption_response):
        """Test successful consumption API call"""
        mock_requests.get.return_value = mock_consumption_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'total_kwh' in data
        assert 'total_price' in data
        assert 'hourly_data' in data
        # Total should be 10 kWh (5 + 3 + 2)
        assert data['total_kwh'] == 10.0
        assert data['total_price'] == 10.0  # 1 kWh = 1 NOK

