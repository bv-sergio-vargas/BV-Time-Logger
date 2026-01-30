"""
Tests for logger utility
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.logger import setup_logger, get_logger, log_spanish_error, log_spanish_info


def test_setup_logger_creates_log_directory(tmp_path):
    """Test logger creates logs directory"""
    with patch('src.utils.logger.Path') as mock_path:
        mock_logs_dir = MagicMock()
        mock_path.return_value = mock_logs_dir
        
        setup_logger()
        
        mock_logs_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_setup_logger_returns_root_logger():
    """Test setup_logger returns configured logger"""
    logger = setup_logger()
    
    assert logger is not None
    assert logger.name == 'src'


def test_get_logger_returns_module_logger():
    """Test get_logger returns module-specific logger"""
    logger = get_logger(__name__)
    
    assert logger is not None
    assert logger.name == __name__


def test_log_spanish_error():
    """Test logging Spanish error message"""
    with patch('src.utils.logger.logger') as mock_logger:
        log_spanish_error("Error de prueba")
        
        mock_logger.error.assert_called_once_with("Error de prueba")


def test_log_spanish_info():
    """Test logging Spanish info message"""
    with patch('src.utils.logger.logger') as mock_logger:
        log_spanish_info("Información de prueba")
        
        mock_logger.info.assert_called_once_with("Información de prueba")


def test_logger_level_configuration():
    """Test logger levels are set correctly"""
    logger = setup_logger()
    
    # Root logger should be INFO or DEBUG
    assert logger.level in [logging.DEBUG, logging.INFO]


def test_logger_has_handlers():
    """Test logger has configured handlers"""
    logger = setup_logger()
    
    # Should have at least 1 handler (file or console)
    assert len(logger.handlers) > 0


def test_logger_utf8_encoding(tmp_path):
    """Test logger handles UTF-8 characters"""
    # This ensures Spanish characters work correctly
    logger = get_logger(__name__)
    
    try:
        logger.info("Información con ñ, á, é, í, ó, ú")
        log_spanish_info("Prueba de caracteres especiales: ñ, á, é")
    except UnicodeEncodeError:
        pytest.fail("Logger failed to handle UTF-8 characters")


def test_multiple_loggers_independent():
    """Test multiple module loggers are independent"""
    logger1 = get_logger('module1')
    logger2 = get_logger('module2')
    
    assert logger1.name != logger2.name
    assert logger1 is not logger2
