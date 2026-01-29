"""
Base API Client with retry logic, rate limiting, and error handling
"""

import time
import logging
from typing import Optional, Dict, Any
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP methods supported by the client"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class BaseAPIClient:
    """
    Base client for API requests with automatic retry logic, rate limiting,
    and comprehensive error handling.
    """
    
    def __init__(
        self,
        auth_provider,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30
    ):
        """
        Initialize base API client.
        
        Args:
            auth_provider: Authentication provider (GraphAuthProvider or DevOpsAuthProvider)
            max_retries: Maximum number of retry attempts for failed requests
            backoff_factor: Multiplier for exponential backoff (delay = backoff_factor * (2 ** retry_count))
            timeout: Request timeout in seconds
        """
        self.auth_provider = auth_provider
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        
        # Create session with connection pooling
        self.session = self._create_session()
        
        logger.info(
            f"[API] BaseAPIClient initialized "
            f"(retries={max_retries}, backoff={backoff_factor}s, timeout={timeout}s)"
        )
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry configuration.
        
        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(
        self,
        method: HTTPMethod,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: Full URL for the request
            headers: Additional headers (merged with auth headers)
            data: Request body (for POST/PUT/PATCH)
            params: Query parameters
            **kwargs: Additional arguments passed to requests
            
        Returns:
            requests.Response object
            
        Raises:
            requests.RequestException: On request failure after retries
        """
        # Get authentication headers
        auth_headers = self.auth_provider.get_auth_headers()
        
        # Merge with additional headers
        if headers:
            auth_headers.update(headers)
        
        # Prepare request kwargs
        request_kwargs = {
            "headers": auth_headers,
            "timeout": self.timeout,
            **kwargs
        }
        
        if data:
            import json
            request_kwargs["data"] = json.dumps(data)
        
        if params:
            request_kwargs["params"] = params
        
        # Log request
        logger.debug(f"[API] {method.value} {url}")
        
        try:
            # Make request
            response = self.session.request(
                method=method.value,
                url=url,
                **request_kwargs
            )
            
            # Log response
            content_size = len(response.content) if hasattr(response, 'content') and response.content else 0
            logger.debug(f"[API] Response: {response.status_code} (size: {content_size} bytes)")
            
            # Raise for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[API] HTTP error: {e.response.status_code} - {str(e)}")
            self._handle_http_error(e.response)
            raise
            
        except requests.exceptions.Timeout as e:
            logger.error(f"[API] Request timeout after {self.timeout}s: {str(e)}")
            raise
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[API] Connection error: {str(e)}")
            raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[API] Request exception: {str(e)}")
            raise
    
    def _handle_http_error(self, response: requests.Response):
        """
        Handle HTTP error responses with specific logging.
        
        Args:
            response: Response object with error status
        """
        status_code = response.status_code
        
        if status_code == 401:
            logger.error("[API] Unauthorized (401): Check authentication credentials")
        elif status_code == 403:
            logger.error("[API] Forbidden (403): Insufficient permissions")
        elif status_code == 404:
            logger.error(f"[API] Not found (404): {response.url}")
        elif status_code == 429:
            logger.warning("[API] Rate limit exceeded (429): Too many requests")
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                logger.warning(f"[API] Retry after {retry_after} seconds")
        elif status_code >= 500:
            logger.error(f"[API] Server error ({status_code}): {response.text[:200]}")
        
        # Log response body for debugging (truncated)
        try:
            error_body = response.json()
            logger.debug(f"[API] Error response: {error_body}")
        except:
            logger.debug(f"[API] Error response (raw): {response.text[:500]}")
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Make GET request.
        
        Args:
            url: Full URL
            **kwargs: Additional arguments for request
            
        Returns:
            Response object
        """
        return self._make_request(HTTPMethod.GET, url, **kwargs)
    
    def post(self, url: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Make POST request.
        
        Args:
            url: Full URL
            data: Request body
            **kwargs: Additional arguments for request
            
        Returns:
            Response object
        """
        return self._make_request(HTTPMethod.POST, url, data=data, **kwargs)
    
    def put(self, url: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Make PUT request.
        
        Args:
            url: Full URL
            data: Request body
            **kwargs: Additional arguments for request
            
        Returns:
            Response object
        """
        return self._make_request(HTTPMethod.PUT, url, data=data, **kwargs)
    
    def patch(self, url: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Make PATCH request.
        
        Args:
            url: Full URL
            data: Request body
            **kwargs: Additional arguments for request
            
        Returns:
            Response object
        """
        return self._make_request(HTTPMethod.PATCH, url, data=data, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """
        Make DELETE request.
        
        Args:
            url: Full URL
            **kwargs: Additional arguments for request
            
        Returns:
            Response object
        """
        return self._make_request(HTTPMethod.DELETE, url, **kwargs)
    
    def close(self):
        """Close the session and release resources."""
        if self.session:
            self.session.close()
            logger.info("[API] Session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
