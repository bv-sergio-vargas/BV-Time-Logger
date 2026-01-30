"""
Tests for TimeLoggerOrchestrator
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from src.main import TimeLoggerOrchestrator


@pytest.fixture
def mock_clients():
    """Mock all API clients"""
    with patch('src.main.TeamsClient') as mock_teams, \
         patch('src.main.AzureDevOpsClient') as mock_devops:
        
        yield {
            'teams': mock_teams.return_value,
            'devops': mock_devops.return_value
        }


@pytest.fixture
def mock_processors():
    """Mock all processors"""
    with patch('src.main.MeetingProcessor') as mock_processor, \
         patch('src.main.MeetingMatcher') as mock_matcher, \
         patch('src.main.TimeComparator') as mock_comparator, \
         patch('src.main.WorkItemUpdater') as mock_updater, \
         patch('src.main.ReportGenerator') as mock_reporter:
        
        yield {
            'processor': mock_processor.return_value,
            'matcher': mock_matcher.return_value,
            'comparator': mock_comparator.return_value,
            'updater': mock_updater.return_value,
            'reporter': mock_reporter.return_value
        }


@pytest.fixture
def orchestrator(mock_clients, mock_processors):
    """Create orchestrator with mocked dependencies"""
    orch = TimeLoggerOrchestrator()
    return orch


def test_orchestrator_initialization():
    """Test orchestrator initializes with default config"""
    with patch('src.main.TeamsClient'), \
         patch('src.main.AzureDevOpsClient'):
        
        orch = TimeLoggerOrchestrator()
        
        assert orch.dry_run is False
        assert orch.conflict_strategy == 'SKIP'
        assert orch.last_run is None
        assert len(orch.execution_log) == 0


def test_orchestrator_initialization_with_config():
    """Test orchestrator initializes with custom config"""
    with patch('src.main.TeamsClient'), \
         patch('src.main.AzureDevOpsClient'):
        
        orch = TimeLoggerOrchestrator(dry_run=True, conflict_strategy='OVERRIDE')
        
        assert orch.dry_run is True
        assert orch.conflict_strategy == 'OVERRIDE'


def test_run_success_flow(orchestrator, mock_clients, mock_processors):
    """Test successful end-to-end execution"""
    # Setup mock data
    mock_meetings = [
        {'id': 'meeting1', 'subject': 'Team Meeting', 'duration_minutes': 60}
    ]
    mock_processed = [
        {
            'meeting_id': 'meeting1',
            'subject': 'Team Meeting',
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(hours=1),
            'duration_minutes': 60,
            'attendees': ['user1@example.com']
        }
    ]
    mock_work_items = [
        {'id': 123, 'fields': {'System.Title': 'Task 1'}}
    ]
    mock_matches = [
        {'meeting': mock_processed[0], 'work_item_id': 123, 'confidence': 0.9}
    ]
    mock_comparisons = [
        {
            'work_item_id': 123,
            'estimated_hours': 8.0,
            'actual_hours': 7.5,
            'variance_hours': -0.5,
            'variance_percent': -6.25,
            'deviation_level': 'none',
            'recommendation': 'Within acceptable range'
        }
    ]
    
    mock_clients['teams'].get_meetings.return_value = mock_meetings
    mock_processors['processor'].process_meetings.return_value = mock_processed
    mock_clients['devops'].get_work_items_batch.return_value = mock_work_items
    mock_processors['matcher'].match_meetings_to_work_items.return_value = mock_matches
    mock_processors['comparator'].compare_work_items.return_value = mock_comparisons
    mock_processors['updater'].update_work_items_batch.return_value = {'updated': 1, 'failed': 0, 'skipped': 0}
    mock_processors['reporter'].generate_daily_report_csv.return_value = 'report.csv'
    
    # Execute
    result = orchestrator.run(
        start_date=date.today() - timedelta(days=7),
        end_date=date.today()
    )
    
    # Verify
    assert result['success'] is True
    assert result['meetings_processed'] == 1
    assert result['work_items_updated'] == 1
    assert len(result['reports']) > 0
    assert len(result['errors']) == 0


def test_run_with_user_filter(orchestrator, mock_clients):
    """Test run with specific user IDs"""
    user_ids = ['user1@example.com', 'user2@example.com']
    
    orchestrator.run(
        start_date=date.today(),
        end_date=date.today(),
        user_ids=user_ids
    )
    
    # Verify user filter was applied
    call_args = mock_clients['teams'].get_meetings.call_args
    assert 'user_ids' in call_args[1] or user_ids in call_args[0]


def test_run_dry_run_mode(orchestrator, mock_clients, mock_processors):
    """Test dry-run mode doesn't apply changes"""
    orchestrator.dry_run = True
    
    mock_clients['teams'].get_meetings.return_value = []
    mock_processors['processor'].process_meetings.return_value = []
    
    result = orchestrator.run(
        start_date=date.today(),
        end_date=date.today()
    )
    
    # Verify no update was called
    mock_processors['updater'].update_work_items_batch.assert_not_called()


def test_run_handles_empty_meetings(orchestrator, mock_clients, mock_processors):
    """Test handling of no meetings found"""
    mock_clients['teams'].get_meetings.return_value = []
    mock_processors['processor'].process_meetings.return_value = []
    
    result = orchestrator.run(
        start_date=date.today(),
        end_date=date.today()
    )
    
    assert result['success'] is True
    assert result['meetings_processed'] == 0
    assert result['work_items_updated'] == 0


