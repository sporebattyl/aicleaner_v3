"""
Tests for Unified Logging System
"""

import pytest
import json
import logging
import sys
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, StringIO
from contextlib import redirect_stdout

from utils.unified_logger import (
    CorrelationIDFilter,
    StructuredFormatter,
    UnifiedLogger,
    configure_logging,
    get_logger,
    set_correlation_id,
    set_component,
    set_user_id,
    get_correlation_id,
    clear_context,
    log_context,
    log_performance,
    log_security_event,
    log_api_request,
    configure_ha_addon_logging,
    _context
)


class TestCorrelationIDFilter:
    """Test the CorrelationIDFilter class."""
    
    def test_filter_adds_default_values(self):
        """Test that filter adds default values when no context is set."""
        filter_instance = CorrelationIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        clear_context()
        result = filter_instance.filter(record)
        
        assert result is True
        assert record.correlation_id == 'no-correlation'
        assert record.component == 'unknown'
        assert record.user_id == 'system'
    
    def test_filter_uses_context_values(self):
        """Test that filter uses values from thread-local context."""
        filter_instance = CorrelationIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        set_correlation_id('test-correlation')
        set_component('test-component')
        set_user_id('test-user')
        
        result = filter_instance.filter(record)
        
        assert result is True
        assert record.correlation_id == 'test-correlation'
        assert record.component == 'test-component'
        assert record.user_id == 'test-user'


