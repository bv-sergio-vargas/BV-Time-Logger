"""
Tests for JobScheduler
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from apscheduler.events import JobExecutionEvent, EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from src.scheduler.job_scheduler import JobScheduler


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator"""
    orchestrator = Mock()
    orchestrator.run.return_value = {
        'success': True,
        'meetings_processed': 5,
        'work_items_updated': 3
    }
    return orchestrator


@pytest.fixture
def scheduler(mock_orchestrator):
    """Create scheduler with mock orchestrator"""
    return JobScheduler(mock_orchestrator)


def test_scheduler_initialization(mock_orchestrator):
    """Test scheduler initializes correctly"""
    scheduler = JobScheduler(mock_orchestrator)
    
    assert scheduler.orchestrator == mock_orchestrator
    assert scheduler.scheduler is not None
    assert len(scheduler.jobs) == 0
    assert len(scheduler.execution_history) == 0


def test_schedule_daily_sync(scheduler):
    """Test scheduling daily sync"""
    scheduler.schedule_daily_sync(hour=9, minute=30)
    
    assert 'daily_sync' in scheduler.jobs
    assert scheduler.jobs['daily_sync']['type'] == 'daily'
    assert scheduler.jobs['daily_sync']['schedule'] == '09:30'
    assert scheduler.jobs['daily_sync']['enabled'] is True


def test_schedule_daily_sync_validates_time(scheduler):
    """Test daily sync validates time parameters"""
    with pytest.raises(ValueError, match="hour must be between 0 and 23"):
        scheduler.schedule_daily_sync(hour=25, minute=0)
    
    with pytest.raises(ValueError, match="minute must be between 0 and 59"):
        scheduler.schedule_daily_sync(hour=0, minute=60)


def test_schedule_interval_sync_hours(scheduler):
    """Test scheduling interval sync with hours"""
    scheduler.schedule_interval_sync(hours=2)
    
    assert 'interval_sync' in scheduler.jobs
    assert scheduler.jobs['interval_sync']['type'] == 'interval'
    assert '2 hours' in scheduler.jobs['interval_sync']['schedule']


def test_schedule_interval_sync_minutes(scheduler):
    """Test scheduling interval sync with minutes"""
    scheduler.schedule_interval_sync(minutes=30)
    
    assert 'interval_sync' in scheduler.jobs
    assert '30 minutes' in scheduler.jobs['interval_sync']['schedule']


def test_schedule_interval_sync_validates_parameters(scheduler):
    """Test interval sync validates parameters"""
    with pytest.raises(ValueError, match="Must specify either hours or minutes"):
        scheduler.schedule_interval_sync()
    
    with pytest.raises(ValueError, match="hours must be positive"):
        scheduler.schedule_interval_sync(hours=-1)
    
    with pytest.raises(ValueError, match="minutes must be positive"):
        scheduler.schedule_interval_sync(minutes=0)


def test_schedule_custom_cron(scheduler):
    """Test scheduling with custom cron expression"""
    cron_expr = "0 9 * * 1-5"  # 9 AM on weekdays
    
    scheduler.schedule_custom(cron_expr, job_id='weekday_sync')
    
    assert 'weekday_sync' in scheduler.jobs
    assert scheduler.jobs['weekday_sync']['type'] == 'custom'
    assert scheduler.jobs['weekday_sync']['schedule'] == cron_expr


def test_schedule_custom_validates_cron(scheduler):
    """Test custom schedule validates cron expression"""
    with pytest.raises(ValueError, match="Invalid cron expression"):
        scheduler.schedule_custom("invalid cron")


def test_start_scheduler(scheduler):
    """Test starting scheduler"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    
    scheduler.start()
    
    assert scheduler.scheduler.running is True


def test_stop_scheduler(scheduler):
    """Test stopping scheduler"""
    scheduler.start()
    scheduler.stop(wait=False)
    
    assert scheduler.scheduler.running is False


def test_pause_job(scheduler):
    """Test pausing a job"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.start()
    
    scheduler.pause_job('daily_sync')
    
    assert scheduler.jobs['daily_sync']['enabled'] is False


def test_pause_job_not_found(scheduler):
    """Test pausing non-existent job raises error"""
    with pytest.raises(ValueError, match="Job not found"):
        scheduler.pause_job('nonexistent')


def test_resume_job(scheduler):
    """Test resuming a paused job"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.start()
    scheduler.pause_job('daily_sync')
    
    scheduler.resume_job('daily_sync')
    
    assert scheduler.jobs['daily_sync']['enabled'] is True


def test_remove_job(scheduler):
    """Test removing a job"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.start()
    
    scheduler.remove_job('daily_sync')
    
    assert 'daily_sync' not in scheduler.jobs


