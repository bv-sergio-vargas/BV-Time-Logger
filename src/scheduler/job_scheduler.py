"""
Job Scheduler - Scheduled execution of time logging workflow
"""

import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Manages scheduled execution of time logging jobs.
    """
    
    def __init__(self):
        """
        Initialize job scheduler.
        """
        self.scheduler = BackgroundScheduler()
        self.jobs: Dict[str, Any] = {}
        self.execution_history: list = []
        
        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        logger.info("[SCHEDULER] Job scheduler initialized")
    
    def schedule_daily_sync(
        self,
        job_func: Callable,
        hour: int = 0,
        minute: int = 0,
        job_id: str = "daily_sync"
    ):
        """
        Schedule daily synchronization job.
        
        Args:
            job_func: Function to execute
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            job_id: Unique job identifier
        """
        trigger = CronTrigger(hour=hour, minute=minute)
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Daily Sync at {hour:02d}:{minute:02d}",
            replace_existing=True
        )
        
        self.jobs[job_id] = {
            'job': job,
            'type': 'daily',
            'schedule': f"{hour:02d}:{minute:02d}",
            'enabled': True
        }
        
        logger.info(
            f"[SCHEDULER] Daily sync scheduled for {hour:02d}:{minute:02d} "
            f"(job_id={job_id})"
        )
    
    def schedule_interval_sync(
        self,
        job_func: Callable,
        hours: int = 0,
        minutes: int = 0,
        job_id: str = "interval_sync"
    ):
        """
        Schedule synchronization at regular intervals.
        
        Args:
            job_func: Function to execute
            hours: Interval in hours
            minutes: Interval in minutes
            job_id: Unique job identifier
        """
        trigger = IntervalTrigger(hours=hours, minutes=minutes)
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Interval Sync every {hours}h {minutes}m",
            replace_existing=True
        )
        
        self.jobs[job_id] = {
            'job': job,
            'type': 'interval',
            'schedule': f"{hours}h {minutes}m",
            'enabled': True
        }
        
        logger.info(
            f"[SCHEDULER] Interval sync scheduled every {hours}h {minutes}m "
            f"(job_id={job_id})"
        )
    
    def schedule_custom(
        self,
        job_func: Callable,
        cron_expression: str,
        job_id: str = "custom_job"
    ):
        """
        Schedule job with custom cron expression.
        
        Args:
            job_func: Function to execute
            cron_expression: Cron expression (e.g., "0 */4 * * *" for every 4 hours)
            job_id: Unique job identifier
        """
        # Parse cron expression
        # Format: minute hour day month day_of_week
        parts = cron_expression.split()
        
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month day_of_week")
        
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Custom Job: {cron_expression}",
            replace_existing=True
        )
        
        self.jobs[job_id] = {
            'job': job,
            'type': 'custom',
            'schedule': cron_expression,
            'enabled': True
        }
        
        logger.info(
            f"[SCHEDULER] Custom job scheduled with cron '{cron_expression}' "
            f"(job_id={job_id})"
        )
    
    def start(self):
        """
        Start the scheduler.
        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[SCHEDULER] Scheduler started")
        else:
            logger.warning("[SCHEDULER] Scheduler already running")
    
    def stop(self, wait: bool = True):
        """
        Stop the scheduler.
        
        Args:
            wait: Wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("[SCHEDULER] Scheduler stopped")
        else:
            logger.warning("[SCHEDULER] Scheduler not running")
    
    def pause_job(self, job_id: str):
        """
        Pause a specific job.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self.jobs:
            self.scheduler.pause_job(job_id)
            self.jobs[job_id]['enabled'] = False
            logger.info(f"[SCHEDULER] Job '{job_id}' paused")
        else:
            logger.warning(f"[SCHEDULER] Job '{job_id}' not found")
    
    def resume_job(self, job_id: str):
        """
        Resume a paused job.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self.jobs:
            self.scheduler.resume_job(job_id)
            self.jobs[job_id]['enabled'] = True
            logger.info(f"[SCHEDULER] Job '{job_id}' resumed")
        else:
            logger.warning(f"[SCHEDULER] Job '{job_id}' not found")
    
    def remove_job(self, job_id: str):
        """
        Remove a job from the scheduler.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"[SCHEDULER] Job '{job_id}' removed")
        else:
            logger.warning(f"[SCHEDULER] Job '{job_id}' not found")
    
    def run_job_now(self, job_id: str):
        """
        Execute a job immediately (on-demand).
        
        Args:
            job_id: Job identifier
        """
        if job_id in self.jobs:
            job = self.jobs[job_id]['job']
            job.modify(next_run_time=datetime.now())
            logger.info(f"[SCHEDULER] Job '{job_id}' scheduled for immediate execution")
        else:
            logger.warning(f"[SCHEDULER] Job '{job_id}' not found")
    
    def get_jobs(self) -> Dict[str, Any]:
        """
        Get list of all scheduled jobs.
        
        Returns:
            Dictionary of job information
        """
        jobs_info = {}
        
        for job_id, job_data in self.jobs.items():
            job = job_data['job']
            jobs_info[job_id] = {
                'name': job.name,
                'type': job_data['type'],
                'schedule': job_data['schedule'],
                'enabled': job_data['enabled'],
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None
            }
        
        return jobs_info
    
    def get_execution_history(self, limit: int = 10) -> list:
        """
        Get recent execution history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of execution records
        """
        return self.execution_history[-limit:]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on scheduler.
        
        Returns:
            Health check results
        """
        health = {
            'status': 'healthy' if self.scheduler.running else 'stopped',
            'running': self.scheduler.running,
            'total_jobs': len(self.jobs),
            'enabled_jobs': sum(1 for j in self.jobs.values() if j['enabled']),
            'paused_jobs': sum(1 for j in self.jobs.values() if not j['enabled']),
            'last_execution': None
        }
        
        if self.execution_history:
            health['last_execution'] = self.execution_history[-1]
        
        return health
    
    def _job_executed_listener(self, event):
        """
        Event listener for job execution.
        
        Args:
            event: APScheduler event
        """
        execution_record = {
            'job_id': event.job_id,
            'timestamp': datetime.now().isoformat(),
            'success': not event.exception,
            'exception': str(event.exception) if event.exception else None
        }
        
        self.execution_history.append(execution_record)
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        if event.exception:
            logger.error(
                f"[SCHEDULER] Job '{event.job_id}' failed: {event.exception}",
                exc_info=True
            )
        else:
            logger.info(f"[SCHEDULER] Job '{event.job_id}' executed successfully")
