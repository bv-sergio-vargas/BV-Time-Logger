"""
Meeting Matcher - Link meetings to Azure DevOps work items
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class MeetingMatcher:
    """
    Match Microsoft Teams meetings to Azure DevOps work items.
    Uses multiple strategies: work item ID detection, subject matching, attendee matching.
    """
    
    def __init__(self, min_similarity: float = 0.6):
        """
        Initialize MeetingMatcher.
        
        Args:
            min_similarity: Minimum similarity score (0-1) for fuzzy matching (default: 0.6)
        """
        self.min_similarity = min_similarity
        logger.info(f"[MATCHER] Initialized with min_similarity={min_similarity}")
    
    def match_meeting_to_workitem(
        self,
        meeting: Dict[str, Any],
        work_items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to match a meeting to a work item.
        
        Args:
            meeting: Processed meeting dictionary
            work_items: List of work item dictionaries from Azure DevOps
            
        Returns:
            Best matching work item or None
        """
        if not work_items:
            logger.debug(f"[MATCHER] No work items provided for matching")
            return None
        
        # Strategy 1: Look for work item ID in subject
        work_item = self._match_by_id_in_subject(meeting, work_items)
        if work_item:
            logger.info(f"[MATCHER] Matched meeting '{meeting['subject']}' to work item #{work_item['id']} by ID")
            return work_item
        
        # Strategy 2: Fuzzy match by subject similarity
        work_item, score = self._match_by_subject_similarity(meeting, work_items)
        if work_item and score >= self.min_similarity:
            logger.info(f"[MATCHER] Matched meeting '{meeting['subject']}' to work item #{work_item['id']} by subject (score: {score:.2f})")
            return work_item
        
        # Strategy 3: Match by assigned users in attendees
        work_item = self._match_by_attendees(meeting, work_items)
        if work_item:
            logger.info(f"[MATCHER] Matched meeting '{meeting['subject']}' to work item #{work_item['id']} by attendees")
            return work_item
        
        logger.debug(f"[MATCHER] No match found for meeting '{meeting['subject']}'")
        return None
    
    def match_meetings_batch(
        self,
        meetings: List[Dict[str, Any]],
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Match multiple meetings to work items.
        
        Args:
            meetings: List of processed meetings
            work_items: List of work items from Azure DevOps
            
        Returns:
            Dictionary with matched, unmatched, and statistics
        """
        matched = []
        unmatched = []
        
        for meeting in meetings:
            # Skip cancelled meetings
            if meeting.get('is_cancelled'):
                continue
            
            work_item = self.match_meeting_to_workitem(meeting, work_items)
            
            if work_item:
                matched.append({
                    'meeting': meeting,
                    'work_item': work_item,
                    'duration_hours': meeting.get('duration_hours', 0.0)
                })
            else:
                unmatched.append(meeting)
        
        logger.info(f"[MATCHER] Batch matching: {len(matched)} matched, {len(unmatched)} unmatched")
        
        return {
            'matched': matched,
            'unmatched': unmatched,
            'total_meetings': len(meetings),
            'matched_count': len(matched),
            'unmatched_count': len(unmatched),
            'match_rate': len(matched) / len(meetings) if meetings else 0.0
        }
    
    def _match_by_id_in_subject(
        self,
        meeting: Dict[str, Any],
        work_items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to find work item ID in meeting subject.
        Supports formats: #123, WI-123, Task 123, [123]
        
        Args:
            meeting: Meeting dictionary
            work_items: List of work items
            
        Returns:
            Matching work item or None
        """
        subject = meeting.get('subject', '')
        
        # Try different ID patterns
        patterns = [
            r'#(\d+)',           # #123
            r'WI[-\s]?(\d+)',    # WI-123 or WI 123
            r'Task[-\s]?(\d+)',  # Task-123 or Task 123
            r'\[(\d+)\]',        # [123]
            r'(?:^|\s)(\d{3,})'  # Standalone 3+ digit number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                work_item_id = int(match.group(1))
                
                # Find matching work item
                for work_item in work_items:
                    if work_item.get('id') == work_item_id:
                        return work_item
        
        return None
    
    def _match_by_subject_similarity(
        self,
        meeting: Dict[str, Any],
        work_items: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Match by fuzzy comparison of subject with work item title.
        
        Args:
            meeting: Meeting dictionary
            work_items: List of work items
            
        Returns:
            Tuple of (best matching work item, similarity score)
        """
        meeting_subject = meeting.get('subject', '').lower()
        
        if not meeting_subject:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        
        for work_item in work_items:
            title = work_item.get('fields', {}).get('System.Title', '').lower()
            
            if not title:
                continue
            
            # Calculate similarity
            score = SequenceMatcher(None, meeting_subject, title).ratio()
            
            if score > best_score:
                best_score = score
                best_match = work_item
        
        return best_match, best_score
    
    def _match_by_attendees(
        self,
        meeting: Dict[str, Any],
        work_items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Match by checking if assigned user is in meeting attendees.
        
        Args:
            meeting: Meeting dictionary
            work_items: List of work items
            
        Returns:
            Matching work item or None
        """
        attendees = [a.lower() for a in meeting.get('attendees', [])]
        
        if not attendees:
            return None
        
        # Look for work items assigned to any of the attendees
        for work_item in work_items:
            assigned_to = work_item.get('fields', {}).get('System.AssignedTo', {})
            
            if isinstance(assigned_to, dict):
                unique_name = assigned_to.get('uniqueName', '').lower()
            else:
                unique_name = str(assigned_to).lower()
            
            if unique_name in attendees:
                return work_item
        
        return None
    
    def create_matching_rules(
        self,
        rules: List[Dict[str, Any]]
    ) -> 'MatchingRuleEngine':
        """
        Create a custom rule engine for matching.
        
        Args:
            rules: List of rule dictionaries
            
        Returns:
            MatchingRuleEngine instance
        """
        return MatchingRuleEngine(rules)
    
    def get_unmatched_summary(self, unmatched_meetings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of unmatched meetings for analysis.
        
        Args:
            unmatched_meetings: List of unmatched meeting dictionaries
            
        Returns:
            Summary statistics
        """
        if not unmatched_meetings:
            return {
                'count': 0,
                'total_hours': 0.0,
                'subjects': []
            }
        
        total_hours = sum(m.get('duration_hours', 0.0) for m in unmatched_meetings)
        subjects = [m.get('subject', 'No Subject') for m in unmatched_meetings]
        
        return {
            'count': len(unmatched_meetings),
            'total_hours': round(total_hours, 2),
            'subjects': subjects,
            'unique_subjects': list(set(subjects))
        }


class MatchingRuleEngine:
    """
    Custom rule engine for flexible meeting-to-work-item matching.
    Allows defining custom rules based on patterns, keywords, etc.
    """
    
    def __init__(self, rules: List[Dict[str, Any]]):
        """
        Initialize rule engine with custom rules.
        
        Args:
            rules: List of rule dictionaries with 'pattern', 'work_item_id', etc.
        """
        self.rules = rules
        logger.info(f"[RULE_ENGINE] Initialized with {len(rules)} rules")
    
    def apply_rules(
        self,
        meeting: Dict[str, Any],
        work_items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Apply custom rules to match meeting.
        
        Args:
            meeting: Meeting dictionary
            work_items: List of work items
            
        Returns:
            Matched work item or None
        """
        subject = meeting.get('subject', '')
        
        for rule in self.rules:
            pattern = rule.get('pattern')
            work_item_id = rule.get('work_item_id')
            
            if not pattern or not work_item_id:
                continue
            
            # Check if pattern matches subject
            if re.search(pattern, subject, re.IGNORECASE):
                # Find work item by ID
                for work_item in work_items:
                    if work_item.get('id') == work_item_id:
                        logger.info(f"[RULE_ENGINE] Matched by rule: {rule.get('name', 'unnamed')}")
                        return work_item
        
        return None
