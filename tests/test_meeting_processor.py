"""
Unit tests for MeetingProcessor and MeetingMatcher
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pytz

from src.core.meeting_processor import MeetingProcessor
from src.core.meeting_matcher import MeetingMatcher, MatchingRuleEngine


class TestMeetingProcessor:
    """Tests for MeetingProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Create MeetingProcessor instance"""
        return MeetingProcessor(timezone="America/Bogota")
    
    @pytest.fixture
    def sample_meetings(self):
        """Sample Graph API meetings"""
        tz = pytz.timezone("America/Bogota")
        now = datetime.now(tz)
        
        return [
            {
                'id': 'meeting-1',
                'subject': 'Daily Standup',
                'start': {'dateTime': now.replace(hour=9, minute=0).isoformat()},
                'end': {'dateTime': now.replace(hour=9, minute=30).isoformat()},
                'attendees': [
                    {'emailAddress': {'address': 'user1@example.com'}},
                    {'emailAddress': {'address': 'user2@example.com'}}
                ],
                'organizer': {'emailAddress': {'address': 'user1@example.com'}},
                'isCancelled': False,
                'isOnlineMeeting': True
            },
            {
                'id': 'meeting-2',
                'subject': 'Sprint Planning',
                'start': {'dateTime': now.replace(hour=14, minute=0).isoformat()},
                'end': {'dateTime': now.replace(hour=16, minute=0).isoformat()},
                'attendees': [
                    {'emailAddress': {'address': 'user1@example.com'}},
                    {'emailAddress': {'address': 'user3@example.com'}}
                ],
                'organizer': {'emailAddress': {'address': 'user3@example.com'}},
                'isCancelled': False,
                'isOnlineMeeting': True
            },
            {
                'id': 'meeting-3',
                'subject': 'Cancelled Meeting',
                'start': {'dateTime': now.replace(hour=11, minute=0).isoformat()},
                'end': {'dateTime': now.replace(hour=12, minute=0).isoformat()},
                'attendees': [{'emailAddress': {'address': 'user1@example.com'}}],
                'organizer': {'emailAddress': {'address': 'user1@example.com'}},
                'isCancelled': True,
                'isOnlineMeeting': True
            }
        ]
    
    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor.timezone.zone == "America/Bogota"
    
    def test_process_meetings(self, processor, sample_meetings):
        """Test processing list of meetings"""
        processed = processor.process_meetings(sample_meetings)
        
        assert len(processed) == 3
        assert all('duration_hours' in m for m in processed)
        assert all('date' in m for m in processed)
        assert processed[0]['subject'] == 'Daily Standup'
        assert processed[0]['duration_hours'] == 0.5  # 30 minutes
        assert processed[1]['duration_hours'] == 2.0  # 2 hours
    
    def test_process_single_meeting(self, processor, sample_meetings):
        """Test processing a single meeting"""
        meeting = sample_meetings[0]
        processed = processor._process_single_meeting(meeting)
        
        assert processed is not None
        assert processed['id'] == 'meeting-1'
        assert processed['subject'] == 'Daily Standup'
        assert processed['duration_hours'] == 0.5
        assert len(processed['attendees']) == 2
        assert processed['organizer'] == 'user1@example.com'
        assert processed['is_cancelled'] is False
        assert processed['is_online'] is True
    
    def test_process_meeting_missing_time(self, processor):
        """Test handling meeting with missing time"""
        invalid_meeting = {
            'id': 'invalid',
            'subject': 'Test',
            'start': {},
            'end': {}
        }
        
        processed = processor._process_single_meeting(invalid_meeting)
        assert processed is None
    
    def test_aggregate_by_day(self, processor, sample_meetings):
        """Test daily aggregation"""
        processed = processor.process_meetings(sample_meetings)
        daily = processor.aggregate_by_day(processed)
        
        assert len(daily) == 1  # All meetings same day
        date_key = list(daily.keys())[0]
        
        # Should only count non-cancelled meetings
        assert daily[date_key]['meeting_count'] == 2
        assert daily[date_key]['total_hours'] == 2.5  # 0.5 + 2.0
        assert len(daily[date_key]['meetings']) == 2
    
    def test_aggregate_by_week(self, processor, sample_meetings):
        """Test weekly aggregation"""
        processed = processor.process_meetings(sample_meetings)
        weekly = processor.aggregate_by_week(processed)
        
        assert len(weekly) >= 1
        week_key = list(weekly.keys())[0]
        
        assert weekly[week_key]['meeting_count'] == 2
        assert weekly[week_key]['total_hours'] == 2.5
    
    def test_aggregate_by_user(self, processor, sample_meetings):
        """Test user aggregation"""
        processed = processor.process_meetings(sample_meetings)
        by_user = processor.aggregate_by_user(processed)
        
        assert 'user1@example.com' in by_user
        assert 'user2@example.com' in by_user
        assert 'user3@example.com' in by_user
        
        # user1 is in both active meetings
        assert by_user['user1@example.com']['meeting_count'] == 2
        assert by_user['user1@example.com']['total_hours'] == 2.5
        
        # user2 only in first meeting
        assert by_user['user2@example.com']['meeting_count'] == 1
        assert by_user['user2@example.com']['total_hours'] == 0.5
    
    def test_filter_by_attendee(self, processor, sample_meetings):
        """Test filtering by attendee"""
        processed = processor.process_meetings(sample_meetings)
        filtered = processor.filter_by_attendee(processed, 'user1@example.com')
        
        assert len(filtered) == 3  # user1 in all meetings
        
        filtered = processor.filter_by_attendee(processed, 'user2@example.com')
        assert len(filtered) == 1  # user2 only in first
    
    def test_get_summary(self, processor, sample_meetings):
        """Test summary statistics"""
        processed = processor.process_meetings(sample_meetings)
        summary = processor.get_summary(processed)
        
        assert summary['total_meetings'] == 3
        assert summary['active_meetings'] == 2
        assert summary['total_hours'] == 2.5
        assert summary['cancelled_count'] == 1
        assert summary['online_count'] == 3
        assert summary['average_duration'] == 1.25  # 2.5 / 2


class TestMeetingMatcher:
    """Tests for MeetingMatcher"""
    
    @pytest.fixture
    def matcher(self):
        """Create MeetingMatcher instance"""
        return MeetingMatcher(min_similarity=0.6)
    
    @pytest.fixture
    def sample_meeting(self):
        """Sample processed meeting"""
        return {
            'id': 'meeting-1',
            'subject': 'Work on Task #123',
            'duration_hours': 1.0,
            'attendees': ['user1@example.com', 'user2@example.com'],
            'is_cancelled': False
        }
    
    @pytest.fixture
    def sample_work_items(self):
        """Sample Azure DevOps work items"""
        return [
            {
                'id': 123,
                'fields': {
                    'System.Title': 'Implement authentication feature',
                    'System.AssignedTo': {
                        'uniqueName': 'user1@example.com'
                    }
                }
            },
            {
                'id': 456,
                'fields': {
                    'System.Title': 'Fix login bug',
                    'System.AssignedTo': {
                        'uniqueName': 'user3@example.com'
                    }
                }
            }
        ]
    
    def test_initialization(self, matcher):
        """Test matcher initialization"""
        assert matcher.min_similarity == 0.6
    
    def test_match_by_id_in_subject(self, matcher, sample_meeting, sample_work_items):
        """Test matching by work item ID in subject"""
        work_item = matcher.match_meeting_to_workitem(sample_meeting, sample_work_items)
        
        assert work_item is not None
        assert work_item['id'] == 123
    
    def test_match_by_id_various_formats(self, matcher, sample_work_items):
        """Test matching various ID formats"""
        test_cases = [
            {'subject': '#123 Daily meeting', 'expected_id': 123},
            {'subject': 'Meeting about WI-123', 'expected_id': 123},
            {'subject': 'Task 123 discussion', 'expected_id': 123},
            {'subject': '[123] Planning session', 'expected_id': 123},
        ]
        
        for test_case in test_cases:
            meeting = {
                'id': 'test',
                'subject': test_case['subject'],
                'attendees': [],
                'is_cancelled': False
            }
            
            work_item = matcher.match_meeting_to_workitem(meeting, sample_work_items)
            assert work_item is not None
            assert work_item['id'] == test_case['expected_id']
    
    def test_match_by_attendees(self, matcher, sample_work_items):
        """Test matching by assigned user in attendees"""
        meeting = {
            'id': 'meeting-2',
            'subject': 'General planning',  # No ID
            'attendees': ['user1@example.com', 'user2@example.com'],
            'is_cancelled': False
        }
        
        work_item = matcher.match_meeting_to_workitem(meeting, sample_work_items)
        
        assert work_item is not None
        assert work_item['id'] == 123  # Assigned to user1
    
    def test_no_match(self, matcher, sample_work_items):
        """Test when no match is found"""
        meeting = {
            'id': 'meeting-3',
            'subject': 'Random meeting',
            'attendees': ['unknown@example.com'],
            'is_cancelled': False
        }
        
        work_item = matcher.match_meeting_to_workitem(meeting, sample_work_items)
        
        assert work_item is None
    
    def test_match_meetings_batch(self, matcher, sample_work_items):
        """Test batch matching"""
        meetings = [
            {
                'id': 'm1',
                'subject': 'Task #123 review',
                'attendees': ['user1@example.com'],
                'duration_hours': 1.0,
                'is_cancelled': False
            },
            {
                'id': 'm2',
                'subject': 'Fix issue #456',
                'attendees': ['user3@example.com'],
                'duration_hours': 0.5,
                'is_cancelled': False
            },
            {
                'id': 'm3',
                'subject': 'Random meeting',
                'attendees': ['unknown@example.com'],
                'duration_hours': 1.0,
                'is_cancelled': False
            }
        ]
        
        result = matcher.match_meetings_batch(meetings, sample_work_items)
        
        assert result['matched_count'] == 2
        assert result['unmatched_count'] == 1
        assert result['match_rate'] == pytest.approx(0.666, rel=0.01)
        assert len(result['matched']) == 2
        assert len(result['unmatched']) == 1
    
    def test_skip_cancelled_meetings(self, matcher, sample_work_items):
        """Test that cancelled meetings are skipped"""
        meetings = [
            {
                'id': 'm1',
                'subject': 'Task #123',
                'attendees': ['user1@example.com'],
                'is_cancelled': True
            }
        ]
        
        result = matcher.match_meetings_batch(meetings, sample_work_items)
        
        assert result['matched_count'] == 0
        assert result['unmatched_count'] == 0
    
    def test_get_unmatched_summary(self, matcher):
        """Test unmatched summary"""
        unmatched = [
            {
                'id': 'm1',
                'subject': 'Meeting 1',
                'duration_hours': 1.0
            },
            {
                'id': 'm2',
                'subject': 'Meeting 2',
                'duration_hours': 0.5
            }
        ]
        
        summary = matcher.get_unmatched_summary(unmatched)
        
        assert summary['count'] == 2
        assert summary['total_hours'] == 1.5
        assert len(summary['subjects']) == 2


class TestMatchingRuleEngine:
    """Tests for MatchingRuleEngine"""
    
    @pytest.fixture
    def rules(self):
        """Sample matching rules"""
        return [
            {
                'name': 'Daily Standup Rule',
                'pattern': r'Daily.*Standup',
                'work_item_id': 100
            },
            {
                'name': 'Sprint Planning Rule',
                'pattern': r'Sprint.*Planning',
                'work_item_id': 200
            }
        ]
    
    @pytest.fixture
    def work_items(self):
        """Sample work items"""
        return [
            {'id': 100, 'fields': {'System.Title': 'Standup Task'}},
            {'id': 200, 'fields': {'System.Title': 'Planning Task'}}
        ]
    
    def test_rule_engine_initialization(self, rules):
        """Test rule engine initialization"""
        engine = MatchingRuleEngine(rules)
        assert len(engine.rules) == 2
    
    def test_apply_rules_match(self, rules, work_items):
        """Test applying rules with match"""
        engine = MatchingRuleEngine(rules)
        
        meeting = {
            'subject': 'Daily Team Standup',
            'attendees': []
        }
        
        work_item = engine.apply_rules(meeting, work_items)
        
        assert work_item is not None
        assert work_item['id'] == 100
    
    def test_apply_rules_no_match(self, rules, work_items):
        """Test applying rules with no match"""
        engine = MatchingRuleEngine(rules)
        
        meeting = {
            'subject': 'Random Meeting',
            'attendees': []
        }
        
        work_item = engine.apply_rules(meeting, work_items)
        
        assert work_item is None
