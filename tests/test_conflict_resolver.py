"""
Tests for ConflictResolver
"""

import pytest
from unittest.mock import Mock
from src.core.conflict_resolver import ConflictResolver, ConflictStrategy, ConflictType
from src.clients.azure_devops_client import AzureDevOpsClient


@pytest.fixture
def mock_devops_client():
    """Mock Azure DevOps client"""
    client = Mock(spec=AzureDevOpsClient)
    return client


@pytest.fixture
def resolver(mock_devops_client):
    """Create ConflictResolver instance"""
    return ConflictResolver(
        devops_client=mock_devops_client,
        default_strategy=ConflictStrategy.SKIP
    )


class TestConflictResolver:
    """Test cases for ConflictResolver"""
    
    def test_initialization(self, resolver):
        """Test resolver initialization"""
        assert resolver.default_strategy == ConflictStrategy.SKIP
        assert len(resolver.conflict_log) == 0
    
    def test_detect_no_conflicts(self, resolver, mock_devops_client):
        """Test detection when no conflicts exist"""
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
        
        result = resolver.detect_conflicts(123, 5.0, last_known_hours=0.0)
        
        assert result['has_conflicts'] is False
        assert len(result['conflicts']) == 0
        assert result['can_proceed'] is True
    
    def test_detect_manual_update_conflict(self, resolver, mock_devops_client):
        """Test detection of manual update conflict"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 3.0,  # Current value
            'remaining_work': 5.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        # Last known was 0, now it's 3 - manual update detected
        result = resolver.detect_conflicts(123, 5.0, last_known_hours=0.0)
        
        assert result['has_conflicts'] is True
        assert result['current_hours'] == 3.0
        assert any(c['type'] == ConflictType.MANUAL_UPDATE.value for c in result['conflicts'])
    
    def test_detect_value_mismatch(self, resolver, mock_devops_client):
        """Test detection of value mismatch"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 2.0,
            'remaining_work': 6.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        # No last_known_hours, but work item already has hours
        result = resolver.detect_conflicts(123, 5.0, last_known_hours=None)
        
        assert result['has_conflicts'] is True
        assert any(c['type'] == ConflictType.VALUE_MISMATCH.value for c in result['conflicts'])
    
    def test_detect_overbudget_conflict(self, resolver, mock_devops_client):
        """Test detection of overbudget conflict"""
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
        
        # Proposing 25 hours on 8 hour estimate (3.125x ratio)
        result = resolver.detect_conflicts(123, 25.0)
        
        assert result['has_conflicts'] is True
        assert any(c['type'] == ConflictType.OVERBUDGET.value for c in result['conflicts'])
    
    def test_detect_locked_work_item(self, resolver, mock_devops_client):
        """Test detection of locked work item"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Removed'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0
        }
        mock_devops_client.validate_permissions.return_value = True
        
        result = resolver.detect_conflicts(123, 5.0)
        
        assert result['has_conflicts'] is True
        assert result['can_proceed'] is False
        assert any(c['type'] == ConflictType.WORK_ITEM_LOCKED.value for c in result['conflicts'])
    
    def test_detect_permission_denied(self, resolver, mock_devops_client):
        """Test detection of permission issues"""
        mock_devops_client.get_work_item.return_value = {
            'id': 123,
            'fields': {'System.State': 'Active'}
        }
        mock_devops_client.get_scheduling_fields.return_value = {
            'original_estimate': 8.0,
            'completed_work': 0.0
        }
        mock_devops_client.validate_permissions.return_value = False
        
        result = resolver.detect_conflicts(123, 5.0)
        
        assert result['has_conflicts'] is True
        assert result['can_proceed'] is False
        assert any(c['type'] == ConflictType.PERMISSION_DENIED.value for c in result['conflicts'])
    
    def test_resolve_override_strategy(self, resolver):
        """Test conflict resolution with OVERRIDE strategy"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 3.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        resolution = resolver.resolve_conflict(conflict_info, ConflictStrategy.OVERRIDE)
        
        assert resolution['resolved'] is True
        assert resolution['strategy'] == ConflictStrategy.OVERRIDE.value
        assert resolution['final_value'] == 5.0
        assert resolution['action_taken'] == 'override'
    
    def test_resolve_add_strategy(self, resolver):
        """Test conflict resolution with ADD strategy"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 3.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        resolution = resolver.resolve_conflict(conflict_info, ConflictStrategy.ADD)
        
        assert resolution['resolved'] is True
        assert resolution['strategy'] == ConflictStrategy.ADD.value
        assert resolution['final_value'] == 8.0  # 3.0 + 5.0
        assert resolution['action_taken'] == 'add'
    
    def test_resolve_skip_strategy(self, resolver):
        """Test conflict resolution with SKIP strategy"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 3.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        resolution = resolver.resolve_conflict(conflict_info, ConflictStrategy.SKIP)
        
        assert resolution['resolved'] is True
        assert resolution['strategy'] == ConflictStrategy.SKIP.value
        assert resolution['final_value'] == 3.0  # Keep current
        assert resolution['action_taken'] == 'skip'
    
    def test_resolve_fail_strategy(self, resolver):
        """Test conflict resolution with FAIL strategy"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 3.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        resolution = resolver.resolve_conflict(conflict_info, ConflictStrategy.FAIL)
        
        assert resolution['resolved'] is False
        assert resolution['strategy'] == ConflictStrategy.FAIL.value
        assert resolution['action_taken'] == 'fail'
    
    def test_resolve_no_conflicts(self, resolver):
        """Test resolution when no conflicts exist"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': False,
            'can_proceed': True,
            'current_hours': 0.0,
            'proposed_hours': 5.0,
            'conflicts': []
        }
        
        resolution = resolver.resolve_conflict(conflict_info)
        
        assert resolution['resolved'] is True
        assert resolution['action_taken'] == 'no_conflicts'
        assert resolution['final_value'] == 5.0
    
    def test_resolve_blocked(self, resolver):
        """Test resolution when blocked"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': False,
            'current_hours': 0.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.PERMISSION_DENIED.value}
            ]
        }
        
        resolution = resolver.resolve_conflict(conflict_info)
        
        assert resolution['resolved'] is False
        assert resolution['action_taken'] == 'blocked'
    
    def test_resolve_batch(self, resolver):
        """Test batch conflict resolution"""
        conflicts = [
            {
                'work_item_id': 123,
                'has_conflicts': True,
                'can_proceed': True,
                'current_hours': 3.0,
                'proposed_hours': 5.0,
                'conflicts': [{'type': ConflictType.VALUE_MISMATCH.value}]
            },
            {
                'work_item_id': 124,
                'has_conflicts': True,
                'can_proceed': True,
                'current_hours': 2.0,
                'proposed_hours': 4.0,
                'conflicts': [{'type': ConflictType.VALUE_MISMATCH.value}]
            }
        ]
        
        results = resolver.resolve_batch(conflicts, ConflictStrategy.OVERRIDE)
        
        assert results['total'] == 2
        assert results['resolved'] == 2
        assert results['failed'] == 0
    
    def test_get_recommended_strategy_manual_update(self, resolver):
        """Test recommended strategy for manual update"""
        conflict_info = {
            'has_conflicts': True,
            'can_proceed': True,
            'conflicts': [
                {'type': ConflictType.MANUAL_UPDATE.value}
            ]
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.SKIP
    
    def test_get_recommended_strategy_overbudget(self, resolver):
        """Test recommended strategy for overbudget"""
        conflict_info = {
            'has_conflicts': True,
            'can_proceed': True,
            'conflicts': [
                {'type': ConflictType.OVERBUDGET.value}
            ]
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.SKIP
    
    def test_get_recommended_strategy_value_mismatch_override(self, resolver):
        """Test recommended strategy for value mismatch (proposed > current)"""
        conflict_info = {
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 2.0,
            'proposed_hours': 5.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.OVERRIDE
    
    def test_get_recommended_strategy_value_mismatch_add(self, resolver):
        """Test recommended strategy for value mismatch (proposed <= current)"""
        conflict_info = {
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 5.0,
            'proposed_hours': 2.0,
            'conflicts': [
                {'type': ConflictType.VALUE_MISMATCH.value}
            ]
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.ADD
    
    def test_get_recommended_strategy_no_conflicts(self, resolver):
        """Test recommended strategy when no conflicts"""
        conflict_info = {
            'has_conflicts': False,
            'can_proceed': True,
            'conflicts': []
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.OVERRIDE
    
    def test_get_recommended_strategy_blocked(self, resolver):
        """Test recommended strategy when blocked"""
        conflict_info = {
            'has_conflicts': True,
            'can_proceed': False,
            'conflicts': []
        }
        
        strategy = resolver.get_recommended_strategy(conflict_info)
        
        assert strategy == ConflictStrategy.FAIL
    
    def test_conflict_log(self, resolver):
        """Test conflict logging"""
        conflict_info = {
            'work_item_id': 123,
            'has_conflicts': True,
            'can_proceed': True,
            'current_hours': 3.0,
            'proposed_hours': 5.0,
            'conflicts': [{'type': ConflictType.VALUE_MISMATCH.value}]
        }
        
        resolver.resolve_conflict(conflict_info, ConflictStrategy.OVERRIDE)
        
        log = resolver.get_conflict_log()
        assert len(log) == 1
        assert log[0]['work_item_id'] == 123
        assert log[0]['resolved'] is True
    
    def test_get_summary(self, resolver):
        """Test summary statistics"""
        conflicts = [
            {
                'work_item_id': 123,
                'has_conflicts': True,
                'can_proceed': True,
                'current_hours': 3.0,
                'proposed_hours': 5.0,
                'conflicts': [{'type': ConflictType.VALUE_MISMATCH.value}]
            },
            {
                'work_item_id': 124,
                'has_conflicts': True,
                'can_proceed': True,  # Changed to can_proceed=True
                'current_hours': 2.0,
                'proposed_hours': 4.0,
                'conflicts': [{'type': ConflictType.VALUE_MISMATCH.value}]
            }
        ]
        
        resolver.resolve_batch(conflicts)
        
        summary = resolver.get_summary()
        
        assert summary['total_conflicts'] == 2
        assert summary['resolved'] == 2  # Both resolved now
        assert summary['failed'] == 0
    
    def test_clear_conflict_log(self, resolver):
        """Test clearing conflict log"""
        resolver.conflict_log = [{'test': 'entry'}]
        
        resolver.clear_conflict_log()
        
        assert len(resolver.conflict_log) == 0
