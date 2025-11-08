"""
Tests for HTML templates structure and content
"""
import pytest
from unittest.mock import patch

class TestTemplates:
    """Test template rendering and structure"""
    
    def test_login_template_structure(self, client):
        """Test login template has required elements"""
        response = client.get('/login')
        html = response.data.decode('utf-8')
        
        # Check for key elements
        assert 'EV Charging Invoicing' in html
        assert 'username' in html.lower()
        assert 'password' in html.lower()
        assert 'form' in html.lower()
        assert 'Sign In' in html or 'sign in' in html.lower()
    
    def test_dashboard_template_structure(self, client, authenticated_session):
        """Test dashboard template has required elements"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/dashboard')
        html = response.data.decode('utf-8')
        
        # Check for key elements
        assert 'site' in html.lower() or 'Site' in html
        assert 'charger' in html.lower() or 'Charger' in html
        assert 'month' in html.lower() or 'Month' in html
        assert 'Generate Report' in html or 'generate' in html.lower()
        assert 'logout' in html.lower() or 'Logout' in html
    
    def test_dashboard_has_javascript(self, client, authenticated_session):
        """Test dashboard has JavaScript functions"""
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/dashboard')
        html = response.data.decode('utf-8')
        
        # Check for JavaScript functions
        assert 'loadSites' in html
        assert 'loadChargers' in html
        assert 'generateReport' in html
        assert 'displayReport' in html
    
    def test_error_display_in_login(self, client):
        """Test error message display in login"""
        # Simulate error by posting invalid data
        with patch('app.easee_api.authenticate', return_value=(False, "Invalid credentials")):
            response = client.post('/login', data={
                'username': 'test',
                'password': 'test'
            })
            html = response.data.decode('utf-8')
            assert 'error' in html.lower() or 'Authentication failed' in html

