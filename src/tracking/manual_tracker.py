"""
Manual Time Tracker
Allows manual entry and import of execution hours not related to meetings.
"""

import csv
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class TimeEntry:
    """Represents a manual time entry"""
    
    def __init__(
        self,
        work_item_id: int,
        hours: float,
        date: date,
        description: str,
        user_id: str,
        entry_id: Optional[str] = None
    ):
        """
        Initialize a time entry
        
        Args:
            work_item_id: Azure DevOps work item ID
            hours: Number of hours worked
            date: Date of work
            description: Description of work performed
            user_id: User who performed the work
            entry_id: Unique identifier (auto-generated if None)
        """
        self.entry_id = entry_id or self._generate_id()
        self.work_item_id = work_item_id
        self.hours = hours
        self.date = date if isinstance(date, str) else date.isoformat()
        self.description = description
        self.user_id = user_id
        self.created_at = datetime.utcnow().isoformat()
        self.synced = False
        self.synced_at: Optional[str] = None
    
    @staticmethod
    def _generate_id() -> str:
        """Generate unique entry ID"""
        return f"ENTRY-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'entry_id': self.entry_id,
            'work_item_id': self.work_item_id,
            'hours': self.hours,
            'date': self.date,
            'description': self.description,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'synced': self.synced,
            'synced_at': self.synced_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeEntry':
        """Create from dictionary"""
        entry = cls(
            work_item_id=data['work_item_id'],
            hours=data['hours'],
            date=data['date'],
            description=data['description'],
            user_id=data['user_id'],
            entry_id=data.get('entry_id')
        )
        entry.created_at = data.get('created_at', entry.created_at)
        entry.synced = data.get('synced', False)
        entry.synced_at = data.get('synced_at')
        return entry
    
    def mark_synced(self):
        """Mark entry as synced"""
        self.synced = True
        self.synced_at = datetime.utcnow().isoformat()
    
    def __repr__(self) -> str:
        return (f"TimeEntry(id={self.entry_id}, work_item={self.work_item_id}, "
                f"hours={self.hours}, date={self.date}, synced={self.synced})")


