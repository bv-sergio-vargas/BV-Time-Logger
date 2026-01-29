"""
Unit tests for API clients
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

from src.clients.base_client import BaseAPIClient, HTTPMethod
from src.clients.teams_client import TeamsClient
from src.clients.azure_devops_client import AzureDevOpsClient
from src.auth.graph_auth import GraphAuthProvider
from src.auth.devops_auth import DevOpsAuthProvider


class TestBaseAPIClient:
    """Tests for BaseAPIClient"""
    
    @pytest.fixture
    def mock_auth_provider(self):
        """Mock authentication provider"""
        provider = Mock()
        provider.get_auth_headers.return_value = {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        }
        return provider
    
    def test_init(self, mock_auth_provider):
        """Test client initialization"""
        client = BaseAPIClient(mock_auth_provider)
        
        assert client.auth_provider == mock_auth_provider
        assert client.session is not None
        assert client.base_url is None
    
    def test_init_with_base_url(self, mock_auth_provider):
        """Test client initialization with base URL"""
        client = BaseAPIClient(mock_auth_provider, base_url="https://api.example.com")
        
        assert client.base_url == "https://api.example.com"
    
    def test_context_manager(self, mock_auth_provider):
        """Test context manager support"""
        with BaseAPIClient(mock_auth_provider) as client:
            assert client.session is not None
        
        # Session should be closed after context
        assert client.session is None
    
    @patch('src.clients.base_client.requests.Session')
    def test_create_session(self, mock_session_class, mock_auth_provider):
        """Test session creation with retry logic"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        client = BaseAPIClient(mock_auth_provider)
        
        # Verify retry adapter was mounted
        assert mock_session.mount.called
    
    @patch('requests.Session.request')
    def test_make_request_get_success(self, mock_request, mock_auth_provider):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.content = b'{"data":"test"}'  # Add content attribute
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        response = client._make_request(HTTPMethod.GET, 'https://api.example.com/test')
        
        assert response.status_code == 200
        assert response.json() == {'data': 'test'}
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_make_request_with_headers_merge(self, mock_request, mock_auth_provider):
        """Test request with merged headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        custom_headers = {'X-Custom-Header': 'custom-value'}
        
        client._make_request(
            HTTPMethod.GET,
            'https://api.example.com/test',
            headers=custom_headers
        )
        
        # Verify headers were merged
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        assert 'Authorization' in headers
        assert 'X-Custom-Header' in headers
    
    @patch('requests.Session.request')
    def test_make_request_rate_limit_429(self, mock_request, mock_auth_provider):
        """Test rate limiting handling (429 status)"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '2'}
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        
        with pytest.raises(HTTPError):
            client._make_request(HTTPMethod.GET, 'https://api.example.com/test')
    
    @patch('requests.Session.request')
    def test_make_request_server_error_500(self, mock_request, mock_auth_provider):
        """Test server error handling (500 status)"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        
        with pytest.raises(HTTPError):
            client._make_request(HTTPMethod.GET, 'https://api.example.com/test')
    
    @patch('requests.Session.request')
    def test_make_request_connection_error(self, mock_request, mock_auth_provider):
        """Test connection error handling"""
        mock_request.side_effect = ConnectionError("Network unreachable")
        
        client = BaseAPIClient(mock_auth_provider)
        
        with pytest.raises(ConnectionError):
            client._make_request(HTTPMethod.GET, 'https://api.example.com/test')
    
    @patch('requests.Session.request')
    def test_get_method(self, mock_request, mock_auth_provider):
        """Test GET method shortcut"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'ok'}
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        response = client.get('https://api.example.com/resource')
        
        assert response.status_code == 200
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == 'GET'
    
    @patch('requests.Session.request')
    def test_post_method(self, mock_request, mock_auth_provider):
        """Test POST method shortcut"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        data = {'name': 'test'}
        response = client.post('https://api.example.com/resource', json=data)
        
        assert response.status_code == 201
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == 'POST'
    
    @patch('requests.Session.request')
    def test_patch_method(self, mock_request, mock_auth_provider):
        """Test PATCH method shortcut"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        data = {'status': 'updated'}
        response = client.patch('https://api.example.com/resource/1', json=data)
        
        assert response.status_code == 200
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == 'PATCH'
    
    @patch('requests.Session.request')
    def test_delete_method(self, mock_request, mock_auth_provider):
        """Test DELETE method shortcut"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(mock_auth_provider)
        response = client.delete('https://api.example.com/resource/1')
        
        assert response.status_code == 204
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == 'DELETE'


class TestTeamsClient:
    """Tests for TeamsClient"""
    
    @pytest.fixture
    def mock_graph_auth(self, mock_env_vars):
        """Mock Graph authentication provider"""
        with patch('src.auth.graph_auth.msal.ConfidentialClientApplication'):
            return GraphAuthProvider.from_env()
    
    @patch('requests.Session.request')
    def test_get_user_info(self, mock_request, mock_graph_auth, sample_user_info):
        """Test getting user information"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_user_info
        mock_request.return_value = mock_response
        
        client = TeamsClient(mock_graph_auth)
        user_info = client.get_user_info()
        
        assert user_info['displayName'] == 'Test User'
        assert user_info['mail'] == 'test.user@example.com'
    
    @patch('requests.Session.request')
    def test_get_calendar_events(self, mock_request, mock_graph_auth, sample_calendar_event):
        """Test getting calendar events"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [sample_calendar_event]
        }
        mock_request.return_value = mock_response
        
        client = TeamsClient(mock_graph_auth)
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=1)
        
        events = client.get_calendar_events(start_date, end_date)
        
        assert len(events) == 1
        assert events[0]['subject'] == 'Team Standup'
    
    @patch('requests.Session.request')
    def test_get_online_meetings(self, mock_request, mock_graph_auth, sample_online_meeting):
        """Test getting online meetings"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [sample_online_meeting]
        }
        mock_request.return_value = mock_response
        
        client = TeamsClient(mock_graph_auth)
        meetings = client.get_online_meetings()
        
        assert len(meetings) == 1
        assert meetings[0]['subject'] == 'Sprint Planning'
    
    def test_calculate_meeting_duration(self, mock_graph_auth, sample_calendar_event):
        """Test meeting duration calculation"""
        client = TeamsClient(mock_graph_auth)
        
        duration = client.calculate_meeting_duration(sample_calendar_event)
        
        assert duration == 1.0  # 1 hour
    
    def test_calculate_meeting_duration_invalid_format(self, mock_graph_auth):
        """Test duration calculation with invalid event format"""
        client = TeamsClient(mock_graph_auth)
        
        invalid_event = {'subject': 'Test', 'start': {}, 'end': {}}
        
        duration = client.calculate_meeting_duration(invalid_event)
        
        assert duration == 0.0
    
    def test_filter_meetings(self, mock_graph_auth, sample_calendar_event):
        """Test meeting filtering"""
        client = TeamsClient(mock_graph_auth)
        
        # Create multiple meetings
        cancelled_meeting = sample_calendar_event.copy()
        cancelled_meeting['isCancelled'] = True
        cancelled_meeting['id'] = 'event-cancelled'
        
        non_teams_meeting = sample_calendar_event.copy()
        non_teams_meeting['isOnlineMeeting'] = False
        non_teams_meeting['id'] = 'event-offline'
        
        meetings = [sample_calendar_event, cancelled_meeting, non_teams_meeting]
        
        # Filter only Teams meetings
        filtered = client.filter_meetings(
            meetings,
            only_teams_meetings=True,
            exclude_cancelled=True
        )
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'event-123'
    
    def test_get_meeting_attendees(self, mock_graph_auth, sample_calendar_event):
        """Test extracting meeting attendees"""
        client = TeamsClient(mock_graph_auth)
        
        attendees = client.get_meeting_attendees(sample_calendar_event)
        
        assert len(attendees) == 2
        assert 'user1@example.com' in attendees
        assert 'user2@example.com' in attendees


