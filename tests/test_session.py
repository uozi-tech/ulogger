"""
Tests for session-based logging functionality
"""

import pytest

from ulogger.session import SessionLogger
from ulogger import LoggerFactory
from pathlib import Path


class TestSessionLogger:
    """Test SessionLogger class"""
    
    def test_session_logger_init(self):
        """Test SessionLogger initialization"""
        session_logger = SessionLogger("test_tag", "session_123")
        
        assert session_logger.tag == "test_tag"
        assert session_logger.session_id == "session_123"
        assert session_logger.logger is not None
    
    def test_session_logger_init_custom_logger(self):
        """Test SessionLogger initialization with custom logger"""
        custom_logger = LoggerFactory.create_basic_logger("custom")
        session_logger = SessionLogger("test_tag", "session_123", custom_logger)
        
        assert session_logger.logger == custom_logger
    
    def test_create_factory_method(self):
        """Test SessionLogger.create factory method"""
        session_logger = SessionLogger.create("test_tag", "session_456")
        
        assert isinstance(session_logger, SessionLogger)
        assert session_logger.tag == "test_tag"
        assert session_logger.session_id == "session_456"
    
    def test_format_message_basic(self):
        """Test basic message formatting"""
        session_logger = SessionLogger("test", "sess_123")
        message = session_logger._format_message("user_login")
        
        expected = 'session=sess_123 event="user_login"'
        assert message == expected
    
    def test_format_message_with_content(self):
        """Test message formatting with content"""
        session_logger = SessionLogger("test", "sess_123")
        message = session_logger._format_message("user_login", "Login successful")
        
        expected = 'session=sess_123 event="user_login" content="Login successful"'
        assert message == expected
    
    def test_format_message_with_kwargs(self):
        """Test message formatting with keyword arguments"""
        session_logger = SessionLogger("test", "sess_123")
        message = session_logger._format_message("user_login", "Login successful", 
                                                user_id=12345, ip="192.168.1.1")
        
        assert 'session=sess_123' in message
        assert 'event="user_login"' in message
        assert 'content="Login successful"' in message
        assert 'user_id=12345' in message
        assert 'ip="192.168.1.1"' in message
    
    def test_format_message_string_and_numeric_values(self):
        """Test message formatting with different value types"""
        session_logger = SessionLogger("test", "sess_123")
        message = session_logger._format_message("test_event", "",
                                                string_val="text",
                                                int_val=42,
                                                float_val=3.14,
                                                bool_val=True)
        
        assert 'string_val="text"' in message
        assert 'int_val=42' in message
        assert 'float_val=3.14' in message
        assert 'bool_val=True' in message


class TestSessionLoggerMethods:
    """Test SessionLogger logging methods"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.session_logger = SessionLogger.create("test_session", "session_123")
    
    def capture_log_output(self, log_method, *args, **kwargs):
        """Helper method to capture log output"""
        import tempfile
        import time
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a logger that writes to file for testing
            from ulogger import LoggerBuilder
            test_logger = (LoggerBuilder()
                          .with_tag("test_session")
                          .with_level("DEBUG")
                          .with_console(False)
                          .with_file(temp_path)
                          .build())
            
            # Replace the session logger's logger with our test logger
            original_logger = self.session_logger.logger
            self.session_logger.logger = test_logger
            
            # Call the log method
            log_method(*args, **kwargs)
            
            # Restore original logger
            self.session_logger.logger = original_logger
            
            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)
            
            # Read the file content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            return content
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
    
    def test_info_logging(self):
        """Test info level logging"""
        output = self.capture_log_output(
            self.session_logger.info,
            "user_login", "User logged in successfully", user_id=12345
        )
        
        assert "session=session_123" in output
        assert 'event="user_login"' in output
        assert 'content="User logged in successfully"' in output
        assert "user_id=12345" in output
        assert "INFO" in output
    
    def test_debug_logging(self):
        """Test debug level logging"""
        # Create logger with DEBUG level
        debug_session = SessionLogger("debug_test", "debug_session")
        debug_session.logger = LoggerFactory.create_basic_logger("debug", "DEBUG")
        
        output = self.capture_log_output(
            debug_session.debug,
            "debug_event", "Debug information"
        )
        
        assert "session=debug_session" in output
        assert 'event="debug_event"' in output
        assert "DEBUG" in output
    
    def test_warning_logging(self):
        """Test warning level logging"""
        output = self.capture_log_output(
            self.session_logger.warning,
            "performance_warning", "Slow response time", response_time=2.5
        )
        
        assert "session=session_123" in output
        assert 'event="performance_warning"' in output
        assert "response_time=2.5" in output
        assert "WARNING" in output
    
    def test_error_logging(self):
        """Test error level logging"""
        output = self.capture_log_output(
            self.session_logger.error,
            "auth_failed", "Invalid credentials", attempts=3
        )
        
        assert "session=session_123" in output
        assert 'event="auth_failed"' in output
        assert "attempts=3" in output
        assert "ERROR" in output
    
    def test_success_logging(self):
        """Test success level logging"""
        output = self.capture_log_output(
            self.session_logger.success,
            "payment_completed", "Payment processed", amount=100.00
        )
        
        assert "session=session_123" in output
        assert 'event="payment_completed"' in output
        assert "amount=100.0" in output
        assert "SUCCESS" in output
    
    def test_critical_logging(self):
        """Test critical level logging"""
        output = self.capture_log_output(
            self.session_logger.critical,
            "system_failure", "Database connection lost"
        )
        
        assert "session=session_123" in output
        assert 'event="system_failure"' in output
        assert "CRITICAL" in output
    
    def test_exception_logging(self):
        """Test exception logging"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            output = self.capture_log_output(
                self.session_logger.exception,
                "exception_occurred", "An error occurred"
            )
            
            assert "session=session_123" in output
            assert 'event="exception_occurred"' in output
            assert "ERROR" in output  # Exception logging uses ERROR level
    
    def test_logging_without_content(self):
        """Test logging without content parameter"""
        output = self.capture_log_output(
            self.session_logger.info,
            "simple_event"
        )
        
        assert "session=session_123" in output
        assert 'event="simple_event"' in output
        assert "content=" not in output  # No content should be included
    
    def test_logging_with_empty_content(self):
        """Test logging with empty content"""
        output = self.capture_log_output(
            self.session_logger.info,
            "empty_content_event", ""
        )
        
        assert "session=session_123" in output
        assert 'event="empty_content_event"' in output
        assert "content=" not in output  # Empty content should not be included