class ManualTimeTracker:
    """
    Manages manual time entries
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize manual time tracker
        
        Args:
            storage_path: Path to JSON storage file (default: data/manual_entries.json)
        """
        self.storage_path = storage_path or Path("data/manual_entries.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[TimeEntry] = []
        self._load_entries()
        logger.info(f"ManualTimeTracker initialized with {len(self.entries)} entries")
    
    def _load_entries(self):
        """Load entries from storage"""
        if not self.storage_path.exists():
            logger.info(f"No existing storage found at {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.entries = [TimeEntry.from_dict(e) for e in data.get('entries', [])]
            logger.info(f"Loaded {len(self.entries)} entries from storage")
        except Exception as e:
            logger.error(f"Failed to load entries: {e}")
            raise
    
    def _save_entries(self):
        """Save entries to storage"""
        try:
            data = {
                'last_updated': datetime.utcnow().isoformat(),
                'entries': [e.to_dict() for e in self.entries]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.entries)} entries to storage")
        except Exception as e:
            logger.error(f"Failed to save entries: {e}")
            raise
    
    def add_entry(
        self,
        work_item_id: int,
        hours: float,
        date: date,
        description: str,
        user_id: str
    ) -> TimeEntry:
        """
        Add a manual time entry
        
        Args:
            work_item_id: Azure DevOps work item ID
            hours: Number of hours worked
            date: Date of work
            description: Description of work
            user_id: User who performed work
        
        Returns:
            Created TimeEntry
        
        Raises:
            ValueError: If validation fails
        """
        # Validation
        if hours <= 0:
            raise ValueError("Hours must be positive")
        if hours > 24:
            raise ValueError("Hours cannot exceed 24 per day")
        if not work_item_id or work_item_id <= 0:
            raise ValueError("Invalid work item ID")
        if not description or not description.strip():
            raise ValueError("Description is required")
        if not user_id or not user_id.strip():
            raise ValueError("User ID is required")
        
        entry = TimeEntry(
            work_item_id=work_item_id,
            hours=hours,
            date=date,
            description=description.strip(),
            user_id=user_id.strip()
        )
        
        self.entries.append(entry)
        self._save_entries()
        logger.info(f"Added entry: {entry}")
        return entry
    
    def get_entries(
        self,
        work_item_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        synced: Optional[bool] = None
    ) -> List[TimeEntry]:
        """
        Get entries with optional filters
        
        Args:
            work_item_id: Filter by work item ID
            user_id: Filter by user
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            synced: Filter by sync status
        
        Returns:
            Filtered list of entries
        """
        filtered = self.entries
        
        if work_item_id is not None:
            filtered = [e for e in filtered if e.work_item_id == work_item_id]
        
        if user_id is not None:
            filtered = [e for e in filtered if e.user_id == user_id]
        
        if start_date is not None:
            start_str = start_date.isoformat()
            filtered = [e for e in filtered if e.date >= start_str]
        
        if end_date is not None:
            end_str = end_date.isoformat()
            filtered = [e for e in filtered if e.date <= end_str]
        
        if synced is not None:
            filtered = [e for e in filtered if e.synced == synced]
        
        return filtered
    
    def get_unsynced_entries(self) -> List[TimeEntry]:
        """Get all unsynced entries"""
        return self.get_entries(synced=False)
    
    def mark_entry_synced(self, entry_id: str):
        """
        Mark entry as synced
        
        Args:
            entry_id: Entry ID to mark
        
        Raises:
            ValueError: If entry not found
        """
        entry = next((e for e in self.entries if e.entry_id == entry_id), None)
        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")
        
        entry.mark_synced()
        self._save_entries()
        logger.info(f"Marked entry as synced: {entry_id}")
    
    def delete_entry(self, entry_id: str):
        """
        Delete an entry
        
        Args:
            entry_id: Entry ID to delete
        
        Raises:
            ValueError: If entry not found
        """
        entry = next((e for e in self.entries if e.entry_id == entry_id), None)
        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")
        
        self.entries.remove(entry)
        self._save_entries()
        logger.info(f"Deleted entry: {entry_id}")
    
    def import_from_csv(self, csv_path: Path) -> List[TimeEntry]:
        """
        Import entries from CSV file
        
        CSV format:
        work_item_id,hours,date,description,user_id
        
        Args:
            csv_path: Path to CSV file
        
        Returns:
            List of imported entries
        
        Raises:
            ValueError: If CSV validation fails
        """
        if not csv_path.exists():
            raise ValueError(f"CSV file not found: {csv_path}")
        
        imported = []
        errors = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                required_cols = {'work_item_id', 'hours', 'date', 'description', 'user_id'}
                if not required_cols.issubset(set(reader.fieldnames or [])):
                    raise ValueError(f"CSV must have columns: {required_cols}")
                
                for i, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    try:
                        work_item_id = int(row['work_item_id'])
                        hours = float(row['hours'])
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                        description = row['description']
                        user_id = row['user_id']
                        
                        entry = self.add_entry(
                            work_item_id=work_item_id,
                            hours=hours,
                            date=date_obj,
                            description=description,
                            user_id=user_id
                        )
                        imported.append(entry)
                    
                    except Exception as e:
                        errors.append(f"Row {i}: {str(e)}")
                        logger.warning(f"Failed to import row {i}: {e}")
            
            if errors:
                logger.warning(f"Imported {len(imported)} entries with {len(errors)} errors")
            else:
                logger.info(f"Successfully imported {len(imported)} entries from CSV")
            
            return imported
        
        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            raise
    
    def export_to_csv(
        self,
        csv_path: Path,
        work_item_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        synced: Optional[bool] = None
    ):
        """
        Export entries to CSV
        
        Args:
            csv_path: Output CSV path
            work_item_id: Filter by work item ID
            user_id: Filter by user
            start_date: Filter by start date
            end_date: Filter by end date
            synced: Filter by sync status
        """
        entries = self.get_entries(
            work_item_id=work_item_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            synced=synced
        )
        
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['entry_id', 'work_item_id', 'hours', 'date', 
                             'description', 'user_id', 'created_at', 'synced', 'synced_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for entry in entries:
                    writer.writerow(entry.to_dict())
            
            logger.info(f"Exported {len(entries)} entries to {csv_path}")
        
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise
    
    def get_summary(
        self,
        work_item_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics
        
        Returns:
            Dictionary with summary data
        """
        entries = self.get_entries(
            work_item_id=work_item_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        total_hours = sum(e.hours for e in entries)
        synced_entries = [e for e in entries if e.synced]
        unsynced_entries = [e for e in entries if not e.synced]
        
        by_work_item = {}
        for entry in entries:
            wi_id = entry.work_item_id
            if wi_id not in by_work_item:
                by_work_item[wi_id] = {'count': 0, 'hours': 0}
            by_work_item[wi_id]['count'] += 1
            by_work_item[wi_id]['hours'] += entry.hours
        
        by_user = {}
        for entry in entries:
            uid = entry.user_id
            if uid not in by_user:
                by_user[uid] = {'count': 0, 'hours': 0}
            by_user[uid]['count'] += 1
            by_user[uid]['hours'] += entry.hours
        
        return {
            'total_entries': len(entries),
            'total_hours': total_hours,
            'synced_entries': len(synced_entries),
            'unsynced_entries': len(unsynced_entries),
            'by_work_item': by_work_item,
            'by_user': by_user
        }
    
    def clear_synced_entries(self):
        """Remove all synced entries from storage"""
        before_count = len(self.entries)
        self.entries = [e for e in self.entries if not e.synced]
        self._save_entries()
        removed = before_count - len(self.entries)
        logger.info(f"Cleared {removed} synced entries")
        return removed
