"""
Unit tests for EaseeAPI class
"""
import pytest
from unittest.mock import Mock, patch
from app import EaseeAPI

class TestEaseeAPI:
    """Test cases for EaseeAPI class"""
    
    def test_init(self, easee_api):
        """Test EaseeAPI initialization"""
        assert easee_api.access_token is None
        assert easee_api.base_url == "https://api.easee.com/api"
    
    def test_authenticate_success(self, easee_api, mock_requests, mock_auth_response):
        """Test successful authentication"""
        mock_requests.post.return_value = mock_auth_response
        
        success, result = easee_api.authenticate("testuser", "testpass")
        
        assert success is True
        assert result == "test-access-token-12345"
        assert easee_api.access_token == "test-access-token-12345"
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert "accounts/login" in call_args[0][0]
        assert call_args[1]["json"]["userName"] == "testuser"
        assert call_args[1]["json"]["password"] == "testpass"
    
    def test_authenticate_failure(self, easee_api, mock_requests):
        """Test authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_requests.post.return_value = mock_response
        
        success, result = easee_api.authenticate("testuser", "wrongpass")
        
        assert success is False
        assert "Invalid credentials" in result
    
    def test_authenticate_exception(self, easee_api, mock_requests):
        """Test authentication with exception"""
        mock_requests.post.side_effect = Exception("Connection error")
        
        success, result = easee_api.authenticate("testuser", "testpass")
        
        assert success is False
        assert "Connection error" in result
    
    def test_get_sites_success(self, easee_api, mock_requests, mock_sites_response):
        """Test successful sites retrieval"""
        mock_requests.get.return_value = mock_sites_response
        
        success, result = easee_api.get_sites("test-token")
        
        assert success is True
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Site 1"
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        assert "sites" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"
    
    def test_get_sites_failure(self, easee_api, mock_requests):
        """Test sites retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.get.return_value = mock_response
        
        success, result = easee_api.get_sites("invalid-token")
        
        assert success is False
        assert "Unauthorized" in result
    
    def test_get_chargers_success(self, easee_api, mock_requests, mock_chargers_response):
        """Test successful chargers retrieval"""
        mock_requests.get.return_value = mock_chargers_response
        
        success, result = easee_api.get_chargers("test-token", 1)
        
        assert success is True
        assert len(result) == 2
        assert result[0]["id"] == "CH1"
        assert result[0]["name"] == "Charger 1"
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        assert "sites/1/chargers" in call_args[0][0]
    
    def test_get_chargers_failure(self, easee_api, mock_requests):
        """Test chargers retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Site not found"
        mock_requests.get.return_value = mock_response
        
        success, result = easee_api.get_chargers("test-token", 999)
        
        assert success is False
        assert "Site not found" in result
    
    def test_get_hourly_consumption_success(self, easee_api, mock_requests, mock_consumption_response):
        """Test successful consumption retrieval"""
        mock_requests.get.return_value = mock_consumption_response
        
        success, result = easee_api.get_hourly_consumption("test-token", "CH1", 2024, 1)
        
        assert success is True
        assert len(result) == 3
        assert result[0]["consumption"] == 5000
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        assert "lifetime-energy/CH1/hourly" in call_args[0][0]
        assert "from" in call_args[1]["params"]
        assert "to" in call_args[1]["params"]
        # Check date format
        assert "2024-01-01" in call_args[1]["params"]["from"]
        assert "2024-01-31" in call_args[1]["params"]["to"] or "2024-02-01" in call_args[1]["params"]["to"]
    
    def test_get_hourly_consumption_december(self, easee_api, mock_requests, mock_consumption_response):
        """Test consumption retrieval for December (year boundary)"""
        mock_requests.get.return_value = mock_consumption_response
        
        success, result = easee_api.get_hourly_consumption("test-token", "CH1", 2024, 12)
        
        assert success is True
        call_args = mock_requests.get.call_args
        # Should handle December correctly (end of year)
        assert "2024-12-01" in call_args[1]["params"]["from"]
    
    def test_get_hourly_consumption_failure(self, easee_api, mock_requests):
        """Test consumption retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid date range"
        mock_requests.get.return_value = mock_response
        
        success, result = easee_api.get_hourly_consumption("test-token", "CH1", 2024, 1)
        
        assert success is False
        assert "Invalid date range" in result
    
    def test_get_hourly_consumption_exception(self, easee_api, mock_requests):
        """Test consumption retrieval with exception"""
        mock_requests.get.side_effect = Exception("Network error")
        
        success, result = easee_api.get_hourly_consumption("test-token", "CH1", 2024, 1)
        
        assert success is False
        assert "Network error" in result