def test_run_job_now(scheduler, mock_orchestrator):
    """Test running a job immediately"""
    scheduler.schedule_daily_sync(hour=23, minute=59)  # Far future
    scheduler.start()
    
    # Mock the scheduler's modify_job to verify it was called
    with patch.object(scheduler.scheduler, 'modify_job') as mock_modify:
        scheduler.run_job_now('daily_sync')
        mock_modify.assert_called_once()


def test_get_jobs(scheduler):
    """Test getting all jobs"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.schedule_interval_sync(hours=2)
    
    jobs = scheduler.get_jobs()
    
    assert len(jobs) == 2
    assert 'daily_sync' in jobs
    assert 'interval_sync' in jobs
    assert 'next_run_time' in jobs['daily_sync']


def test_get_jobs_empty(scheduler):
    """Test getting jobs when none scheduled"""
    jobs = scheduler.get_jobs()
    
    assert len(jobs) == 0


def test_get_execution_history(scheduler):
    """Test getting execution history"""
    # Add some fake history
    scheduler.execution_history = [
        {
            'job_id': 'daily_sync',
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'exception': None
        },
        {
            'job_id': 'daily_sync',
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'success': False,
            'exception': 'Test error'
        }
    ]
    
    history = scheduler.get_execution_history(limit=10)
    
    assert len(history) == 2
    assert history[0]['success'] is True
    assert history[1]['exception'] == 'Test error'


def test_get_execution_history_limit(scheduler):
    """Test execution history respects limit"""
    # Add 15 entries
    for i in range(15):
        scheduler.execution_history.append({
            'job_id': 'test',
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'exception': None
        })
    
    history = scheduler.get_execution_history(limit=5)
    
    assert len(history) == 5


def test_health_check_not_running(scheduler):
    """Test health check when scheduler not running"""
    health = scheduler.health_check()
    
    assert health['status'] == 'stopped'
    assert health['running'] is False
    assert health['total_jobs'] == 0
    assert health['last_execution'] is None


def test_health_check_running(scheduler):
    """Test health check when scheduler running"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.start()
    
    health = scheduler.health_check()
    
    assert health['status'] == 'running'
    assert health['running'] is True
    assert health['total_jobs'] == 1
    assert health['enabled_jobs'] == 1


def test_health_check_with_paused_jobs(scheduler):
    """Test health check with paused jobs"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.schedule_interval_sync(hours=2)
    scheduler.start()
    scheduler.pause_job('daily_sync')
    
    health = scheduler.health_check()
    
    assert health['total_jobs'] == 2
    assert health['enabled_jobs'] == 1
    assert health['paused_jobs'] == 1


def test_health_check_with_execution_history(scheduler):
    """Test health check includes last execution"""
    scheduler.execution_history = [
        {
            'job_id': 'daily_sync',
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'exception': None
        }
    ]
    
    health = scheduler.health_check()
    
    assert health['last_execution'] is not None
    assert health['last_execution']['success'] is True


def test_job_executed_listener_success(scheduler):
    """Test event listener handles successful execution"""
    event = Mock()
    event.job_id = 'daily_sync'
    event.exception = None
    
    scheduler._job_executed_listener(event)
    
    assert len(scheduler.execution_history) == 1
    assert scheduler.execution_history[0]['success'] is True
    assert scheduler.execution_history[0]['exception'] is None


def test_job_executed_listener_error(scheduler):
    """Test event listener handles failed execution"""
    event = Mock()
    event.job_id = 'daily_sync'
    event.exception = Exception("Test error")
    
    scheduler._job_executed_listener(event)
    
    assert len(scheduler.execution_history) == 1
    assert scheduler.execution_history[0]['success'] is False
    assert 'Test error' in scheduler.execution_history[0]['exception']


def test_execution_history_limit_100(scheduler):
    """Test execution history is limited to 100 entries"""
    # Simulate 150 executions
    for i in range(150):
        event = Mock()
        event.job_id = 'test'
        event.exception = None
        scheduler._job_executed_listener(event)
    
    assert len(scheduler.execution_history) == 100


def test_multiple_schedules_coexist(scheduler):
    """Test multiple schedule types can coexist"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.schedule_interval_sync(hours=2)
    scheduler.schedule_custom("0 12 * * *", job_id='noon_sync')
    
    assert len(scheduler.jobs) == 3
    assert 'daily_sync' in scheduler.jobs
    assert 'interval_sync' in scheduler.jobs
    assert 'noon_sync' in scheduler.jobs


def test_replace_existing_job(scheduler):
    """Test scheduling same job ID replaces previous"""
    scheduler.schedule_daily_sync(hour=9, minute=0)
    scheduler.schedule_daily_sync(hour=10, minute=0)
    
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs['daily_sync']['schedule'] == '10:00'