def test_run_handles_api_error(orchestrator, mock_clients):
    """Test handling of API errors"""
    mock_clients['teams'].get_meetings.side_effect = Exception("API Error")
    
    result = orchestrator.run(
        start_date=date.today(),
        end_date=date.today()
    )
    
    assert result['success'] is False
    assert len(result['errors']) > 0
    assert 'API Error' in str(result['errors'][0])


def test_run_handles_partial_failure(orchestrator, mock_clients, mock_processors):
    """Test handling of partial failures in update step"""
    mock_meetings = [{'id': 'meeting1'}]
    mock_processed = [
        {
            'meeting_id': 'meeting1',
            'subject': 'Meeting',
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(hours=1),
            'duration_minutes': 60,
            'attendees': ['user1@example.com']
        }
    ]
    
    mock_clients['teams'].get_meetings.return_value = mock_meetings
    mock_processors['processor'].process_meetings.return_value = mock_processed
    mock_clients['devops'].get_work_items_batch.return_value = []
    mock_processors['matcher'].match_meetings_to_work_items.return_value = []
    
    result = orchestrator.run(
        start_date=date.today(),
        end_date=date.today()
    )
    
    assert result['success'] is True
    assert result['meetings_processed'] == 1


def test_execution_log_tracking(orchestrator, mock_clients, mock_processors):
    """Test execution log is properly tracked"""
    mock_clients['teams'].get_meetings.return_value = []
    mock_processors['processor'].process_meetings.return_value = []
    
    orchestrator.run(
        start_date=date.today(),
        end_date=date.today()
    )
    
    log = orchestrator.get_execution_log()
    assert len(log) > 0
    
    last_exec = orchestrator.get_last_execution()
    assert last_exec is not None
    assert 'timestamp' in last_exec
    assert 'result' in last_exec


def test_clear_execution_log(orchestrator):
    """Test clearing execution log"""
    orchestrator.execution_log = [{'timestamp': datetime.now().isoformat(), 'result': {}}]
    
    orchestrator.clear_execution_log()
    
    assert len(orchestrator.execution_log) == 0


def test_get_meetings_with_date_range(orchestrator, mock_clients):
    """Test _get_meetings applies correct date range"""
    start = date(2024, 1, 1)
    end = date(2024, 1, 31)
    
    mock_clients['teams'].get_meetings.return_value = []
    
    orchestrator._get_meetings(start, end)
    
    call_args = mock_clients['teams'].get_meetings.call_args
    assert start in call_args[0] or 'start_date' in call_args[1]
    assert end in call_args[0] or 'end_date' in call_args[1]


def test_match_meetings_to_work_items(orchestrator, mock_processors):
    """Test meeting matching logic"""
    processed = [
        {
            'meeting_id': 'meeting1',
            'subject': 'WI-123: Review',
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(hours=1),
            'duration_minutes': 60,
            'attendees': ['user1@example.com']
        }
    ]
    work_items = [
        {'id': 123, 'fields': {'System.Title': 'Code Review'}}
    ]
    
    mock_processors['matcher'].match_meetings_to_work_items.return_value = [
        {'meeting': processed[0], 'work_item_id': 123, 'confidence': 0.9}
    ]
    
    matches = orchestrator._match_meetings_to_work_items(processed, work_items)
    
    assert len(matches) == 1
    assert matches[0]['work_item_id'] == 123


def test_compare_times_aggregation(orchestrator, mock_processors):
    """Test time comparison and aggregation"""
    matches = [
        {'meeting': Mock(duration_minutes=60), 'work_item_id': 123},
        {'meeting': Mock(duration_minutes=30), 'work_item_id': 123}
    ]
    work_items = [
        {
            'id': 123,
            'fields': {
                'Microsoft.VSTS.Scheduling.OriginalEstimate': 2.0,
                'Microsoft.VSTS.Scheduling.CompletedWork': 0.0
            }
        }
    ]
    
    mock_processors['comparator'].compare_work_items.return_value = []
    
    comparisons = orchestrator._compare_times(matches, work_items)
    
    mock_processors['comparator'].compare_work_items.assert_called_once()


def test_update_work_items_with_conflict_strategy(orchestrator, mock_processors):
    """Test work item update uses configured conflict strategy"""
    comparisons = [
        {
            'work_item_id': 123,
            'estimated_hours': 8.0,
            'actual_hours': 7.5,
            'variance_hours': -0.5,
            'variance_percent': -6.25,
            'deviation_level': 'none',
            'recommendation': 'OK'
        }
    ]
    work_items = [
        {
            'id': 123,
            'fields': {
                'Microsoft.VSTS.Scheduling.CompletedWork': 0.0
            }
        }
    ]
    
    orchestrator.conflict_strategy = 'OVERRIDE'
    mock_processors['updater'].update_work_items_batch.return_value = {
        'updated': 1, 'failed': 0, 'skipped': 0
    }
    
    orchestrator._update_work_items(comparisons, work_items)
    
    call_args = mock_processors['updater'].update_work_items_batch.call_args
    assert call_args[1]['conflict_strategy'] == 'OVERRIDE'
