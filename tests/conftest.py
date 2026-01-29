"""
Pytest configuration and shared fixtures
"""
import os
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from typing import Dict, Any


def create_mock_response(status_code: int, json_data: Any = None, text: str = "") -> Mock:
    """Helper to create properly configured mock HTTP response"""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.content = text.encode() if text else b''
    
    if json_data is not None:
        mock_response.json.return_value = json_data
    
    # Configure raise_for_status behavior
    if 400 <= status_code < 600:
        from requests.exceptions import HTTPError
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
    else:
        mock_response.raise_for_status.return_value = None
    
    return mock_response


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    env_vars = {
        'AZURE_DEVOPS_ORGANIZATION': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat-token-12345',
        'AZURE_DEVOPS_PROJECT': 'Test Project',
        'AZURE_AD_CLIENT_ID': 'test-client-id',
        'AZURE_AD_CLIENT_SECRET': 'test-client-secret',
        'AZURE_AD_TENANT_ID': 'test-tenant-id',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def sample_work_item():
    """Sample Azure DevOps work item"""
    return {
        "id": 123,
        "rev": 1,
        "fields": {
            "System.WorkItemType": "Task",
            "System.Title": "Sample Task",
            "System.State": "Active",
            "System.AssignedTo": {
                "displayName": "John Doe",
                "uniqueName": "john.doe@example.com"
            },
            "Microsoft.VSTS.Scheduling.OriginalEstimate": 8.0,
            "Microsoft.VSTS.Scheduling.CompletedWork": 5.0,
            "Microsoft.VSTS.Scheduling.RemainingWork": 3.0,
        },
        "url": "https://dev.azure.com/test-org/_apis/wit/workItems/123"
    }


@pytest.fixture
def sample_calendar_event():
    """Sample Microsoft Graph calendar event"""
    start_time = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    return {
        "id": "event-123",
        "subject": "Team Standup",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": "user1@example.com",
                    "name": "User One"
                },
                "type": "required"
            },
            {
                "emailAddress": {
                    "address": "user2@example.com",
                    "name": "User Two"
                },
                "type": "optional"
            }
        ],
        "organizer": {
            "emailAddress": {
                "address": "organizer@example.com",
                "name": "Organizer"
            }
        },
        "isCancelled": False,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }


@pytest.fixture
def sample_online_meeting():
    """Sample Microsoft Graph online meeting"""
    return {
        "id": "meeting-123",
        "subject": "Sprint Planning",
        "startDateTime": datetime.utcnow().isoformat() + "Z",
        "endDateTime": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        "participants": {
            "attendees": [
                {
                    "identity": {
                        "user": {
                            "displayName": "User One",
                            "id": "user-id-1"
                        }
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_user_info():
    """Sample Microsoft Graph user info"""
    return {
        "id": "user-123",
        "displayName": "Test User",
        "mail": "test.user@example.com",
        "userPrincipalName": "test.user@example.com",
        "officeLocation": "Bogotá",
        "preferredLanguage": "es-CO"
    }
