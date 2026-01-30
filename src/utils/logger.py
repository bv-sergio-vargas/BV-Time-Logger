"""
Structured Logger - Configurable logging system for BV-Time-Logger
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output (optional, Windows compatible).
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        if sys.platform == 'win32':
            # No colors on Windows unless using Windows Terminal
            return super().format(record)
        
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure the logging system for BV-Time-Logger.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_file: Log file name (defaults to timestamped file)
        enable_console: Enable console logging
        enable_file: Enable file logging
        max_bytes: Maximum size of each log file
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"bv_time_logger_{timestamp}.log"
    
    full_log_path = log_path / log_file
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Define format for logs
    detailed_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    simple_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(simple_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            full_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(detailed_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific log levels for modules
    logging.getLogger('src.auth').setLevel(logging.INFO)
    logging.getLogger('src.clients').setLevel(logging.INFO)
    logging.getLogger('src.core').setLevel(logging.DEBUG)
    logging.getLogger('src.reports').setLevel(logging.INFO)
    logging.getLogger('src.scheduler').setLevel(logging.INFO)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('msal').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    root_logger.info(f"Logging system initialized. Log file: {full_log_path}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function for Spanish error messages
def log_spanish_error(logger: logging.Logger, error_code: str, details: str):
    """
    Log error with Spanish message for operators.
    
    Args:
        logger: Logger instance
        error_code: Error code for tracking
        details: Error details in Spanish
    """
    logger.error(f"[ERROR-{error_code}] {details}")


def log_spanish_info(logger: logging.Logger, message: str):
    """
    Log info message in Spanish for operators.
    
    Args:
        logger: Logger instance
        message: Info message in Spanish
    """
    logger.info(f"[INFO] {message}")