class TestAzureDevOpsClient:
    """Tests for AzureDevOpsClient"""
    
    @pytest.fixture
    def mock_devops_auth(self, mock_env_vars):
        """Mock DevOps authentication provider"""
        return DevOpsAuthProvider.from_env()
    
    @patch('requests.Session.request')
    def test_get_work_item(self, mock_request, mock_devops_auth, sample_work_item):
        """Test getting work item by ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_work_item
        mock_request.return_value = mock_response
        
        client = AzureDevOpsClient(mock_devops_auth)
        work_item = client.get_work_item(123)
        
        assert work_item['id'] == 123
        assert work_item['fields']['System.Title'] == 'Sample Task'
    
    @patch('requests.Session.request')
    def test_get_work_item_not_found(self, mock_request, mock_devops_auth):
        """Test getting non-existent work item"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Work item not found'
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        client = AzureDevOpsClient(mock_devops_auth)
        
        work_item = client.get_work_item(999)
        
        assert work_item is None
    
    @patch('requests.Session.request')
    def test_update_work_item(self, mock_request, mock_devops_auth, sample_work_item):
        """Test updating work item"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_work_item
        mock_request.return_value = mock_response
        
        client = AzureDevOpsClient(mock_devops_auth)
        updates = [
            {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": 6.0}
        ]
        
        result = client.update_work_item(123, updates)
        
        assert result is True
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_update_completed_work(self, mock_request, mock_devops_auth, sample_work_item):
        """Test updating completed work field"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_work_item
        mock_request.return_value = mock_response
        
        client = AzureDevOpsClient(mock_devops_auth)
        result = client.update_completed_work(123, 7.5)
        
        assert result is True
        
        # Verify PATCH was called with correct payload
        call_args = mock_request.call_args
        assert call_args[0][0] == 'PATCH'
        json_data = call_args[1]['json']
        assert json_data[0]['op'] == 'add'
        assert json_data[0]['value'] == 7.5
    
    @patch('requests.Session.request')
    def test_query_work_items(self, mock_request, mock_devops_auth, sample_work_item):
        """Test querying work items with WIQL"""
        # Mock query result
        mock_query_response = Mock()
        mock_query_response.status_code = 200
        mock_query_response.json.return_value = {
            'workItems': [{'id': 123, 'url': 'https://dev.azure.com/test-org/_apis/wit/workItems/123'}]
        }
        
        # Mock work item detail
        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = sample_work_item
        
        mock_request.side_effect = [mock_query_response, mock_detail_response]
        
        client = AzureDevOpsClient(mock_devops_auth)
        wiql = "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"
        
        work_items = client.query_work_items(wiql)
        
        assert len(work_items) == 1
        assert work_items[0]['id'] == 123
    
    @patch('requests.Session.request')
    def test_get_work_items_by_iteration(self, mock_request, mock_devops_auth, sample_work_item):
        """Test getting work items by iteration path"""
        mock_query_response = Mock()
        mock_query_response.status_code = 200
        mock_query_response.json.return_value = {
            'workItems': [{'id': 123}]
        }
        
        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = sample_work_item
        
        mock_request.side_effect = [mock_query_response, mock_detail_response]
        
        client = AzureDevOpsClient(mock_devops_auth)
        work_items = client.get_work_items_by_iteration('Sprint 1')
        
        assert len(work_items) == 1
        assert work_items[0]['id'] == 123
    
    @patch('requests.Session.request')
    def test_get_projects(self, mock_request, mock_devops_auth):
        """Test getting list of projects"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {'id': 'proj-1', 'name': 'Project 1'},
                {'id': 'proj-2', 'name': 'Project 2'}
            ]
        }
        mock_request.return_value = mock_response
        
        client = AzureDevOpsClient(mock_devops_auth)
        projects = client.get_projects()
        
        assert len(projects) == 2
        assert projects[0]['name'] == 'Project 1'
    
    def test_get_scheduling_fields(self, mock_devops_auth, sample_work_item):
        """Test extracting scheduling fields from work item"""
        client = AzureDevOpsClient(mock_devops_auth)
        
        fields = client.get_scheduling_fields(sample_work_item)
        
        assert 'original_estimate' in fields
        assert 'completed_work' in fields
        assert 'remaining_work' in fields
        assert fields['original_estimate'] == 8.0
        assert fields['completed_work'] == 5.0
        assert fields['remaining_work'] == 3.0
    
    def test_get_scheduling_fields_missing(self, mock_devops_auth):
        """Test extracting scheduling fields when fields are missing"""
        client = AzureDevOpsClient(mock_devops_auth)
        
        incomplete_work_item = {
            'id': 456,
            'fields': {
                'System.Title': 'Incomplete Task'
            }
        }
        
        fields = client.get_scheduling_fields(incomplete_work_item)
        
        assert fields['original_estimate'] == 0.0
        assert fields['completed_work'] == 0.0
        assert fields['remaining_work'] == 0.0