class TestStructuredFormatter:
    """Test the StructuredFormatter class."""
    
    def test_basic_formatting(self):
        """Test basic log entry formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = 'test-corr'
        record.component = 'test-comp'
        record.user_id = 'test-user'
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry['level'] == 'INFO'
        assert log_entry['message'] == 'Test message'
        assert log_entry['logger'] == 'test.logger'
        assert log_entry['correlation_id'] == 'test-corr'
        assert log_entry['component'] == 'test-comp'
        assert log_entry['user_id'] == 'test-user'
        assert 'timestamp' in log_entry
        assert log_entry['timestamp'].endswith('Z')
    
    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger", level=logging.ERROR, pathname="", lineno=0,
                msg="Error occurred", args=(), exc_info=sys.exc_info()
            )
            record.correlation_id = 'test-corr'
            record.component = 'test-comp'
            record.user_id = 'test-user'
            
            formatted = formatter.format(record)
            log_entry = json.loads(formatted)
            
            assert log_entry['level'] == 'ERROR'
            assert log_entry['message'] == 'Error occurred'
            assert 'exception' in log_entry
            assert log_entry['exception']['type'] == 'ValueError'
            assert log_entry['exception']['message'] == 'Test exception'
            assert isinstance(log_entry['exception']['traceback'], list)
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = 'test-corr'
        record.component = 'test-comp'
        record.user_id = 'test-user'
        record.custom_field = 'custom_value'
        record.another_field = 42
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert 'extra' in log_entry
        assert log_entry['extra']['custom_field'] == 'custom_value'
        assert log_entry['extra']['another_field'] == 42
    
    def test_formatting_exclude_extra_fields(self):
        """Test formatting with extra fields disabled."""
        formatter = StructuredFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        record.correlation_id = 'test-corr'
        record.component = 'test-comp'
        record.user_id = 'test-user'
        record.custom_field = 'custom_value'
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert 'extra' not in log_entry


class TestUnifiedLogger:
    """Test the UnifiedLogger class."""
    
    def test_logger_initialization(self):
        """Test logger initialization with various configurations."""
        logger_instance = UnifiedLogger(
            name="test_logger",
            level=logging.DEBUG,
            console_output=True,
            structured_format=True
        )
        
        logger = logger_instance.get_logger()
        
        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG
        assert logger.propagate is False
        assert len(logger.handlers) == 1
        
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, StructuredFormatter)
        assert len(handler.filters) == 1
        assert isinstance(handler.filters[0], CorrelationIDFilter)
    
    def test_logger_with_file_output(self):
        """Test logger with file output."""
        with patch('logging.FileHandler') as mock_file_handler:
            mock_handler = MagicMock()
            mock_file_handler.return_value = mock_handler
            
            logger_instance = UnifiedLogger(
                name="file_logger",
                file_output="/tmp/test.log",
                console_output=False
            )
            
            logger = logger_instance.get_logger()
            
            mock_file_handler.assert_called_once_with("/tmp/test.log")
            assert len(logger.handlers) == 1
            assert logger.handlers[0] == mock_handler
    
    def test_logger_level_string_conversion(self):
        """Test that string log levels are converted correctly."""
        logger_instance = UnifiedLogger(level="WARNING")
        logger = logger_instance.get_logger()
        
        assert logger.level == logging.WARNING


class TestContextManagement:
    """Test context management functions."""
    
    def test_context_setters_and_getters(self):
        """Test setting and getting context values."""
        clear_context()
        
        set_correlation_id('test-corr-123')
        set_component('test-component')
        set_user_id('test-user')
        
        assert get_correlation_id() == 'test-corr-123'
        assert getattr(_context, 'component', None) == 'test-component'
        assert getattr(_context, 'user_id', None) == 'test-user'
    
    def test_clear_context(self):
        """Test clearing context values."""
        set_correlation_id('test-corr')
        set_component('test-comp')
        set_user_id('test-user')
        
        clear_context()
        
        assert get_correlation_id() == 'no-correlation'
        assert getattr(_context, 'component', None) is None
        assert getattr(_context, 'user_id', None) is None
    
    def test_log_context_manager(self):
        """Test log context manager functionality."""
        clear_context()
        
        with log_context(correlation_id='ctx-123', component='ctx-comp', user_id='ctx-user') as corr_id:
            assert corr_id == 'ctx-123'
            assert get_correlation_id() == 'ctx-123'
            assert getattr(_context, 'component', None) == 'ctx-comp'
            assert getattr(_context, 'user_id', None) == 'ctx-user'
        
        # After context manager, values should be cleared
        assert get_correlation_id() == 'no-correlation'
        assert getattr(_context, 'component', None) is None
        assert getattr(_context, 'user_id', None) is None
    
    def test_log_context_manager_auto_correlation_id(self):
        """Test log context manager with auto-generated correlation ID."""
        clear_context()
        
        with log_context(component='auto-comp') as corr_id:
            assert corr_id is not None
            assert len(corr_id) == 8  # UUID first 8 characters
            assert get_correlation_id() == corr_id
            assert getattr(_context, 'component', None) == 'auto-comp'
    
    def test_log_context_manager_nested(self):
        """Test nested log context managers."""
        clear_context()
        
        with log_context(correlation_id='outer', component='outer-comp'):
            assert get_correlation_id() == 'outer'
            assert getattr(_context, 'component', None) == 'outer-comp'
            
            with log_context(correlation_id='inner', component='inner-comp'):
                assert get_correlation_id() == 'inner'
                assert getattr(_context, 'component', None) == 'inner-comp'
            
            # After inner context, outer context should be restored
            assert get_correlation_id() == 'outer'
            assert getattr(_context, 'component', None) == 'outer-comp'


class TestSpecializedLogging:
    """Test specialized logging functions."""
    
    def test_log_performance(self):
        """Test performance logging."""
        with patch('utils.unified_logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_performance("test_operation", 1.234, records_processed=100, status="success")
            
            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args
            
            assert "Performance: test_operation completed in 1.234s" in args[0]
            assert 'extra' in kwargs
            assert kwargs['extra']['operation'] == 'test_operation'
            assert kwargs['extra']['duration_seconds'] == 1.234
            assert kwargs['extra']['performance_log'] is True
            assert kwargs['extra']['records_processed'] == 100
            assert kwargs['extra']['status'] == 'success'
    
    def test_log_security_event(self):
        """Test security event logging."""
        with patch('utils.unified_logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Test critical security event
            log_security_event(
                "unauthorized_access",
                "critical",
                {"user": "admin", "action": "login"},
                ip_address="192.168.1.1"
            )
            
            mock_logger.error.assert_called_once()
            args, kwargs = mock_logger.error.call_args
            
            assert "Security Event: unauthorized_access" in args[0]
            assert 'extra' in kwargs
            assert kwargs['extra']['security_event'] is True
            assert kwargs['extra']['event_type'] == 'unauthorized_access'
            assert kwargs['extra']['severity'] == 'critical'
            assert kwargs['extra']['details']['user'] == 'admin'
            assert kwargs['extra']['ip_address'] == '192.168.1.1'
    
    def test_log_security_event_severity_levels(self):
        """Test security event logging with different severity levels."""
        with patch('utils.unified_logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Test different severity levels
            log_security_event("high_event", "high", {})
            mock_logger.error.assert_called()
            
            log_security_event("medium_event", "medium", {})
            mock_logger.warning.assert_called()
            
            log_security_event("low_event", "low", {})
            mock_logger.info.assert_called()
    
    def test_log_api_request(self):
        """Test API request logging."""
        with patch('utils.unified_logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_api_request(
                "GET", "/api/v1/data", 200, 0.123,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
            
            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args
            
            assert "API GET /api/v1/data - 200" in args[0]
            assert 'extra' in kwargs
            assert kwargs['extra']['api_request'] is True
            assert kwargs['extra']['method'] == 'GET'
            assert kwargs['extra']['path'] == '/api/v1/data'
            assert kwargs['extra']['status_code'] == 200
            assert kwargs['extra']['duration_seconds'] == 0.123
            assert kwargs['extra']['ip_address'] == '127.0.0.1'
            assert kwargs['extra']['user_agent'] == 'TestAgent/1.0'
    
    def test_log_api_request_status_levels(self):
        """Test API request logging with different status codes."""
        with patch('utils.unified_logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Test different status codes
            log_api_request("GET", "/api/success", 200, 0.1)
            mock_logger.info.assert_called()
            
            log_api_request("GET", "/api/notfound", 404, 0.1)
            mock_logger.warning.assert_called()
            
            log_api_request("GET", "/api/error", 500, 0.1)
            mock_logger.error.assert_called()


class TestHAAddonConfiguration:
    """Test Home Assistant addon specific configuration."""
    
    def test_configure_ha_addon_logging(self):
        """Test HA addon logging configuration."""
        with patch('utils.unified_logger.configure_logging') as mock_configure:
            mock_unified_logger = MagicMock()
            mock_configure.return_value = mock_unified_logger
            
            result = configure_ha_addon_logging(log_level="DEBUG", enable_debug=True)
            
            mock_configure.assert_called_once_with(
                name="aicleaner",
                level=logging.DEBUG,
                console_output=True,
                file_output=None,
                structured_format=True
            )
            assert result == mock_unified_logger
    
    def test_configure_ha_addon_logging_no_debug(self):
        """Test HA addon logging without debug enabled."""
        with patch('utils.unified_logger.configure_logging') as mock_configure:
            mock_unified_logger = MagicMock()
            mock_configure.return_value = mock_unified_logger
            
            result = configure_ha_addon_logging(log_level="INFO", enable_debug=False)
            
            mock_configure.assert_called_once_with(
                name="aicleaner",
                level=logging.INFO,
                console_output=True,
                file_output=None,
                structured_format=True
            )


class TestGlobalConfiguration:
    """Test global configuration functions."""
    
    def test_configure_logging_global(self):
        """Test global logging configuration."""
        # Reset global logger
        import utils.unified_logger
        utils.unified_logger._global_logger = None
        
        result = configure_logging(name="test_global", level="WARNING")
        
        assert isinstance(result, UnifiedLogger)
        assert result.get_logger().name == "test_global"
        assert result.get_logger().level == logging.WARNING
        
        # Test that get_logger returns the global instance
        global_logger = get_logger()
        assert global_logger == result.get_logger()
    
    def test_get_logger_fallback(self):
        """Test get_logger fallback when no global logger is configured."""
        # Reset global logger
        import utils.unified_logger
        utils.unified_logger._global_logger = None
        
        logger = get_logger()
        
        assert logger.name == "aicleaner"
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1
    
    def test_get_logger_with_name(self):
        """Test get_logger with specific name."""
        logger = get_logger("specific.logger")
        
        assert logger.name == "specific.logger"


class TestComponentLoggers:
    """Test component-specific logger factories."""
    
    def test_component_logger_factories(self):
        """Test that component logger factories set correct context."""
        from utils.unified_logger import (
            get_ai_logger, get_security_logger, get_zone_logger,
            get_device_logger, get_config_logger, get_api_logger
        )
        
        # Note: These functions use log_context, so we need to test the context setting
        # Since the context is set within the function, we'll test the logger names
        
        ai_logger = get_ai_logger()
        assert ai_logger.name == "aicleaner.ai"
        
        security_logger = get_security_logger()
        assert security_logger.name == "aicleaner.security"
        
        zone_logger = get_zone_logger()
        assert zone_logger.name == "aicleaner.zones"
        
        device_logger = get_device_logger()
        assert device_logger.name == "aicleaner.devices"
        
        config_logger = get_config_logger()
        assert config_logger.name == "aicleaner.config"
        
        api_logger = get_api_logger()
        assert api_logger.name == "aicleaner.api"