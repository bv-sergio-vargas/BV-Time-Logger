"""
Microsoft Graph API Authentication Provider
OAuth 2.0 authentication using MSAL (Microsoft Authentication Library)
"""

import os
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import msal

logger = logging.getLogger(__name__)


class GraphAuthProvider:
    """
    Handles OAuth 2.0 authentication for Microsoft Graph API.
    Manages token acquisition, refresh, and caching.
    """
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        """
        Initialize Graph API authentication provider.
        
        Args:
            client_id: Azure AD Application (Client) ID
            client_secret: Azure AD Client Secret
            tenant_id: Azure AD Tenant (Directory) ID
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        
        # Initialize MSAL confidential client application
        self._app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        logger.info(f"[AUTH] GraphAuthProvider initialized for tenant {tenant_id}")
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get valid access token. Returns cached token if available and not expired.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
            
        Returns:
            Valid access token string
            
        Raises:
            Exception: If token acquisition fails
        """
        # Return cached token if valid and not expired
        if not force_refresh and self._is_token_valid():
            logger.debug("[AUTH] Using cached access token")
            return self._access_token
        
        logger.info("[AUTH] Acquiring new access token from Microsoft Graph")
        
        try:
            result = self._app.acquire_token_for_client(scopes=self.scopes)
            
            if "access_token" in result:
                self._access_token = result["access_token"]
                
                # Set expiry time (default 3600 seconds, subtract 5 minutes for safety)
                expires_in = result.get("expires_in", 3600)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
                
                logger.info(f"[AUTH] Access token acquired successfully. Expires in {expires_in}s")
                return self._access_token
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "No description")
                logger.error(f"[AUTH] Token acquisition failed: {error} - {error_desc}")
                raise Exception(f"Failed to acquire token: {error} - {error_desc}")
                
        except Exception as e:
            logger.error(f"[AUTH] Exception during token acquisition: {str(e)}")
            raise
    
    def _is_token_valid(self) -> bool:
        """
        Check if cached token exists and is not expired.
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self._access_token or not self._token_expiry:
            return False
        
        # Check if token is expired (with 5-minute buffer)
        return datetime.now() < self._token_expiry
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for Graph API requests.
        
        Returns:
            Dictionary with Authorization header
        """
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def invalidate_token(self):
        """
        Invalidate cached token. Next request will acquire a new token.
        """
        logger.info("[AUTH] Invalidating cached token")
        self._access_token = None
        self._token_expiry = None
    
    @classmethod
    def from_env(cls) -> 'GraphAuthProvider':
        """
        Create GraphAuthProvider from environment variables.
        
        Environment variables required:
            - AZURE_AD_CLIENT_ID
            - AZURE_AD_CLIENT_SECRET
            - AZURE_AD_TENANT_ID
            
        Returns:
            Configured GraphAuthProvider instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        client_id = os.getenv('AZURE_AD_CLIENT_ID')
        client_secret = os.getenv('AZURE_AD_CLIENT_SECRET')
        tenant_id = os.getenv('AZURE_AD_TENANT_ID')
        
        if not all([client_id, client_secret, tenant_id]):
            missing = []
            if not client_id:
                missing.append('AZURE_AD_CLIENT_ID')
            if not client_secret:
                missing.append('AZURE_AD_CLIENT_SECRET')
            if not tenant_id:
                missing.append('AZURE_AD_TENANT_ID')
            
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return cls(client_id, client_secret, tenant_id)