class TestSessionLoggerContext:
    """Test SessionLogger context management"""
    
    def test_bind_method(self):
        """Test bind method"""
        session_logger = SessionLogger.create("test", "session_123")
        bound_logger = session_logger.bind(component="auth", version="1.0")
        
        # Should return the same instance (modified in-place)
        assert bound_logger == session_logger
    
    def test_with_context_method(self):
        """Test with_context method"""
        original_session = SessionLogger.create("test", "session_123")
        new_session = original_session.with_context(component="payment", request_id="req_456")
        
        # Should return a new instance
        assert isinstance(new_session, SessionLogger)
        assert new_session != original_session
        assert new_session.tag == original_session.tag
        assert new_session.session_id == original_session.session_id


class TestSessionLoggerIntegration:
    """Integration tests for SessionLogger"""
    
    def test_real_world_logging_scenario(self):
        """Test a real-world logging scenario"""
        import tempfile
        import time
        from pathlib import Path
        
        session_logger = SessionLogger.create("web_app", "user_session_789")
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a logger that writes to file for testing
            from ulogger import LoggerBuilder
            test_logger = (LoggerBuilder()
                          .with_tag("web_app")
                          .with_level("DEBUG")
                          .with_console(False)
                          .with_file(temp_path)
                          .build())
            
            # Replace the session logger's logger
            session_logger.logger = test_logger
            
            # Simulate a user session flow
            session_logger.info("session_start", "User session initiated", user_id="user_123")
            session_logger.info("page_view", "Homepage viewed", page="/home", load_time=0.25)
            session_logger.warning("slow_query", "Database query took longer than expected", 
                                 query_time=1.5, table="users")
            session_logger.success("login", "User successfully logged in", 
                                  user_id="user_123", method="oauth")
            session_logger.error("payment_failed", "Payment processing failed", 
                                amount=99.99, error_code="CARD_DECLINED")
            session_logger.info("session_end", "User session ended", duration=1800)
            
            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)
            
            # Read the file content
            with open(temp_path, 'r') as f:
                output = f.read()
        
            # Verify all events are logged with correct session ID
            events = ["session_start", "page_view", "slow_query", "login", "payment_failed", "session_end"]
            for event in events:
                assert f'event="{event}"' in output
                assert "session=user_session_789" in output
            
            # Verify specific details
            assert "user_id=\"user_123\"" in output
            assert "load_time=0.25" in output
            assert "query_time=1.5" in output
            assert "amount=99.99" in output
            assert "duration=1800" in output
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
    
    def test_multiple_session_loggers(self):
        """Test multiple session loggers don't interfere"""
        import tempfile
        import time
        from pathlib import Path
        
        session1 = SessionLogger.create("app1", "session_001")
        session2 = SessionLogger.create("app2", "session_002")
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a shared logger that writes to file for testing
            from ulogger import LoggerBuilder
            test_logger = (LoggerBuilder()
                          .with_tag("multi_session")
                          .with_level("DEBUG")
                          .with_console(False)
                          .with_file(temp_path)
                          .build())
            
            # Replace both session loggers' logger
            session1.logger = test_logger
            session2.logger = test_logger
            
            session1.info("event1", "First session event")
            session2.info("event2", "Second session event")
            
            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)
            
            # Read the file content
            with open(temp_path, 'r') as f:
                output = f.read()
        
            assert "session=session_001" in output
            assert "session=session_002" in output
            assert 'event="event1"' in output
            assert 'event="event2"' in output
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__]) 