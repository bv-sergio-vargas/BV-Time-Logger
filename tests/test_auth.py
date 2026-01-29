"""
Unit tests for authentication providers
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import base64

from src.auth.graph_auth import GraphAuthProvider
from src.auth.devops_auth import DevOpsAuthProvider


class TestGraphAuthProvider:
    """Tests for GraphAuthProvider"""
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_init(self, mock_msal, mock_env_vars):
        """Test initialization with explicit parameters"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id"
        )
        
        assert provider.client_id == "test-client-id"
        assert provider.client_secret == "test-client-secret"
        assert provider.tenant_id == "test-tenant-id"
        assert provider.authority == "https://login.microsoftonline.com/test-tenant-id"
        assert provider.scopes == ["https://graph.microsoft.com/.default"]
        assert provider._token_cache is None
        assert provider._token_expiry is None
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_from_env(self, mock_msal, mock_env_vars):
        """Test factory method from environment variables"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        
        assert provider.client_id == "test-client-id"
        assert provider.client_secret == "test-client-secret"
        assert provider.tenant_id == "test-tenant-id"
    
    def test_from_env_missing_variable(self, monkeypatch):
        """Test from_env raises error when variables missing"""
        monkeypatch.delenv('AZURE_AD_CLIENT_ID', raising=False)
        
        with pytest.raises(ValueError, match="AZURE_AD_CLIENT_ID"):
            GraphAuthProvider.from_env()
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_get_access_token_new(self, mock_msal, mock_env_vars):
        """Test getting new access token"""
        # Mock MSAL response
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            'access_token': 'new-token-12345',
            'expires_in': 3600
        }
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        token = provider.get_access_token()
        
        assert token == 'new-token-12345'
        assert provider._token_cache == 'new-token-12345'
        assert provider._token_expiry is not None
        mock_app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://graph.microsoft.com/.default"]
        )
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_get_access_token_cached(self, mock_msal, mock_env_vars):
        """Test using cached token when still valid"""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            'access_token': 'cached-token',
            'expires_in': 3600
        }
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        
        # First call - should acquire new token
        token1 = provider.get_access_token()
        call_count_after_first = mock_app.acquire_token_for_client.call_count
        
        # Second call - should use cached token
        token2 = provider.get_access_token()
        
        assert token1 == token2 == 'cached-token'
        assert mock_app.acquire_token_for_client.call_count == call_count_after_first
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_get_access_token_expired(self, mock_msal, mock_env_vars):
        """Test refreshing expired token"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        
        # Set expired token
        provider._token_cache = 'old-token'
        provider._token_expiry = datetime.utcnow() - timedelta(minutes=10)
        
        # Mock new token response
        mock_app.acquire_token_for_client.return_value = {
            'access_token': 'refreshed-token',
            'expires_in': 3600
        }
        
        token = provider.get_access_token()
        
        assert token == 'refreshed-token'
        assert provider._token_cache == 'refreshed-token'
        mock_app.acquire_token_for_client.assert_called_once()
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_get_access_token_error(self, mock_msal, mock_env_vars):
        """Test error handling when token acquisition fails"""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            'error': 'invalid_client',
            'error_description': 'Client authentication failed'
        }
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        
        with pytest.raises(Exception, match="Failed to acquire token"):
            provider.get_access_token()
    
    def test_is_token_valid_no_token(self, mock_env_vars):
        """Test _is_token_valid with no cached token"""
        provider = GraphAuthProvider.from_env()
        
        assert not provider._is_token_valid()
    
    def test_is_token_valid_expired(self, mock_env_vars):
        """Test _is_token_valid with expired token"""
        provider = GraphAuthProvider.from_env()
        provider._token_cache = 'some-token'
        provider._token_expiry = datetime.utcnow() - timedelta(minutes=1)
        
        assert not provider._is_token_valid()
    
    def test_is_token_valid_near_expiry(self, mock_env_vars):
        """Test _is_token_valid with token near expiry (within 5 min buffer)"""
        provider = GraphAuthProvider.from_env()
        provider._token_cache = 'some-token'
        provider._token_expiry = datetime.utcnow() + timedelta(minutes=3)
        
        assert not provider._is_token_valid()
    
    def test_is_token_valid_ok(self, mock_env_vars):
        """Test _is_token_valid with valid token"""
        provider = GraphAuthProvider.from_env()
        provider._token_cache = 'some-token'
        provider._token_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        assert provider._is_token_valid()
    
    @patch('src.auth.graph_auth.msal.ConfidentialClientApplication')
    def test_get_auth_headers(self, mock_msal, mock_env_vars):
        """Test getting authorization headers"""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        mock_msal.return_value = mock_app
        
        provider = GraphAuthProvider.from_env()
        headers = provider.get_auth_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-token'
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'
    
    def test_invalidate_token(self, mock_env_vars):
        """Test token invalidation"""
        provider = GraphAuthProvider.from_env()
        provider._token_cache = 'some-token'
        provider._token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        provider.invalidate_token()
        
        assert provider._token_cache is None
        assert provider._token_expiry is None


