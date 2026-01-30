"""
Work Item Updater - Updates completed work in Azure DevOps work items
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.clients.azure_devops_client import AzureDevOpsClient

logger = logging.getLogger(__name__)


class WorkItemUpdater:
    """
    Handles updating work items with completed work hours.
    Includes validation, audit logging, and dry-run mode.
    """
    
    def __init__(
        self,
        devops_client: AzureDevOpsClient,
        dry_run: bool = False,
        max_variance_threshold: float = 2.0
    ):
        """
        Initialize work item updater.
        
        Args:
            devops_client: Azure DevOps client instance
            dry_run: If True, preview changes without applying them
            max_variance_threshold: Maximum allowed ratio of completed/estimated
                                   (e.g., 2.0 = 200% of estimate)
        """
        self.devops_client = devops_client
        self.dry_run = dry_run
        self.max_variance_threshold = max_variance_threshold
        self.audit_log: List[Dict[str, Any]] = []
        
        logger.info(f"[UPDATER] Initialized (dry_run={dry_run}, max_variance={max_variance_threshold})")
    
    def update_completed_work(
        self,
        work_item_id: int,
        completed_hours: float,
        comment: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Update completed work hours for a work item.
        
        Args:
            work_item_id: Work item ID
            completed_hours: Hours to set as completed work
            comment: Optional comment explaining the update
            force: Skip validation checks if True
            
        Returns:
            Dictionary with update result and details
        """
        logger.info(f"[UPDATER] Processing work item #{work_item_id} - {completed_hours}h")
        
        result = {
            'work_item_id': work_item_id,
            'completed_hours': completed_hours,
            'success': False,
            'updated': False,
            'validation_errors': [],
            'warnings': [],
            'previous_value': None,
            'new_value': None
        }
        
        try:
            # Validate update unless forced
            if not force:
                validation_result = self.validate_update(work_item_id, completed_hours)
                
                if not validation_result['valid']:
                    result['validation_errors'] = validation_result['errors']
                    result['warnings'] = validation_result.get('warnings', [])
                    logger.warning(f"[UPDATER] Validation failed for #{work_item_id}: {validation_result['errors']}")
                    return result
                
                result['warnings'] = validation_result.get('warnings', [])
            
            # Get current value before update
            current_fields = self.devops_client.get_scheduling_fields(work_item_id)
            result['previous_value'] = current_fields['completed_work']
            
            # Check if update is needed
            if result['previous_value'] == completed_hours:
                logger.info(f"[UPDATER] Work item #{work_item_id} already has {completed_hours}h - skipping")
                result['success'] = True
                result['updated'] = False
                result['new_value'] = completed_hours
                return result
            
            # Dry run mode - preview only
            if self.dry_run:
                logger.info(f"[UPDATER] DRY RUN: Would update #{work_item_id} from {result['previous_value']}h to {completed_hours}h")
                result['success'] = True
                result['updated'] = False
                result['new_value'] = completed_hours
                result['dry_run'] = True
                return result
            
            # Perform actual update
            update_comment = comment or f"Tiempo completado actualizado automáticamente a {completed_hours} horas por BV-Time-Logger"
            
            updated_item = self.devops_client.update_completed_work(
                work_item_id,
                completed_hours,
                update_comment
            )
            
            result['success'] = True
            result['updated'] = True
            result['new_value'] = completed_hours
            result['updated_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"[UPDATER] Successfully updated #{work_item_id} from {result['previous_value']}h to {completed_hours}h")
            
            # Log to audit trail
            self.create_audit_log(work_item_id, result)
            
        except Exception as e:
            logger.error(f"[UPDATER] Error updating work item #{work_item_id}: {e}")
            result['validation_errors'].append(f"Update failed: {str(e)}")
        
        return result
    
    def validate_update(
        self,
        work_item_id: int,
        completed_hours: float
    ) -> Dict[str, Any]:
        """
        Validate that an update is safe to perform.
        
        Args:
            work_item_id: Work item ID
            completed_hours: Proposed completed hours
            
        Returns:
            Dictionary with validation result
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Basic validation
        if completed_hours < 0:
            validation['valid'] = False
            validation['errors'].append("Completed hours cannot be negative")
            return validation
        
        if completed_hours > 1000:
            validation['valid'] = False
            validation['errors'].append(f"Completed hours ({completed_hours}) exceeds reasonable limit (1000h)")
            return validation
        
        try:
            # Get work item details
            work_item = self.devops_client.get_work_item(work_item_id)
            fields = work_item.get('fields', {})
            
            # Check work item state
            state = fields.get('System.State', '')
            if state in ['Removed', 'Closed']:
                validation['warnings'].append(f"Work item is in '{state}' state")
            
            # Get scheduling fields
            scheduling = self.devops_client.get_scheduling_fields(work_item)
            original_estimate = scheduling['original_estimate']
            
            # Validate against estimate
            if original_estimate > 0:
                variance = completed_hours / original_estimate
                
                if variance > self.max_variance_threshold:
                    validation['valid'] = False
                    validation['errors'].append(
                        f"Completed hours ({completed_hours}h) exceeds {self.max_variance_threshold}x "
                        f"the original estimate ({original_estimate}h)"
                    )
                elif variance > 1.5:
                    validation['warnings'].append(
                        f"Completed hours ({completed_hours}h) is {variance:.1f}x "
                        f"the original estimate ({original_estimate}h)"
                    )
            else:
                validation['warnings'].append("No original estimate defined for this work item")
            
            # Check permissions
            if not self.devops_client.validate_permissions(work_item_id):
                validation['valid'] = False
                validation['errors'].append(f"Insufficient permissions to update work item #{work_item_id}")
        
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Validation error: {str(e)}")
        
        return validation
    
    def update_batch(
        self,
        updates: List[Dict[str, Any]],
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Update multiple work items in batch.
        
        Args:
            updates: List of dicts with 'work_item_id' and 'completed_hours'
            stop_on_error: If True, stop processing on first error
            
        Returns:
            Summary of batch update results
        """
        logger.info(f"[UPDATER] Processing batch of {len(updates)} work items")
        
        results = {
            'total': len(updates),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'items': []
        }
        
        for update in updates:
            work_item_id = update['work_item_id']
            completed_hours = update['completed_hours']
            comment = update.get('comment')
            
            result = self.update_completed_work(work_item_id, completed_hours, comment)
            results['items'].append(result)
            
            if result['success']:
                if result['updated']:
                    results['successful'] += 1
                else:
                    results['skipped'] += 1
            else:
                results['failed'] += 1
                
                if stop_on_error:
                    logger.error(f"[UPDATER] Stopping batch processing due to error on #{work_item_id}")
                    break
        
        logger.info(
            f"[UPDATER] Batch complete: {results['successful']} successful, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results
    
    def create_audit_log(
        self,
        work_item_id: int,
        update_result: Dict[str, Any]
    ):
        """
        Create audit log entry for an update.
        
        Args:
            work_item_id: Work item ID
            update_result: Result dictionary from update operation
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'work_item_id': work_item_id,
            'previous_value': update_result.get('previous_value'),
            'new_value': update_result.get('new_value'),
            'success': update_result['success'],
            'updated': update_result['updated'],
            'dry_run': self.dry_run,
            'errors': update_result.get('validation_errors', []),
            'warnings': update_result.get('warnings', [])
        }
        
        self.audit_log.append(log_entry)
        
        logger.debug(f"[UPDATER] Audit log entry created for work item #{work_item_id}")
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        Get complete audit log.
        
        Returns:
            List of audit log entries
        """
        return self.audit_log.copy()
    
    def clear_audit_log(self):
        """
        Clear the audit log.
        """
        logger.info(f"[UPDATER] Clearing audit log ({len(self.audit_log)} entries)")
        self.audit_log.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics from audit log.
        
        Returns:
            Summary dictionary
        """
        total = len(self.audit_log)
        successful = sum(1 for entry in self.audit_log if entry['success'] and entry['updated'])
        failed = sum(1 for entry in self.audit_log if not entry['success'])
        skipped = sum(1 for entry in self.audit_log if entry['success'] and not entry['updated'])
        
        return {
            'total_operations': total,
            'successful_updates': successful,
            'failed_updates': failed,
            'skipped_updates': skipped,
            'dry_run_mode': self.dry_run
        }
