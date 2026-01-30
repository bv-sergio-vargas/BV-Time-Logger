"""
Microsoft Teams Client - Microsoft Graph API integration
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz
from src.clients.base_client import BaseAPIClient
from src.auth.graph_auth import GraphAuthProvider

logger = logging.getLogger(__name__)


class TeamsClient(BaseAPIClient):
    """
    Client for Microsoft Teams operations via Microsoft Graph API.
    Handles meeting retrieval, calendar access, and user information.
    """
    
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, auth_provider: GraphAuthProvider, timezone: str = "America/Bogota", **kwargs):
        """
        Initialize Teams client.
        
        Args:
            auth_provider: GraphAuthProvider instance
            timezone: Timezone for date operations (default: America/Bogota)
            **kwargs: Additional arguments passed to BaseAPIClient
        """
        super().__init__(auth_provider, **kwargs)
        self.base_url = self.GRAPH_BASE_URL
        self.timezone = pytz.timezone(timezone)
        logger.info(f"[TEAMS] TeamsClient initialized with timezone {timezone}")
    
    def get_user_info(self, user_id: str = "me") -> Dict[str, Any]:
        """
        Get user information from Microsoft Graph.
        
        Args:
            user_id: User ID or "me" for authenticated user
            
        Returns:
            User information dictionary
        """
        url = f"{self.base_url}/users/{user_id}"
        logger.info(f"[TEAMS] Retrieving user info for: {user_id}")
        
        response = self.get(url)
        return response.json()
    
    def get_calendar_events(
        self,
        user_id: str = "me",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        top: int = 100,
        paginate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events for a user within a date range with pagination.
        
        Args:
            user_id: User ID or "me" for authenticated user
            start_date: Start date for event range (optional)
            end_date: End date for event range (optional)
            top: Maximum number of events per page
            paginate: If True, fetch all pages; if False, only first page
            
        Returns:
            List of calendar event dictionaries
        """
        url = f"{self.base_url}/users/{user_id}/calendar/events"
        
        params = {"$top": top}
        
        # Add date filter if provided (convert to UTC for API)
        if start_date and end_date:
            # Ensure timezone-aware
            if start_date.tzinfo is None:
                start_date = self.timezone.localize(start_date)
            if end_date.tzinfo is None:
                end_date = self.timezone.localize(end_date)
            
            # Convert to UTC for API
            start_utc = start_date.astimezone(pytz.utc)
            end_utc = end_date.astimezone(pytz.utc)
            
            start_str = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_str = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'"
        
        logger.info(
            f"[TEAMS] Retrieving calendar events for {user_id} "
            f"(from {start_date} to {end_date}, limit={top})"
        )
        
        events = []
        next_link = url
        
        while next_link:
            if next_link == url:
                response = self.get(url, params=params)
            else:
                # Follow pagination link
                response = self.get(next_link)
            
            data = response.json()
            events.extend(data.get('value', []))
            
            # Check for pagination
            next_link = data.get('@odata.nextLink') if paginate else None
            
            if next_link:
                logger.debug(f"[TEAMS] Following pagination link (current: {len(events)} events)")
        
        logger.info(f"[TEAMS] Retrieved {len(events)} total events")
        
        return events
    
    def get_online_meetings(
        self,
        user_id: str = "me",
        top: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get online meetings for a user.
        
        Args:
            user_id: User ID or "me" for authenticated user
            top: Maximum number of meetings to return
            
        Returns:
            List of online meeting dictionaries
        """
        url = f"{self.base_url}/users/{user_id}/onlineMeetings"
        
        params = {"$top": top}
        
        logger.info(f"[TEAMS] Retrieving online meetings for {user_id} (limit={top})")
        
        response = self.get(url, params=params)
        data = response.json()
        
        meetings = data.get('value', [])
        logger.info(f"[TEAMS] Retrieved {len(meetings)} online meetings")
        
        return meetings
    
    def calculate_meeting_duration(self, event: Dict[str, Any]) -> float:
        """
        Calculate duration of a meeting event in hours.
        
        Args:
            event: Calendar event dictionary
            
        Returns:
            Duration in hours (float)
        """
        try:
            start_str = event['start']['dateTime']
            end_str = event['end']['dateTime']
            
            # Parse datetime strings
            start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            # Calculate duration
            duration_seconds = (end_dt - start_dt).total_seconds()
            duration_hours = duration_seconds / 3600
            
            logger.debug(f"[TEAMS] Event '{event.get('subject', 'N/A')}': {duration_hours:.2f} hours")
            
            return duration_hours
            
        except (KeyError, ValueError) as e:
            logger.error(f"[TEAMS] Error calculating duration: {str(e)}")
            return 0.0
    
    def filter_meetings(
        self,
        events: List[Dict[str, Any]],
        include_cancelled: bool = False,
        meeting_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter calendar events to include only relevant meetings.
        
        Args:
            events: List of calendar events
            include_cancelled: Whether to include cancelled events
            meeting_types: List of meeting types to include (e.g., ['Teams', 'Skype'])
            
        Returns:
            Filtered list of meetings
        """
        filtered = []
        
        for event in events:
            # Skip cancelled events if configured
            if not include_cancelled and event.get('isCancelled', False):
                continue
            
            # Check if it's an online meeting
            is_online_meeting = event.get('isOnlineMeeting', False)
            
            # Filter by meeting type if specified
            if meeting_types:
                online_meeting_provider = event.get('onlineMeetingProvider', '')
                if online_meeting_provider not in meeting_types:
                    continue
            
            filtered.append(event)
        
        logger.info(f"[TEAMS] Filtered {len(filtered)} meetings from {len(events)} events")
        return filtered
    
    def get_meeting_attendees(self, event: Dict[str, Any]) -> List[str]:
        """
        Extract attendee email addresses from a meeting event.
        
        Args:
            event: Calendar event dictionary
            
        Returns:
            List of attendee email addresses
        """
        attendees = event.get('attendees', [])
        emails = [
            attendee.get('emailAddress', {}).get('address', '')
            for attendee in attendees
            if attendee.get('emailAddress', {}).get('address')
        ]
        
        return emails
