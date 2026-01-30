"""
Tests for WorkItemUpdater
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.core.work_item_updater import WorkItemUpdater
from src.clients.azure_devops_client import AzureDevOpsClient


@pytest.fixture
def mock_devops_client():
    """Mock Azure DevOps client"""
    client = Mock(spec=AzureDevOpsClient)
    return client


@pytest.fixture
def updater(mock_devops_client):
    """Create WorkItemUpdater instance"""
    return WorkItemUpdater(
        devops_client=mock_devops_client,
        dry_run=False,
        max_variance_threshold=2.0
    )


@pytest.fixture
def dry_run_updater(mock_devops_client):
    """Create WorkItemUpdater in dry-run mode"""
    return WorkItemUpdater(
        devops_client=mock_devops_client,
        dry_run=True
    )


class TestWorkItemUpdater:
    """Test cases for WorkItemUpdater"""
    
    def test_initialization(self, updater):
        """Test updater initialization"""
        assert updater.dry_run is False
        assert updater.max_variance_threshold == 2.0
        assert len(updater.audit_log) == 0
    
    def test_update_completed_work_success(self, updater, mock_devops_client):
        """Test successful work item update"""
        # Setup mock responses
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {
                'System.State': 'Active',
                'System.WorkItemType': 'Task'
            }
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = True
        mock_devops_client.update_completed_work.return_value = {
            'id': 123,
            'fields': {
                'Microsoft.VSTS.Scheduling.CompletedWork': 5.0
            }
        }
        
        # Perform update
        result = updater.update_completed_work(123, 5.0)
        
        # Assertions
        assert result['success'] is True
        assert result['updated'] is True
        assert result['work_item_id'] == 123
        assert result['completed_hours'] == 5.0
        assert result['previous_value'] == 0.0
        assert result['new_value'] == 5.0
        assert len(result['validation_errors']) == 0
        
        # Verify client was called
        mock_devops_client.update_completed_work.assert_called_once_with(
            123, 5.0, pytest.approx("Tiempo completado actualizado automáticamente a 5.0 horas por BV-Time-Logger", rel=0.1)
        )
    
    def test_update_completed_work_no_change_needed(self, updater, mock_devops_client):
        """Test update when value is already correct"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 5.0,
            'remaining_work': 3.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        result = updater.update_completed_work(123, 5.0)
        
        assert result['success'] is True
        assert result['updated'] is False
        assert result['previous_value'] == 5.0
        assert result['new_value'] == 5.0
        
        # Should not call update
        mock_devops_client.update_completed_work.assert_not_called()
    
    def test_update_completed_work_dry_run(self, dry_run_updater, mock_devops_client):
        """Test update in dry-run mode"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        result = dry_run_updater.update_completed_work(123, 5.0)
        
        assert result['success'] is True
        assert result['updated'] is False
        assert result.get('dry_run') is True
        
        # Should not call update in dry-run
        mock_devops_client.update_completed_work.assert_not_called()
    
    def test_validation_negative_hours(self, updater, mock_devops_client):
        """Test validation fails for negative hours"""
        validation = updater.validate_update(123, -5.0)
        
        assert validation['valid'] is False
        assert len(validation['errors']) > 0
        assert "cannot be negative" in validation['errors'][0]
    
    def test_validation_excessive_hours(self, updater, mock_devops_client):
        """Test validation fails for excessive hours"""
        validation = updater.validate_update(123, 1500.0)
        
        assert validation['valid'] is False
        assert "exceeds reasonable limit" in validation['errors'][0]
    
    def test_validation_exceeds_estimate(self, updater, mock_devops_client):
        """Test validation fails when hours exceed estimate threshold"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        # Try to update with 20 hours when estimate is 8 (2.5x ratio, exceeds 2.0 threshold)
        validation = updater.validate_update(123, 20.0)
        
        assert validation['valid'] is False
        assert any("exceeds" in err for err in validation['errors'])
    
    def test_validation_warning_high_variance(self, updater, mock_devops_client):
        """Test validation warns on high variance but doesn't fail"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        # 13 hours on 8 hour estimate = 1.625x (between 1.5 and 2.0)
        validation = updater.validate_update(123, 13.0)
        
        assert validation['valid'] is True
        assert len(validation['warnings']) > 0
    
    def test_validation_insufficient_permissions(self, updater, mock_devops_client):
        """Test validation fails without permissions"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = False
        
        validation = updater.validate_update(123, 5.0)
        
        assert validation['valid'] is False
        assert any("permissions" in err for err in validation['errors'])
    
    def test_update_with_force_skips_validation(self, updater, mock_devops_client):
        """Test forced update skips validation"""
        mock_devops_client.get_scheduling_fields.return_value = {
            'completed_work': 0.0
        }
        mock_devops_client.update_completed_work.return_value = {
            'id': 123
        }
        
        result = updater.update_completed_work(123, 5000.0, force=True)
        
        # Should succeed despite excessive hours
        assert result['success'] is True
        assert len(result['validation_errors']) == 0
    
    def test_update_batch(self, updater, mock_devops_client):
        """Test batch update"""
        mock_devops_client.get_work_item.return_value = {
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0,
            'remaining_work': 8.0
        }
        mock_devops_client.validate_permissions.return_value = True
        mock_devops_client.update_completed_work.return_value = {'id': 1}
        
        updates = [
            {'work_item_id': 123, 'completed_hours': 5.0},
            {'work_item_id': 124, 'completed_hours': 7.0},
            {'work_item_id': 125, 'completed_hours': 3.0}
        ]
        
        results = updater.update_batch(updates)
        
        assert results['total'] == 3
        assert results['successful'] == 3
        assert results['failed'] == 0
    
    def test_update_batch_stop_on_error(self, updater, mock_devops_client):
        """Test batch update stops on error"""
        # First one succeeds
        mock_devops_client.get_work_item.side_effect = [
            {'fields': {'System.State': 'Active'}},
            Exception("Permission denied")
        ]
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0
        }
        mock_devops_client.validate_permissions.return_value = True
        mock_devops_client.update_completed_work.return_value = {'id': 1}
        
        updates = [
            {'work_item_id': 123, 'completed_hours': 5.0},
            {'work_item_id': 124, 'completed_hours': 7.0},
            {'work_item_id': 125, 'completed_hours': 3.0}
        ]
        
        results = updater.update_batch(updates, stop_on_error=True)
        
        # Should stop after second item fails
        assert results['total'] == 3
        assert len(results['items']) == 2  # Only processed 2
    
    def test_audit_log(self, updater, mock_devops_client):
        """Test audit log creation"""
        mock_devops_client.get_work_item.return_value = {
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0
        }
        mock_devops_client.validate_permissions.return_value = True
        mock_devops_client.update_completed_work.return_value = {'id': 123}
        
        updater.update_completed_work(123, 5.0)
        
        audit_log = updater.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]['work_item_id'] == 123
        assert audit_log[0]['new_value'] == 5.0
        assert audit_log[0]['success'] is True
    
    def test_get_summary(self, updater, mock_devops_client):
        """Test summary statistics"""
        mock_devops_client.get_work_item.return_value = {
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0
        }
        mock_devops_client.validate_permissions.return_value = True
        mock_devops_client.update_completed_work.return_value = {'id': 1}
        
        # Perform several updates
        updater.update_completed_work(123, 5.0)
        updater.update_completed_work(124, 5.0)  # Will be skipped (already at 5.0 after first call mock)
        
        summary = updater.get_summary()
        
        assert summary['total_operations'] == 2
        assert summary['dry_run_mode'] is False
    
    def test_clear_audit_log(self, updater):
        """Test clearing audit log"""
        updater.audit_log = [{'test': 'entry'}]
        
        updater.clear_audit_log()
        
        assert len(updater.audit_log) == 0