class TestDevOpsAuthProvider:
    """Tests for DevOpsAuthProvider"""
    
    def test_init(self):
        """Test initialization with explicit parameters"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat",
            project="Test Project"
        )
        
        assert provider.organization == "test-org"
        assert provider.pat == "test-pat"
        assert provider.project == "Test Project"
        assert provider.base_url == "https://dev.azure.com/test-org"
    
    def test_from_env(self, mock_env_vars):
        """Test factory method from environment variables"""
        provider = DevOpsAuthProvider.from_env()
        
        assert provider.organization == "test-org"
        assert provider.pat == "test-pat-token-12345"
        assert provider.project == "Test Project"
    
    def test_from_env_missing_variable(self, monkeypatch):
        """Test from_env raises error when variables missing"""
        monkeypatch.delenv('AZURE_DEVOPS_ORGANIZATION', raising=False)
        
        with pytest.raises(ValueError, match="AZURE_DEVOPS_ORGANIZATION"):
            DevOpsAuthProvider.from_env()
    
    def test_encode_pat(self):
        """Test PAT encoding"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat-12345",
            project="Test Project"
        )
        
        encoded = provider._encode_pat()
        
        # Verify it's valid base64
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert decoded == ":test-pat-12345"
    
    def test_get_auth_headers(self):
        """Test getting authorization headers"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat-12345",
            project="Test Project"
        )
        
        headers = provider.get_auth_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic ')
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'
        
        # Verify the encoded PAT is correct
        encoded_pat = headers['Authorization'].replace('Basic ', '')
        decoded = base64.b64decode(encoded_pat).decode('utf-8')
        assert decoded == ":test-pat-12345"
    
    def test_get_project_url(self):
        """Test project URL generation"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat",
            project="Test Project"
        )
        
        url = provider.get_project_url()
        
        assert url == "https://dev.azure.com/test-org/Test%20Project"
    
    def test_get_api_url(self):
        """Test API URL generation"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat",
            project="Test Project"
        )
        
        # Test without endpoint
        url = provider.get_api_url()
        assert url == "https://dev.azure.com/test-org/Test%20Project/_apis"
        
        # Test with endpoint
        url = provider.get_api_url("wit/workitems")
        assert url == "https://dev.azure.com/test-org/Test%20Project/_apis/wit/workitems"
        
        # Test with leading slash
        url = provider.get_api_url("/wit/workitems")
        assert url == "https://dev.azure.com/test-org/Test%20Project/_apis/wit/workitems"
    
    def test_get_api_url_with_query_params(self):
        """Test API URL with query parameters"""
        provider = DevOpsAuthProvider(
            organization="test-org",
            pat="test-pat",
            project="Test Project"
        )
        
        url = provider.get_api_url("wit/workitems/123", api_version="7.0")
        
        assert "api-version=7.0" in url
        assert "Test%20Project" in url
    
    @patch('src.auth.devops_auth.requests.get')
    def test_validate_permissions_success(self, mock_get, mock_env_vars):
        """Test permission validation success"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 1,
            "value": [{"id": "project-1", "name": "Test Project"}]
        }
        mock_get.return_value = mock_response
        
        provider = DevOpsAuthProvider.from_env()
        result = provider.validate_permissions()
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch('src.auth.devops_auth.requests.get')
    def test_validate_permissions_failure(self, mock_get, mock_env_vars):
        """Test permission validation failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        provider = DevOpsAuthProvider.from_env()
        result = provider.validate_permissions()
        
        assert result is False
    
    @patch('src.auth.devops_auth.requests.get')
    def test_validate_permissions_exception(self, mock_get, mock_env_vars):
        """Test permission validation with exception"""
        mock_get.side_effect = Exception("Network error")
        
        provider = DevOpsAuthProvider.from_env()
        result = provider.validate_permissions()
        
        assert result is False
