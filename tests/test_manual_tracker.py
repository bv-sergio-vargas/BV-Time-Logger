"""
Tests for ManualTimeTracker
"""

import pytest
import json
from datetime import date, datetime
from pathlib import Path

from src.tracking.manual_tracker import ManualTimeTracker, TimeEntry


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage path"""
    return tmp_path / "test_entries.json"


@pytest.fixture
def tracker(temp_storage):
    """Create tracker with temporary storage"""
    return ManualTimeTracker(storage_path=temp_storage)


def test_time_entry_initialization():
    """Test TimeEntry initialization"""
    entry = TimeEntry(
        work_item_id=123,
        hours=8.5,
        date=date(2024, 1, 15),
        description="Development work",
        user_id="user@example.com"
    )
    
    assert entry.work_item_id == 123
    assert entry.hours == 8.5
    assert entry.date == "2024-01-15"
    assert entry.description == "Development work"
    assert entry.user_id == "user@example.com"
    assert entry.synced is False
    assert entry.entry_id.startswith("ENTRY-")


def test_time_entry_to_dict():
    """Test TimeEntry to_dict conversion"""
    entry = TimeEntry(
        work_item_id=123,
        hours=8.0,
        date=date(2024, 1, 15),
        description="Test",
        user_id="user@example.com"
    )
    
    data = entry.to_dict()
    
    assert data['work_item_id'] == 123
    assert data['hours'] == 8.0
    assert data['description'] == "Test"
    assert data['synced'] is False


def test_time_entry_from_dict():
    """Test TimeEntry from_dict creation"""
    data = {
        'entry_id': 'ENTRY-123',
        'work_item_id': 123,
        'hours': 8.0,
        'date': '2024-01-15',
        'description': 'Test',
        'user_id': 'user@example.com',
        'created_at': '2024-01-15T10:00:00',
        'synced': False,
        'synced_at': None
    }
    
    entry = TimeEntry.from_dict(data)
    
    assert entry.entry_id == 'ENTRY-123'
    assert entry.work_item_id == 123
    assert entry.hours == 8.0


def test_time_entry_mark_synced():
    """Test marking entry as synced"""
    entry = TimeEntry(
        work_item_id=123,
        hours=8.0,
        date=date.today(),
        description="Test",
        user_id="user@example.com"
    )
    
    entry.mark_synced()
    
    assert entry.synced is True
    assert entry.synced_at is not None


def test_tracker_initialization(tracker, temp_storage):
    """Test tracker initializes correctly"""
    assert tracker.storage_path == temp_storage
    assert len(tracker.entries) == 0


def test_add_entry_success(tracker):
    """Test adding valid entry"""
    entry = tracker.add_entry(
        work_item_id=123,
        hours=8.5,
        date=date(2024, 1, 15),
        description="Development work",
        user_id="user@example.com"
    )
    
    assert len(tracker.entries) == 1
    assert entry.work_item_id == 123
    assert entry.hours == 8.5


def test_add_entry_validates_hours(tracker):
    """Test entry validation for hours"""
    with pytest.raises(ValueError, match="Hours must be positive"):
        tracker.add_entry(
            work_item_id=123,
            hours=0,
            date=date.today(),
            description="Test",
            user_id="user@example.com"
        )
    
    with pytest.raises(ValueError, match="Hours cannot exceed 24"):
        tracker.add_entry(
            work_item_id=123,
            hours=25,
            date=date.today(),
            description="Test",
            user_id="user@example.com"
        )


def test_add_entry_validates_work_item(tracker):
    """Test entry validation for work item ID"""
    with pytest.raises(ValueError, match="Invalid work item ID"):
        tracker.add_entry(
            work_item_id=0,
            hours=8.0,
            date=date.today(),
            description="Test",
            user_id="user@example.com"
        )


def test_add_entry_validates_description(tracker):
    """Test entry validation for description"""
    with pytest.raises(ValueError, match="Description is required"):
        tracker.add_entry(
            work_item_id=123,
            hours=8.0,
            date=date.today(),
            description="",
            user_id="user@example.com"
        )


def test_add_entry_validates_user_id(tracker):
    """Test entry validation for user ID"""
    with pytest.raises(ValueError, match="User ID is required"):
        tracker.add_entry(
            work_item_id=123,
            hours=8.0,
            date=date.today(),
            description="Test",
            user_id=""
        )


def test_add_entry_persists(tracker, temp_storage):
    """Test added entry is persisted to storage"""
    tracker.add_entry(
        work_item_id=123,
        hours=8.0,
        date=date.today(),
        description="Test",
        user_id="user@example.com"
    )
    
    assert temp_storage.exists()
    
    # Load and verify
    with open(temp_storage, 'r') as f:
        data = json.load(f)
    
    assert len(data['entries']) == 1


def test_get_entries_no_filter(tracker):
    """Test getting all entries"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user1@example.com")
    tracker.add_entry(124, 4.0, date.today(), "Test 2", "user2@example.com")
    
    entries = tracker.get_entries()
    
    assert len(entries) == 2


