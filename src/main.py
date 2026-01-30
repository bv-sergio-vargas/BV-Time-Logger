"""
Main Orchestrator - Coordinates the complete time logging workflow
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from src.auth.graph_auth import GraphAuthProvider
from src.auth.devops_auth import DevOpsAuthProvider
from src.clients.teams_client import TeamsClient
from src.clients.azure_devops_client import AzureDevOpsClient
from src.core.meeting_processor import MeetingProcessor
from src.core.meeting_matcher import MeetingMatcher
from src.core.work_item_updater import WorkItemUpdater
from src.core.conflict_resolver import ConflictResolver, ConflictStrategy
from src.core.time_comparator import TimeComparator
from src.reports.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class TimeLoggerOrchestrator:
    """
    Main orchestrator for the BV-Time-Logger system.
    Coordinates the complete workflow from meetings to reports.
    """
    
    def __init__(
        self,
        graph_auth: GraphAuthProvider,
        devops_auth: DevOpsAuthProvider,
        dry_run: bool = False,
        conflict_strategy: ConflictStrategy = ConflictStrategy.SKIP
    ):
        """
        Initialize orchestrator with authentication providers.
        
        Args:
            graph_auth: Microsoft Graph authentication provider
            devops_auth: Azure DevOps authentication provider
            dry_run: If True, preview changes without applying them
            conflict_strategy: Default strategy for conflict resolution
        """
        self.dry_run = dry_run
        self.conflict_strategy = conflict_strategy
        
        # Initialize clients
        self.teams_client = TeamsClient(graph_auth)
        self.devops_client = AzureDevOpsClient(devops_auth)
        
        # Initialize core modules
        self.meeting_processor = MeetingProcessor()
        self.meeting_matcher = MeetingMatcher()
        self.work_item_updater = WorkItemUpdater(
            self.devops_client,
            dry_run=dry_run
        )
        self.conflict_resolver = ConflictResolver(
            self.devops_client,
            default_strategy=conflict_strategy
        )
        self.time_comparator = TimeComparator()
        self.report_generator = ReportGenerator()
        
        # Execution state
        self.last_run: Optional[datetime] = None
        self.execution_log: List[Dict[str, Any]] = []
        
        logger.info(
            f"[ORCHESTRATOR] Initialized (dry_run={dry_run}, "
            f"conflict_strategy={conflict_strategy.value})"
        )
    
    def run(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        user_emails: Optional[List[str]] = None,
        project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete time logging workflow.
        
        Args:
            start_date: Start date for meetings (defaults to yesterday)
            end_date: End date for meetings (defaults to today)
            user_emails: List of user emails to process (None = all)
            project: Azure DevOps project name (None = default)
            
        Returns:
            Dictionary with execution results
        """
        execution_id = datetime.utcnow().isoformat()
        
        logger.info(f"[ORCHESTRATOR] Starting execution {execution_id}")
        
        # Set default date range (yesterday to today)
        if start_date is None:
            start_date = date.today() - timedelta(days=1)
        if end_date is None:
            end_date = date.today()
        
        result = {
            'execution_id': execution_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'dry_run': self.dry_run,
            'success': False,
            'steps': {},
            'errors': [],
            'summary': {}
        }
        
        try:
            # Step 1: Get meetings from Teams
            logger.info("[ORCHESTRATOR] Step 1: Retrieving meetings from Teams")
            meetings_result = self._get_meetings(start_date, end_date, user_emails)
            result['steps']['get_meetings'] = meetings_result
            
            if not meetings_result['success']:
                raise Exception("Failed to retrieve meetings")
            
            # Step 2: Get work items from Azure DevOps
            logger.info("[ORCHESTRATOR] Step 2: Retrieving work items from Azure DevOps")
            work_items_result = self._get_work_items(project)
            result['steps']['get_work_items'] = work_items_result
            
            if not work_items_result['success']:
                raise Exception("Failed to retrieve work items")
            
            # Step 3: Match meetings to work items
            logger.info("[ORCHESTRATOR] Step 3: Matching meetings to work items")
            matching_result = self._match_meetings_to_work_items(
                meetings_result['meetings'],
                work_items_result['work_items']
            )
            result['steps']['match_meetings'] = matching_result
            
            # Step 4: Calculate time comparisons
            logger.info("[ORCHESTRATOR] Step 4: Comparing actual vs estimated time")
            comparison_result = self._compare_times(matching_result['matched'])
            result['steps']['compare_times'] = comparison_result
            
            # Step 5: Resolve conflicts and update work items
            logger.info("[ORCHESTRATOR] Step 5: Updating work items")
            update_result = self._update_work_items(comparison_result['comparisons'])
            result['steps']['update_work_items'] = update_result
            
            # Step 6: Generate reports
            logger.info("[ORCHESTRATOR] Step 6: Generating reports")
            reports_result = self._generate_reports(
                comparison_result['comparisons'],
                comparison_result['statistics'],
                start_date
            )
            result['steps']['generate_reports'] = reports_result
            
            # Build summary
            result['summary'] = {
                'total_meetings': meetings_result.get('count', 0),
                'matched_meetings': matching_result.get('matched_count', 0),
                'unmatched_meetings': matching_result.get('unmatched_count', 0),
                'work_items_updated': update_result.get('successful', 0),
                'work_items_failed': update_result.get('failed', 0),
                'reports_generated': len(reports_result.get('files', {}))
            }
            
            result['success'] = True
            self.last_run = datetime.utcnow()
            
            logger.info(
                f"[ORCHESTRATOR] Execution completed successfully: "
                f"{result['summary']['work_items_updated']} work items updated"
            )
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Execution failed: {e}", exc_info=True)
            result['errors'].append(str(e))
            result['success'] = False
        
        # Log execution
        self.execution_log.append(result)
        
        return result
    
    def _get_meetings(
        self,
        start_date: date,
        end_date: date,
        user_emails: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get meetings from Microsoft Teams.
        
        Args:
            start_date: Start date
            end_date: End date
            user_emails: Optional list of user emails
            
        Returns:
            Result dictionary with meetings
        """
        result = {
            'success': False,
            'meetings': [],
            'count': 0
        }
        
        try:
            # Get calendar events
            events = self.teams_client.get_calendar_events(
                start_date=start_date,
                end_date=end_date
            )
            
            # Process meetings
            processed_meetings = self.meeting_processor.process_meetings(events)
            
            # Filter by user if specified
            if user_emails:
                filtered = []
                for meeting in processed_meetings:
                    for email in user_emails:
                        if self.meeting_processor.filter_by_attendee(
                            [meeting],
                            email
                        ):
                            filtered.append(meeting)
                            break
                processed_meetings = filtered
            
            result['meetings'] = processed_meetings
            result['count'] = len(processed_meetings)
            result['success'] = True
            
            logger.info(f"[ORCHESTRATOR] Retrieved {result['count']} meetings")
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error getting meetings: {e}")
            result['error'] = str(e)
        
        return result
    
    def _get_work_items(
        self,
        project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get work items from Azure DevOps.
        
        Args:
            project: Project name (optional)
            
        Returns:
            Result dictionary with work items
        """
        result = {
            'success': False,
            'work_items': [],
            'count': 0
        }
        
        try:
            # Query for active work items
            wiql = """
            SELECT [System.Id], [System.Title], [System.State], 
                   [System.AssignedTo], [System.WorkItemType]
            FROM WorkItems 
            WHERE [System.State] NOT IN ('Removed', 'Closed')
            """
            
            work_item_ids = self.devops_client.query_work_items(wiql, project)
            
            if work_item_ids:
                # Get full work item details in batch
                work_items = self.devops_client.get_work_items_batch(work_item_ids)
                result['work_items'] = work_items
                result['count'] = len(work_items)
            
            result['success'] = True
            
            logger.info(f"[ORCHESTRATOR] Retrieved {result['count']} work items")
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error getting work items: {e}")
            result['error'] = str(e)
        
        return result
    
    def _match_meetings_to_work_items(
        self,
        meetings: List[Dict[str, Any]],
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Match meetings to work items.
        
        Args:
            meetings: List of processed meetings
            work_items: List of work items
            
        Returns:
            Result dictionary with matching results
        """
        result = {
            'matched': [],
            'unmatched': [],
            'matched_count': 0,
            'unmatched_count': 0
        }
        
        try:
            # Perform batch matching
            matching_result = self.meeting_matcher.match_meetings_batch(
                meetings,
                work_items
            )
            
            result['matched'] = matching_result['matched']
            result['unmatched'] = matching_result['unmatched']
            result['matched_count'] = matching_result['statistics']['matched_count']
            result['unmatched_count'] = matching_result['statistics']['unmatched_count']
            
            logger.info(
                f"[ORCHESTRATOR] Matched {result['matched_count']} meetings, "
                f"{result['unmatched_count']} unmatched"
            )
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error matching meetings: {e}")
            result['error'] = str(e)
        
        return result
    
    def _compare_times(
        self,
        matched_meetings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare actual time vs estimated time.
        
        Args:
            matched_meetings: List of matched meeting-workitem pairs
            
        Returns:
            Result dictionary with comparisons
        """
        result = {
            'comparisons': [],
            'statistics': {}
        }
        
        try:
            # Aggregate hours by work item
            work_item_hours = {}
            for match in matched_meetings:
                work_item_id = match['work_item']['id']
                meeting_duration = match['meeting'].get('duration_hours', 0)
                
                if work_item_id not in work_item_hours:
                    work_item_hours[work_item_id] = {
                        'work_item_id': work_item_id,
                        'title': match['work_item']['fields'].get('System.Title', ''),
                        'estimated_hours': self.devops_client.get_scheduling_fields(
                            match['work_item']
                        )['original_estimate'],
                        'actual_hours': 0,
                        'meeting_hours': 0,
                        'execution_hours': 0
                    }
                
                work_item_hours[work_item_id]['actual_hours'] += meeting_duration
                work_item_hours[work_item_id]['meeting_hours'] += meeting_duration
            
            # Perform batch comparison
            comparison_result = self.time_comparator.compare_batch(
                list(work_item_hours.values())
            )
            
            result['comparisons'] = comparison_result['items']
            result['statistics'] = comparison_result['statistics']
            
            logger.info(
                f"[ORCHESTRATOR] Compared {len(result['comparisons'])} work items"
            )
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error comparing times: {e}")
            result['error'] = str(e)
        
        return result
    
    def _update_work_items(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update work items with actual hours.
        
        Args:
            comparisons: List of time comparisons
            
        Returns:
            Result dictionary with update results
        """
        result = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'items': []
        }
        
        try:
            updates = []
            
            for comparison in comparisons:
                work_item_id = comparison['work_item_id']
                actual_hours = comparison['actual_hours']
                
                # Detect conflicts
                conflict_info = self.conflict_resolver.detect_conflicts(
                    work_item_id,
                    actual_hours
                )
                
                # Resolve conflicts if any
                if conflict_info['has_conflicts']:
                    resolution = self.conflict_resolver.resolve_conflict(
                        conflict_info,
                        self.conflict_strategy
                    )
                    
                    if not resolution['resolved']:
                        logger.warning(
                            f"[ORCHESTRATOR] Skipping work item #{work_item_id} "
                            f"due to unresolved conflicts"
                        )
                        result['skipped'] += 1
                        continue
                    
                    # Use resolved value
                    actual_hours = resolution['final_value']
                
                # Prepare update
                updates.append({
                    'work_item_id': work_item_id,
                    'completed_hours': actual_hours,
                    'comment': f"Actualización automática: {actual_hours} horas "
                              f"(reuniones: {comparison.get('meeting_hours', 0)}h)"
                })
            
            # Perform batch update
            if updates:
                update_result = self.work_item_updater.update_batch(updates)
                
                result['successful'] = update_result['successful']
                result['failed'] = update_result['failed']
                result['skipped'] += update_result['skipped']
                result['items'] = update_result['items']
            
            logger.info(
                f"[ORCHESTRATOR] Updated {result['successful']} work items, "
                f"{result['failed']} failed, {result['skipped']} skipped"
            )
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error updating work items: {e}")
            result['error'] = str(e)
        
        return result
    
    def _generate_reports(
        self,
        comparisons: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        report_date: date
    ) -> Dict[str, Any]:
        """
        Generate reports.
        
        Args:
            comparisons: List of time comparisons
            statistics: Aggregate statistics
            report_date: Date for the report
            
        Returns:
            Result dictionary with report file paths
        """
        result = {
            'files': {},
            'success': False
        }
        
        try:
            # Generate daily report
            files = self.report_generator.generate_daily_report(
                report_date=report_date,
                comparisons=comparisons,
                statistics=statistics
            )
            
            result['files'] = files
            result['success'] = True
            
            logger.info(
                f"[ORCHESTRATOR] Generated reports: "
                f"CSV={files.get('csv')}, JSON={files.get('json')}"
            )
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error generating reports: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """
        Get execution log.
        
        Returns:
            List of execution results
        """
        return self.execution_log.copy()
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        """
        Get last execution result.
        
        Returns:
            Last execution dictionary or None
        """
        return self.execution_log[-1] if self.execution_log else None
    
    def clear_execution_log(self):
        """
        Clear execution log.
        """
        logger.info(f"[ORCHESTRATOR] Clearing execution log ({len(self.execution_log)} entries)")
        self.execution_log.clear()
