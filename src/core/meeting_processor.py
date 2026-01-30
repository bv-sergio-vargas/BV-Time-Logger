"""
Meeting Processor - Process and aggregate Teams meeting data
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import pytz

logger = logging.getLogger(__name__)


class MeetingProcessor:
    """
    Process and aggregate Microsoft Teams meeting data.
    Calculates durations, filters meetings, and aggregates by time periods.
    """
    
    def __init__(self, timezone: str = "America/Bogota"):
        """
        Initialize MeetingProcessor.
        
        Args:
            timezone: Timezone for date calculations (default: America/Bogota)
        """
        self.timezone = pytz.timezone(timezone)
        logger.info(f"[PROCESSOR] Initialized with timezone: {timezone}")
    
    def process_meetings(self, meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process list of meetings and extract relevant information.
        
        Args:
            meetings: List of meeting dictionaries from Microsoft Graph API
            
        Returns:
            List of processed meeting dictionaries with calculated fields
        """
        processed = []
        
        for meeting in meetings:
            try:
                processed_meeting = self._process_single_meeting(meeting)
                if processed_meeting:
                    processed.append(processed_meeting)
            except Exception as e:
                logger.error(f"[PROCESSOR] Error processing meeting {meeting.get('id')}: {e}")
                continue
        
        logger.info(f"[PROCESSOR] Processed {len(processed)} of {len(meetings)} meetings")
        return processed
    
    def _process_single_meeting(self, meeting: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single meeting and extract key information.
        
        Args:
            meeting: Meeting dictionary from Graph API
            
        Returns:
            Processed meeting dictionary or None if invalid
        """
        # Extract basic info
        meeting_id = meeting.get('id')
        subject = meeting.get('subject', 'No Subject')
        
        # Parse start and end times
        start_str = meeting.get('start', {}).get('dateTime')
        end_str = meeting.get('end', {}).get('dateTime')
        
        if not start_str or not end_str:
            logger.warning(f"[PROCESSOR] Meeting {meeting_id} missing start/end time")
            return None
        
        # Convert to datetime with timezone
        start_time = self._parse_datetime(start_str)
        end_time = self._parse_datetime(end_str)
        
        if not start_time or not end_time:
            return None
        
        # Calculate duration in hours
        duration = (end_time - start_time).total_seconds() / 3600
        
        # Extract attendees
        attendees = []
        for attendee in meeting.get('attendees', []):
            email = attendee.get('emailAddress', {}).get('address')
            if email:
                attendees.append(email)
        
        # Extract organizer
        organizer = meeting.get('organizer', {}).get('emailAddress', {}).get('address', '')
        
        # Check if cancelled
        is_cancelled = meeting.get('isCancelled', False)
        
        # Check if online meeting
        is_online = meeting.get('isOnlineMeeting', False)
        
        return {
            'id': meeting_id,
            'subject': subject,
            'start_time': start_time,
            'end_time': end_time,
            'duration_hours': round(duration, 2),
            'date': start_time.date(),
            'attendees': attendees,
            'organizer': organizer,
            'is_cancelled': is_cancelled,
            'is_online': is_online,
            'raw_meeting': meeting
        }
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """
        Parse datetime string and convert to configured timezone.
        
        Args:
            dt_string: ISO format datetime string
            
        Returns:
            Datetime object in configured timezone or None
        """
        try:
            # Parse ISO format (may include Z or timezone offset)
            if dt_string.endswith('Z'):
                dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(dt_string)
            
            # Convert to configured timezone
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            
            return dt.astimezone(self.timezone)
        
        except Exception as e:
            logger.error(f"[PROCESSOR] Error parsing datetime '{dt_string}': {e}")
            return None
    
    def aggregate_by_day(self, meetings: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate meetings by day.
        
        Args:
            meetings: List of processed meetings
            
        Returns:
            Dictionary with date keys and aggregated data
        """
        daily_data = defaultdict(lambda: {
            'total_hours': 0.0,
            'meeting_count': 0,
            'meetings': []
        })
        
        for meeting in meetings:
            if meeting.get('is_cancelled'):
                continue
            
            date_key = meeting['date'].isoformat()
            duration = meeting.get('duration_hours', 0.0)
            
            daily_data[date_key]['total_hours'] += duration
            daily_data[date_key]['meeting_count'] += 1
            daily_data[date_key]['meetings'].append({
                'id': meeting['id'],
                'subject': meeting['subject'],
                'duration_hours': duration,
                'start_time': meeting['start_time'].isoformat(),
                'attendees_count': len(meeting.get('attendees', []))
            })
        
        # Round totals
        for date_key in daily_data:
            daily_data[date_key]['total_hours'] = round(daily_data[date_key]['total_hours'], 2)
        
        logger.info(f"[PROCESSOR] Aggregated {len(meetings)} meetings into {len(daily_data)} days")
        return dict(daily_data)
    
    def aggregate_by_week(self, meetings: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate meetings by week (ISO week number).
        
        Args:
            meetings: List of processed meetings
            
        Returns:
            Dictionary with week keys (YYYY-Wnn) and aggregated data
        """
        weekly_data = defaultdict(lambda: {
            'total_hours': 0.0,
            'meeting_count': 0,
            'meetings': []
        })
        
        for meeting in meetings:
            if meeting.get('is_cancelled'):
                continue
            
            # Get ISO week
            date = meeting['date']
            year, week, _ = date.isocalendar()
            week_key = f"{year}-W{week:02d}"
            
            duration = meeting.get('duration_hours', 0.0)
            
            weekly_data[week_key]['total_hours'] += duration
            weekly_data[week_key]['meeting_count'] += 1
            weekly_data[week_key]['meetings'].append({
                'id': meeting['id'],
                'subject': meeting['subject'],
                'duration_hours': duration,
                'date': date.isoformat()
            })
        
        # Round totals
        for week_key in weekly_data:
            weekly_data[week_key]['total_hours'] = round(weekly_data[week_key]['total_hours'], 2)
        
        logger.info(f"[PROCESSOR] Aggregated {len(meetings)} meetings into {len(weekly_data)} weeks")
        return dict(weekly_data)
    
    def aggregate_by_user(self, meetings: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate meeting time by user (attendee).
        
        Args:
            meetings: List of processed meetings
            
        Returns:
            Dictionary with user email keys and aggregated data
        """
        user_data = defaultdict(lambda: {
            'total_hours': 0.0,
            'meeting_count': 0,
            'meetings': []
        })
        
        for meeting in meetings:
            if meeting.get('is_cancelled'):
                continue
            
            duration = meeting.get('duration_hours', 0.0)
            
            # Add to each attendee's total
            for attendee in meeting.get('attendees', []):
                user_data[attendee]['total_hours'] += duration
                user_data[attendee]['meeting_count'] += 1
                user_data[attendee]['meetings'].append({
                    'id': meeting['id'],
                    'subject': meeting['subject'],
                    'duration_hours': duration,
                    'date': meeting['date'].isoformat()
                })
        
        # Round totals
        for user in user_data:
            user_data[user]['total_hours'] = round(user_data[user]['total_hours'], 2)
        
        logger.info(f"[PROCESSOR] Aggregated meetings for {len(user_data)} users")
        return dict(user_data)
    
    def filter_by_date_range(
        self,
        meetings: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Filter meetings by date range.
        
        Args:
            meetings: List of processed meetings
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Filtered list of meetings
        """
        # Ensure dates have timezone info
        if start_date.tzinfo is None:
            start_date = self.timezone.localize(start_date)
        if end_date.tzinfo is None:
            end_date = self.timezone.localize(end_date)
        
        filtered = [
            m for m in meetings
            if start_date <= m['start_time'] <= end_date
        ]
        
        logger.info(f"[PROCESSOR] Filtered to {len(filtered)} meetings in date range")
        return filtered
    
    def filter_by_attendee(
        self,
        meetings: List[Dict[str, Any]],
        attendee_email: str
    ) -> List[Dict[str, Any]]:
        """
        Filter meetings where a specific user is an attendee.
        
        Args:
            meetings: List of processed meetings
            attendee_email: Email address of attendee
            
        Returns:
            Filtered list of meetings
        """
        filtered = [
            m for m in meetings
            if attendee_email.lower() in [a.lower() for a in m.get('attendees', [])]
        ]
        
        logger.info(f"[PROCESSOR] Filtered to {len(filtered)} meetings for {attendee_email}")
        return filtered
    
    def get_summary(self, meetings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for a list of meetings.
        
        Args:
            meetings: List of processed meetings
            
        Returns:
            Dictionary with summary statistics
        """
        if not meetings:
            return {
                'total_meetings': 0,
                'total_hours': 0.0,
                'average_duration': 0.0,
                'cancelled_count': 0,
                'online_count': 0
            }
        
        total_hours = sum(m.get('duration_hours', 0.0) for m in meetings if not m.get('is_cancelled'))
        active_meetings = [m for m in meetings if not m.get('is_cancelled')]
        cancelled_count = sum(1 for m in meetings if m.get('is_cancelled'))
        online_count = sum(1 for m in meetings if m.get('is_online'))
        
        avg_duration = total_hours / len(active_meetings) if active_meetings else 0.0
        
        return {
            'total_meetings': len(meetings),
            'active_meetings': len(active_meetings),
            'total_hours': round(total_hours, 2),
            'average_duration': round(avg_duration, 2),
            'cancelled_count': cancelled_count,
            'online_count': online_count
        }