def test_get_entries_filter_by_work_item(tracker):
    """Test filtering by work item ID"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user@example.com")
    tracker.add_entry(124, 4.0, date.today(), "Test 2", "user@example.com")
    
    entries = tracker.get_entries(work_item_id=123)
    
    assert len(entries) == 1
    assert entries[0].work_item_id == 123


def test_get_entries_filter_by_user(tracker):
    """Test filtering by user ID"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user1@example.com")
    tracker.add_entry(124, 4.0, date.today(), "Test 2", "user2@example.com")
    
    entries = tracker.get_entries(user_id="user1@example.com")
    
    assert len(entries) == 1
    assert entries[0].user_id == "user1@example.com"


def test_get_entries_filter_by_date_range(tracker):
    """Test filtering by date range"""
    tracker.add_entry(123, 8.0, date(2024, 1, 10), "Test 1", "user@example.com")
    tracker.add_entry(124, 4.0, date(2024, 1, 20), "Test 2", "user@example.com")
    tracker.add_entry(125, 2.0, date(2024, 1, 30), "Test 3", "user@example.com")
    
    entries = tracker.get_entries(
        start_date=date(2024, 1, 15),
        end_date=date(2024, 1, 25)
    )
    
    assert len(entries) == 1
    assert entries[0].work_item_id == 124


def test_get_entries_filter_by_synced(tracker):
    """Test filtering by sync status"""
    entry1 = tracker.add_entry(123, 8.0, date.today(), "Test 1", "user@example.com")
    entry2 = tracker.add_entry(124, 4.0, date.today(), "Test 2", "user@example.com")
    
    entry1.mark_synced()
    tracker._save_entries()
    
    unsynced = tracker.get_entries(synced=False)
    synced = tracker.get_entries(synced=True)
    
    assert len(unsynced) == 1
    assert len(synced) == 1


def test_get_unsynced_entries(tracker):
    """Test getting unsynced entries"""
    entry1 = tracker.add_entry(123, 8.0, date.today(), "Test 1", "user@example.com")
    entry2 = tracker.add_entry(124, 4.0, date.today(), "Test 2", "user@example.com")
    
    entry1.mark_synced()
    tracker._save_entries()
    
    unsynced = tracker.get_unsynced_entries()
    
    assert len(unsynced) == 1
    assert unsynced[0].work_item_id == 124


def test_mark_entry_synced(tracker):
    """Test marking entry as synced"""
    entry = tracker.add_entry(123, 8.0, date.today(), "Test", "user@example.com")
    
    tracker.mark_entry_synced(entry.entry_id)
    
    assert entry.synced is True
    assert entry.synced_at is not None


def test_mark_entry_synced_not_found(tracker):
    """Test marking non-existent entry raises error"""
    with pytest.raises(ValueError, match="Entry not found"):
        tracker.mark_entry_synced("NONEXISTENT")


def test_delete_entry(tracker):
    """Test deleting entry"""
    entry = tracker.add_entry(123, 8.0, date.today(), "Test", "user@example.com")
    
    tracker.delete_entry(entry.entry_id)
    
    assert len(tracker.entries) == 0


def test_delete_entry_not_found(tracker):
    """Test deleting non-existent entry raises error"""
    with pytest.raises(ValueError, match="Entry not found"):
        tracker.delete_entry("NONEXISTENT")


