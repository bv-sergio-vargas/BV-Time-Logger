"""
__init__.py for utils package
"""

from .logger import setup_logger, get_logger, log_spanish_error, log_spanish_info

__all__ = ['setup_logger', 'get_logger', 'log_spanish_error', 'log_spanish_info']
