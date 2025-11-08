"""
Tests for consumption data processing and calculation
"""
import pytest
from unittest.mock import Mock, patch
from app import app

class TestConsumptionProcessing:
    """Test consumption data processing logic"""
    
    def test_consumption_wh_to_kwh_conversion(self, client, mock_requests):
        """Test conversion from Wh to kWh"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"timestamp": "2024-01-01T00:00:00Z", "consumption": 5000},  # 5 kWh
            {"timestamp": "2024-01-01T01:00:00Z", "consumption": 3000},  # 3 kWh
        ]
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['total_kwh'] == 8.0  # 5 + 3
        assert data['total_price'] == 8.0
        assert len(data['hourly_data']) == 2
        assert data['hourly_data'][0]['consumption'] == 5.0
        assert data['hourly_data'][1]['consumption'] == 3.0
    
    def test_consumption_already_in_kwh(self, client, mock_requests):
        """Test consumption already in kWh (small values)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"timestamp": "2024-01-01T00:00:00Z", "consumption": 0.5},  # Already kWh
            {"timestamp": "2024-01-01T01:00:00Z", "consumption": 0.3},  # Already kWh
        ]
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['total_kwh'] == 0.8
        assert data['total_price'] == 0.8
    
    def test_consumption_empty_list(self, client, mock_requests):
        """Test empty consumption data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['success'] is True
        assert data['total_kwh'] == 0.0
        assert data['total_price'] == 0.0
        assert len(data['hourly_data']) == 0
    
    def test_consumption_different_field_names(self, client, mock_requests):
        """Test consumption with different field names"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"timestamp": "2024-01-01T00:00:00Z", "energy": 5000},
            {"timestamp": "2024-01-01T01:00:00Z", "kwh": 3.0},
            {"timestamp": "2024-01-01T02:00:00Z", "wh": 2000},
        ]
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['success'] is True
        assert data['total_kwh'] == 10.0  # 5 + 3 + 2
        assert len(data['hourly_data']) == 3
    
    def test_consumption_dict_response(self, client, mock_requests):
        """Test consumption with dict response (wrapped data)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"timestamp": "2024-01-01T00:00:00Z", "consumption": 5000},
                {"timestamp": "2024-01-01T01:00:00Z", "consumption": 3000},
            ]
        }
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['success'] is True
        assert data['total_kwh'] == 8.0
    
    def test_consumption_price_calculation(self, client, mock_requests):
        """Test price calculation (1 kWh = 1 NOK)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"timestamp": "2024-01-01T00:00:00Z", "consumption": 10000},  # 10 kWh
        ]
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['total_kwh'] == 10.0
        assert data['total_price'] == 10.0  # 1 kWh = 1 NOK
    
    def test_consumption_rounding(self, client, mock_requests):
        """Test consumption values are properly rounded"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"timestamp": "2024-01-01T00:00:00Z", "consumption": 1234},  # 1.234 kWh
            {"timestamp": "2024-01-01T01:00:00Z", "consumption": 5678},  # 5.678 kWh
        ]
        mock_requests.get.return_value = mock_response
        
        with client.session_transaction() as sess:
            sess['access_token'] = 'test-token'
        
        response = client.get('/api/consumption/CH1?year=2024&month=1')
        data = response.get_json()
        
        assert data['total_kwh'] == 6.91  # 1.234 + 5.678 = 6.912, rounded to 6.91
        assert data['total_price'] == 6.91