def test_import_from_csv_success(tracker, tmp_path):
    """Test importing entries from CSV"""
    csv_path = tmp_path / "entries.csv"
    csv_content = """work_item_id,hours,date,description,user_id
123,8.0,2024-01-15,Development work,user@example.com
124,4.5,2024-01-16,Code review,user@example.com"""
    
    csv_path.write_text(csv_content)
    
    imported = tracker.import_from_csv(csv_path)
    
    assert len(imported) == 2
    assert len(tracker.entries) == 2
    assert tracker.entries[0].work_item_id == 123


def test_import_from_csv_file_not_found(tracker, tmp_path):
    """Test importing from non-existent file raises error"""
    csv_path = tmp_path / "nonexistent.csv"
    
    with pytest.raises(ValueError, match="CSV file not found"):
        tracker.import_from_csv(csv_path)


def test_import_from_csv_invalid_headers(tracker, tmp_path):
    """Test importing with invalid headers raises error"""
    csv_path = tmp_path / "invalid.csv"
    csv_content = """wrong,headers
123,8.0"""
    
    csv_path.write_text(csv_content)
    
    with pytest.raises(ValueError, match="CSV must have columns"):
        tracker.import_from_csv(csv_path)


def test_export_to_csv(tracker, tmp_path):
    """Test exporting entries to CSV"""
    tracker.add_entry(123, 8.0, date(2024, 1, 15), "Test 1", "user@example.com")
    tracker.add_entry(124, 4.0, date(2024, 1, 16), "Test 2", "user@example.com")
    
    csv_path = tmp_path / "export.csv"
    
    tracker.export_to_csv(csv_path)
    
    assert csv_path.exists()
    
    content = csv_path.read_text()
    assert "work_item_id" in content
    assert "123" in content
    assert "124" in content


def test_export_to_csv_with_filters(tracker, tmp_path):
    """Test exporting with filters"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user1@example.com")
    tracker.add_entry(124, 4.0, date.today(), "Test 2", "user2@example.com")
    
    csv_path = tmp_path / "export.csv"
    
    tracker.export_to_csv(csv_path, user_id="user1@example.com")
    
    content = csv_path.read_text()
    assert "123" in content
    assert "124" not in content


def test_get_summary(tracker):
    """Test getting summary statistics"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user1@example.com")
    tracker.add_entry(123, 4.0, date.today(), "Test 2", "user1@example.com")
    tracker.add_entry(124, 2.0, date.today(), "Test 3", "user2@example.com")
    
    summary = tracker.get_summary()
    
    assert summary['total_entries'] == 3
    assert summary['total_hours'] == 14.0
    assert summary['unsynced_entries'] == 3
    assert len(summary['by_work_item']) == 2
    assert summary['by_work_item'][123]['hours'] == 12.0
    assert len(summary['by_user']) == 2


def test_get_summary_with_filters(tracker):
    """Test summary with filters"""
    tracker.add_entry(123, 8.0, date.today(), "Test 1", "user1@example.com")
    tracker.add_entry(124, 4.0, date.today(), "Test 2", "user2@example.com")
    
    summary = tracker.get_summary(user_id="user1@example.com")
    
    assert summary['total_entries'] == 1
    assert summary['total_hours'] == 8.0


def test_clear_synced_entries(tracker):
    """Test clearing synced entries"""
    entry1 = tracker.add_entry(123, 8.0, date.today(), "Test 1", "user@example.com")
    entry2 = tracker.add_entry(124, 4.0, date.today(), "Test 2", "user@example.com")
    
    entry1.mark_synced()
    tracker._save_entries()
    
    removed = tracker.clear_synced_entries()
    
    assert removed == 1
    assert len(tracker.entries) == 1
    assert tracker.entries[0].work_item_id == 124


def test_persistence_across_instances(temp_storage):
    """Test entries persist across tracker instances"""
    # First instance
    tracker1 = ManualTimeTracker(storage_path=temp_storage)
    tracker1.add_entry(123, 8.0, date.today(), "Test", "user@example.com")
    
    # Second instance
    tracker2 = ManualTimeTracker(storage_path=temp_storage)
    
    assert len(tracker2.entries) == 1
    assert tracker2.entries[0].work_item_id == 123
