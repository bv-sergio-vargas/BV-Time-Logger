"""
Azure DevOps API Authentication Provider
PAT (Personal Access Token) authentication for Azure DevOps REST API
"""

import os
import base64
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DevOpsAuthProvider:
    """
    Handles PAT-based authentication for Azure DevOps API.
    Personal Access Tokens provide simple, secure authentication for Azure DevOps.
    """
    
    def __init__(self, organization: str, pat: str, project: str = None):
        """
        Initialize Azure DevOps authentication provider.
        
        Args:
            organization: Azure DevOps organization name
            pat: Personal Access Token with required permissions
            project: Optional default project name
        """
        self.organization = organization
        self.pat = pat
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}"
        
        # Pre-encode PAT for Basic authentication
        self._auth_header = self._encode_pat(pat)
        
        logger.info(f"[AUTH] DevOpsAuthProvider initialized for organization '{organization}'")
        if project:
            logger.info(f"[AUTH] Default project: '{project}'")
    
    def _encode_pat(self, pat: Optional[str] = None) -> str:
        """
        Encode PAT for Basic authentication header.
        Azure DevOps uses Basic auth with empty username and PAT as password.
        
        Args:
            pat: Personal Access Token
            
        Returns:
            Base64-encoded authentication string
        """
        # Format: ":{PAT}" (empty username, PAT as password)
        credentials = f":{pat}"
        encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
        return encoded
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for Azure DevOps API requests.
        
        Returns:
            Dictionary with Authorization and Content-Type headers
        """
        return {
            "Authorization": f"Basic {self._auth_header}",
            "Content-Type": "application/json"
        }
    
    def get_project_url(self, project: str = None) -> str:
        """
        Get base URL for a specific project.
        
        Args:
            project: Project name (uses default if not provided)
            
        Returns:
            Full project URL
            
        Raises:
            ValueError: If no project specified and no default configured
        """
        project_name = project or self.project
        if not project_name:
            raise ValueError("No project specified and no default project configured")
        
        return f"{self.base_url}/{project_name}"
    
    def get_api_url(self, endpoint: Optional[str] = None, api_version: str = "7.1") -> str:
        """
        Build full API URL with version.
        
        Args:
            endpoint: API endpoint (e.g., "_apis/wit/workitems/123") or None for base
            api_version: Azure DevOps API version (default: 7.1)
            
        Returns:
            Full API URL with version parameter
        """
        if endpoint is None:
            base = self.base_url
        else:
            # Ensure endpoint starts with /
            if not endpoint.startswith('/'):
                endpoint = f"/{endpoint}"
            
            base = f"{self.base_url}{endpoint}"
        
        # Add API version query parameter
        separator = '&' if '?' in base else '?'
        return f"{base}{separator}api-version={api_version}"
    
    def validate_permissions(self) -> bool:
        """
        Validate that PAT has required permissions.
        Makes a simple API call to check authentication.
        
        Returns:
            True if authentication is valid, False otherwise
        """
        import requests
        
        try:
            url = self.get_api_url("_apis/projects")
            headers = self.get_auth_headers()
            
            logger.info(f"[AUTH] Validating PAT permissions for '{self.organization}'")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                projects = response.json().get('value', [])
                logger.info(f"[AUTH] PAT validation successful. Access to {len(projects)} project(s)")
                return True
            elif response.status_code == 401:
                logger.error("[AUTH] PAT validation failed: Unauthorized (401)")
                return False
            else:
                logger.warning(f"[AUTH] PAT validation returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[AUTH] Exception during PAT validation: {str(e)}")
            return False
    
    @classmethod
    def from_env(cls) -> 'DevOpsAuthProvider':
        """
        Create DevOpsAuthProvider from environment variables.
        
        Environment variables required:
            - AZURE_DEVOPS_ORGANIZATION
            - AZURE_DEVOPS_PAT
        
        Environment variables optional:
            - AZURE_DEVOPS_PROJECT
            
        Returns:
            Configured DevOpsAuthProvider instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        organization = os.getenv('AZURE_DEVOPS_ORGANIZATION')
        pat = os.getenv('AZURE_DEVOPS_PAT')
        project = os.getenv('AZURE_DEVOPS_PROJECT')  # Optional
        
        if not organization or not pat:
            missing = []
            if not organization:
                missing.append('AZURE_DEVOPS_ORGANIZATION')
            if not pat:
                missing.append('AZURE_DEVOPS_PAT')
            
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return cls(organization, pat, project)
