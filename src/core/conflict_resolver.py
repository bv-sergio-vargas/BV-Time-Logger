"""
Conflict Resolver - Handles conflicts when updating work items
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from src.clients.azure_devops_client import AzureDevOpsClient

logger = logging.getLogger(__name__)


class ConflictStrategy(Enum):
    """
    Strategies for resolving conflicts when updating work items.
    """
    OVERRIDE = "override"  # Replace existing value with new value
    ADD = "add"  # Add new value to existing value
    SKIP = "skip"  # Keep existing value, skip update
    FAIL = "fail"  # Raise error on conflict


class ConflictType(Enum):
    """
    Types of conflicts that can occur.
    """
    MANUAL_UPDATE = "manual_update"  # Manual update detected since last sync
    VALUE_MISMATCH = "value_mismatch"  # Current value doesn't match expected
    OVERBUDGET = "overbudget"  # Update would exceed original estimate significantly
    PERMISSION_DENIED = "permission_denied"  # Insufficient permissions
    WORK_ITEM_LOCKED = "work_item_locked"  # Work item is in locked state


class ConflictResolver:
    """
    Detects and resolves conflicts when updating work items.
    """
    
    def __init__(
        self,
        devops_client: AzureDevOpsClient,
        default_strategy: ConflictStrategy = ConflictStrategy.SKIP
    ):
        """
        Initialize conflict resolver.
        
        Args:
            devops_client: Azure DevOps client instance
            default_strategy: Default strategy for resolving conflicts
        """
        self.devops_client = devops_client
        self.default_strategy = default_strategy
        self.conflict_log: List[Dict[str, Any]] = []
        
        logger.info(f"[RESOLVER] Initialized with default strategy: {default_strategy.value}")
    
    def detect_conflicts(
        self,
        work_item_id: int,
        proposed_hours: float,
        last_known_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect conflicts before updating a work item.
        
        Args:
            work_item_id: Work item ID
            proposed_hours: Hours we want to set
            last_known_hours: Last known completed hours (from previous sync)
            
        Returns:
            Dictionary with conflict detection results
        """
        logger.info(f"[RESOLVER] Checking conflicts for work item #{work_item_id}")
        
        result = {
            'work_item_id': work_item_id,
            'has_conflicts': False,
            'conflicts': [],
            'current_hours': None,
            'proposed_hours': proposed_hours,
            'last_known_hours': last_known_hours,
            'can_proceed': True
        }
        
        try:
            # Get current work item state
            work_item = self.devops_client.get_work_item(work_item_id)
            fields = work_item.get('fields', {})
            
            # Get current completed work
            scheduling = self.devops_client.get_scheduling_fields(work_item)
            current_hours = scheduling['completed_work']
            result['current_hours'] = current_hours
            
            # Check for manual update conflict
            if last_known_hours is not None and current_hours != last_known_hours:
                conflict = {
                    'type': ConflictType.MANUAL_UPDATE.value,
                    'message': f"Manual update detected: value changed from {last_known_hours}h to {current_hours}h",
                    'severity': 'high',
                    'current_value': current_hours,
                    'expected_value': last_known_hours
                }
                result['conflicts'].append(conflict)
                result['has_conflicts'] = True
                logger.warning(f"[RESOLVER] Manual update detected for #{work_item_id}")
            
            # Check for value mismatch (when no last_known_hours)
            elif current_hours > 0 and last_known_hours is None:
                conflict = {
                    'type': ConflictType.VALUE_MISMATCH.value,
                    'message': f"Work item already has {current_hours}h completed work",
                    'severity': 'medium',
                    'current_value': current_hours
                }
                result['conflicts'].append(conflict)
                result['has_conflicts'] = True
            
            # Check if proposed update significantly exceeds estimate
            original_estimate = scheduling['original_estimate']
            if original_estimate > 0:
                variance_ratio = proposed_hours / original_estimate
                
                if variance_ratio > 2.5:
                    conflict = {
                        'type': ConflictType.OVERBUDGET.value,
                        'message': f"Proposed hours ({proposed_hours}h) is {variance_ratio:.1f}x the estimate ({original_estimate}h)",
                        'severity': 'high',
                        'proposed_value': proposed_hours,
                        'estimate': original_estimate,
                        'variance_ratio': variance_ratio
                    }
                    result['conflicts'].append(conflict)
                    result['has_conflicts'] = True
            
            # Check work item state
            state = fields.get('System.State', '')
            if state in ['Removed', 'Deleted']:
                conflict = {
                    'type': ConflictType.WORK_ITEM_LOCKED.value,
                    'message': f"Work item is in '{state}' state",
                    'severity': 'critical',
                    'state': state
                }
                result['conflicts'].append(conflict)
                result['has_conflicts'] = True
                result['can_proceed'] = False
            
            # Check permissions
            if not self.devops_client.validate_permissions(work_item_id):
                conflict = {
                    'type': ConflictType.PERMISSION_DENIED.value,
                    'message': "Insufficient permissions to update work item",
                    'severity': 'critical'
                }
                result['conflicts'].append(conflict)
                result['has_conflicts'] = True
                result['can_proceed'] = False
        
        except Exception as e:
            logger.error(f"[RESOLVER] Error detecting conflicts for #{work_item_id}: {e}")
            result['error'] = str(e)
            result['can_proceed'] = False
        
        return result
    
    def resolve_conflict(
        self,
        conflict_info: Dict[str, Any],
        strategy: Optional[ConflictStrategy] = None
    ) -> Dict[str, Any]:
        """
        Resolve a conflict according to the specified strategy.
        
        Args:
            conflict_info: Conflict information from detect_conflicts()
            strategy: Resolution strategy (uses default if not specified)
            
        Returns:
            Dictionary with resolution result
        """
        strategy = strategy or self.default_strategy
        work_item_id = conflict_info['work_item_id']
        
        logger.info(f"[RESOLVER] Resolving conflicts for #{work_item_id} using strategy: {strategy.value}")
        
        resolution = {
            'work_item_id': work_item_id,
            'strategy': strategy.value,
            'resolved': False,
            'action_taken': None,
            'final_value': None,
            'conflicts_resolved': []
        }
        
        # If no conflicts or can't proceed, handle appropriately
        if not conflict_info['has_conflicts']:
            resolution['resolved'] = True
            resolution['action_taken'] = 'no_conflicts'
            resolution['final_value'] = conflict_info['proposed_hours']
            return resolution
        
        if not conflict_info['can_proceed']:
            resolution['resolved'] = False
            resolution['action_taken'] = 'blocked'
            resolution['message'] = "Cannot proceed due to critical conflicts"
            return resolution
        
        current_hours = conflict_info['current_hours']
        proposed_hours = conflict_info['proposed_hours']
        
        try:
            if strategy == ConflictStrategy.OVERRIDE:
                # Replace with proposed value
                resolution['final_value'] = proposed_hours
                resolution['action_taken'] = 'override'
                resolution['message'] = f"Overriding {current_hours}h with {proposed_hours}h"
                resolution['resolved'] = True
                
            elif strategy == ConflictStrategy.ADD:
                # Add proposed to current
                final_value = current_hours + proposed_hours
                resolution['final_value'] = final_value
                resolution['action_taken'] = 'add'
                resolution['message'] = f"Adding {proposed_hours}h to existing {current_hours}h = {final_value}h"
                resolution['resolved'] = True
                
            elif strategy == ConflictStrategy.SKIP:
                # Keep current value, don't update
                resolution['final_value'] = current_hours
                resolution['action_taken'] = 'skip'
                resolution['message'] = f"Keeping existing value {current_hours}h, skipping update"
                resolution['resolved'] = True
                
            elif strategy == ConflictStrategy.FAIL:
                # Fail on conflict
                resolution['resolved'] = False
                resolution['action_taken'] = 'fail'
                resolution['message'] = f"Failing due to conflict (strategy: FAIL)"
                
            resolution['conflicts_resolved'] = [c['type'] for c in conflict_info['conflicts']]
            
            # Log resolution
            self._log_resolution(conflict_info, resolution)
            
        except Exception as e:
            logger.error(f"[RESOLVER] Error resolving conflict for #{work_item_id}: {e}")
            resolution['resolved'] = False
            resolution['error'] = str(e)
        
        return resolution
    
    def resolve_batch(
        self,
        conflicts: List[Dict[str, Any]],
        strategy: Optional[ConflictStrategy] = None
    ) -> Dict[str, Any]:
        """
        Resolve multiple conflicts in batch.
        
        Args:
            conflicts: List of conflict information dictionaries
            strategy: Resolution strategy
            
        Returns:
            Summary of batch resolution results
        """
        logger.info(f"[RESOLVER] Resolving {len(conflicts)} conflicts in batch")
        
        results = {
            'total': len(conflicts),
            'resolved': 0,
            'failed': 0,
            'blocked': 0,
            'items': []
        }
        
        for conflict in conflicts:
            resolution = self.resolve_conflict(conflict, strategy)
            results['items'].append(resolution)
            
            if resolution['resolved']:
                results['resolved'] += 1
            elif resolution.get('action_taken') == 'blocked':
                results['blocked'] += 1
            else:
                results['failed'] += 1
        
        logger.info(
            f"[RESOLVER] Batch resolution complete: {results['resolved']} resolved, "
            f"{results['failed']} failed, {results['blocked']} blocked"
        )
        
        return results
    
    def get_recommended_strategy(
        self,
        conflict_info: Dict[str, Any]
    ) -> ConflictStrategy:
        """
        Get recommended strategy for a conflict based on its characteristics.
        
        Args:
            conflict_info: Conflict information
            
        Returns:
            Recommended ConflictStrategy
        """
        if not conflict_info['can_proceed']:
            return ConflictStrategy.FAIL
        
        if not conflict_info['has_conflicts']:
            return ConflictStrategy.OVERRIDE
        
        # Check conflict types
        conflict_types = [c['type'] for c in conflict_info['conflicts']]
        
        # If manual update detected, recommend skip to preserve manual work
        if ConflictType.MANUAL_UPDATE.value in conflict_types:
            logger.info("[RESOLVER] Recommending SKIP due to manual update")
            return ConflictStrategy.SKIP
        
        # If overbudget, recommend skip
        if ConflictType.OVERBUDGET.value in conflict_types:
            logger.info("[RESOLVER] Recommending SKIP due to overbudget")
            return ConflictStrategy.SKIP
        
        # For value mismatch, consider adding
        if ConflictType.VALUE_MISMATCH.value in conflict_types:
            current = conflict_info.get('current_hours', 0)
            proposed = conflict_info.get('proposed_hours', 0)
            
            # If proposed is larger, override
            if proposed > current:
                logger.info("[RESOLVER] Recommending OVERRIDE (proposed > current)")
                return ConflictStrategy.OVERRIDE
            else:
                logger.info("[RESOLVER] Recommending ADD (proposed <= current)")
                return ConflictStrategy.ADD
        
        # Default to skip for safety
        return ConflictStrategy.SKIP
    
    def _log_resolution(
        self,
        conflict_info: Dict[str, Any],
        resolution: Dict[str, Any]
    ):
        """
        Log conflict resolution for audit trail.
        
        Args:
            conflict_info: Conflict information
            resolution: Resolution result
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'work_item_id': conflict_info['work_item_id'],
            'conflicts': conflict_info['conflicts'],
            'strategy': resolution['strategy'],
            'action_taken': resolution['action_taken'],
            'resolved': resolution['resolved'],
            'current_hours': conflict_info.get('current_hours'),
            'proposed_hours': conflict_info.get('proposed_hours'),
            'final_value': resolution.get('final_value')
        }
        
        self.conflict_log.append(log_entry)
        logger.debug(f"[RESOLVER] Resolution logged for work item #{conflict_info['work_item_id']}")
    
    def get_conflict_log(self) -> List[Dict[str, Any]]:
        """
        Get complete conflict resolution log.
        
        Returns:
            List of conflict log entries
        """
        return self.conflict_log.copy()
    
    def clear_conflict_log(self):
        """
        Clear the conflict log.
        """
        logger.info(f"[RESOLVER] Clearing conflict log ({len(self.conflict_log)} entries)")
        self.conflict_log.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics from conflict log.
        
        Returns:
            Summary dictionary
        """
        total = len(self.conflict_log)
        resolved = sum(1 for entry in self.conflict_log if entry['resolved'])
        failed = total - resolved
        
        # Count by strategy
        strategy_counts = {}
        for entry in self.conflict_log:
            strategy = entry['strategy']
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'total_conflicts': total,
            'resolved': resolved,
            'failed': failed,
            'strategies_used': strategy_counts
        }
