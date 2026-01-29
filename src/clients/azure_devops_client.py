"""
Azure DevOps Client - Work Items API integration
"""

import logging
from typing import List, Dict, Any, Optional, Union
from src.clients.base_client import BaseAPIClient
from src.auth.devops_auth import DevOpsAuthProvider

logger = logging.getLogger(__name__)


class AzureDevOpsClient(BaseAPIClient):
    """
    Client for Azure DevOps Work Items operations.
    Handles work item retrieval, updates, and queries.
    """
    
    API_VERSION = "7.1"
    
    def __init__(self, auth_provider: DevOpsAuthProvider, **kwargs):
        """
        Initialize Azure DevOps client.
        
        Args:
            auth_provider: DevOpsAuthProvider instance
            **kwargs: Additional arguments passed to BaseAPIClient
        """
        super().__init__(auth_provider, **kwargs)
        self.organization = auth_provider.organization
        self.project = auth_provider.project
        self.base_url = auth_provider.base_url
        
        logger.info(f"[DEVOPS] AzureDevOpsClient initialized for '{self.organization}'")
    
    def get_work_item(self, work_item_id: int, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get a specific work item by ID.
        
        Args:
            work_item_id: Work item ID
            fields: List of fields to retrieve (retrieves all if not specified)
            
        Returns:
            Work item dictionary
        """
        url = f"{self.base_url}/_apis/wit/workitems/{work_item_id}"
        
        params = {"api-version": self.API_VERSION}
        if fields:
            params["fields"] = ",".join(fields)
        
        logger.info(f"[DEVOPS] Retrieving work item #{work_item_id}")
        
        response = self.get(url, params=params)
        work_item = response.json()
        
        logger.debug(f"[DEVOPS] Work item type: {work_item.get('fields', {}).get('System.WorkItemType', 'N/A')}")
        
        return work_item
    
    def update_work_item(
        self,
        work_item_id: int,
        fields: Union[Dict[str, Any], List[Dict[str, Any]]],
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update work item fields using PATCH operation.

        Args:
            work_item_id: Work item ID
            fields: Dictionary of field paths and values OR list of PATCH operations
            comment: Optional comment to add to the work item

        Returns:
            Updated work item dictionary
        """
        url = f"{self.base_url}/_apis/wit/workitems/{work_item_id}"

        params = {"api-version": self.API_VERSION}

        # Build PATCH operations
        if isinstance(fields, list):
            # Already formatted as operations list
            operations = fields
        else:
            # Convert dict to operations list
            operations = []
            for field_path, value in fields.items():
                operations.append({
                    "op": "add",
                    "path": f"/fields/{field_path}",
                    "value": value
                })
        
        # Add comment if provided
        if comment:
            operations.append({
                "op": "add",
                "path": "/fields/System.History",
                "value": comment
            })
        
        logger.info(f"[DEVOPS] Updating work item #{work_item_id} ({len(operations)} operations)")
        
        # PATCH requires special content type
        headers = {"Content-Type": "application/json-patch+json"}
        
        response = self.patch(url, data=operations, params=params, headers=headers)
        updated_item = response.json()
        
        logger.info(f"[DEVOPS] Work item #{work_item_id} updated successfully")
        
        return updated_item
    
    def update_completed_work(
        self,
        work_item_id: int,
        completed_work: float,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the CompletedWork field of a work item.
        
        Args:
            work_item_id: Work item ID
            completed_work: Hours of completed work
            comment: Optional comment explaining the update
            
        Returns:
            Updated work item dictionary
        """
        fields = {
            "Microsoft.VSTS.Scheduling.CompletedWork": completed_work
        }
        
        default_comment = f"Completed work updated to {completed_work} hours by BV-Time-Logger"
        final_comment = comment or default_comment
        
        logger.info(f"[DEVOPS] Setting completed work for #{work_item_id} to {completed_work}h")
        
        return self.update_work_item(work_item_id, fields, final_comment)
    
    def query_work_items(
        self,
        wiql: str,
        project: Optional[str] = None,
        top: int = 200
    ) -> List[int]:
        """
        Execute WIQL (Work Item Query Language) query.
        
        Args:
            wiql: WIQL query string
            project: Project name (uses default if not specified)
            top: Maximum number of results
            
        Returns:
            List of work item IDs
        """
        project_name = project or self.project
        if not project_name:
            raise ValueError("No project specified and no default project configured")
        
        url = f"{self.base_url}/{project_name}/_apis/wit/wiql"
        
        params = {"api-version": self.API_VERSION}
        
        query_body = {
            "query": wiql
        }
        
        logger.info(f"[DEVOPS] Executing WIQL query in project '{project_name}'")
        logger.debug(f"[DEVOPS] WIQL: {wiql}")
        
        response = self.post(url, data=query_body, params=params)
        result = response.json()
        
        work_items = result.get('workItems', [])
        work_item_ids = [item['id'] for item in work_items[:top]]
        
        logger.info(f"[DEVOPS] Query returned {len(work_item_ids)} work items")
        
        return work_item_ids
    
    def get_work_items_by_iteration(
        self,
        iteration_path: str,
        project: Optional[str] = None,
        work_item_types: Optional[List[str]] = None
    ) -> List[int]:
        """
        Get work items for a specific iteration.
        
        Args:
            iteration_path: Iteration path (e.g., "Sprint 1")
            project: Project name (uses default if not specified)
            work_item_types: Filter by work item types (e.g., ["Task", "Bug"])
            
        Returns:
            List of work item IDs
        """
        project_name = project or self.project
        
        # Build WIQL query
        wiql = f"SELECT [System.Id] FROM WorkItems WHERE [System.IterationPath] = '{iteration_path}'"
        
        if work_item_types:
            types_filter = ", ".join(f"'{t}'" for t in work_item_types)
            wiql += f" AND [System.WorkItemType] IN ({types_filter})"
        
        return self.query_work_items(wiql, project_name)
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of all projects in the organization.
        
        Returns:
            List of project dictionaries
        """
        url = f"{self.base_url}/_apis/projects"
        
        params = {"api-version": self.API_VERSION}
        
        logger.info(f"[DEVOPS] Retrieving projects for organization '{self.organization}'")
        
        response = self.get(url, params=params)
        data = response.json()
        
        projects = data.get('value', [])
        logger.info(f"[DEVOPS] Found {len(projects)} projects")
        
        return projects
    
    def get_work_item_fields(self, work_item_id: int) -> Dict[str, Any]:
        """
        Get all fields from a work item.
        
        Args:
            work_item_id: Work item ID
            
        Returns:
            Dictionary of field values
        """
        work_item = self.get_work_item(work_item_id)
        return work_item.get('fields', {})
    
    def get_scheduling_fields(self, work_item_or_id: Union[int, Dict[str, Any]]) -> Dict[str, float]:
        """
        Get scheduling-related fields from a work item.
        
        Args:
            work_item_or_id: Work item dictionary or work item ID
            
        Returns:
            Dictionary with original_estimate, completed_work, remaining_work
        """
        # Get work item if ID was provided
        if isinstance(work_item_or_id, int):
            fields = self.get_work_item_fields(work_item_or_id)
        else:
            # Extract directly from provided work item
            fields = work_item_or_id.get('fields', {})
        
        return {
            'original_estimate': fields.get('Microsoft.VSTS.Scheduling.OriginalEstimate', 0.0) or 0.0,
            'completed_work': fields.get('Microsoft.VSTS.Scheduling.CompletedWork', 0.0) or 0.0,
            'remaining_work': fields.get('Microsoft.VSTS.Scheduling.RemainingWork', 0.0) or 0.0
        }
