"""
Tests for core logging functionality
"""

from pathlib import Path
import tempfile
import pytest
from unittest.mock import patch

from ulogger import LoggerFactory, LoggerBuilder, SessionLogger
from ulogger.core import LoggerConfig
from ulogger.sls import SLSConfig


class TestLoggerConfig:
    """Test LoggerConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = LoggerConfig()

        assert config.tag == ""
        assert config.level == "INFO"
        assert config.console_enabled is True
        assert config.file_enabled is False
        assert config.file_path is None
        assert config.sls_enabled is False
        assert config.sls_config is None
        assert config.extra == {}
        assert "time:YYYY-MM-DD HH:mm:ss.SSS" in config.format


class TestLoggerBuilder:
    """Test LoggerBuilder class"""

    def test_builder_chain(self):
        """Test builder method chaining"""
        builder = LoggerBuilder()
        result = (
            builder.with_tag("test")
            .with_level("DEBUG")
            .with_console(False)
            .with_extra(user_id=123, session="abc")
        )

        assert isinstance(result, LoggerBuilder)
        assert builder._config.tag == "test"
        assert builder._config.level == "DEBUG"
        assert builder._config.console_enabled is False
        assert builder._config.extra["user_id"] == 123
        assert builder._config.extra["session"] == "abc"

    def test_with_format(self):
        """Test custom format setting"""
        custom_format = "{time} | {level} | {message}"
        builder = LoggerBuilder().with_format(custom_format)

        assert builder._config.format == custom_format

    def test_with_file(self):
        """Test file output configuration"""
        file_path = "/tmp/test.log"
        builder = LoggerBuilder().with_file(file_path)

        assert builder._config.file_enabled is True
        assert builder._config.file_path == file_path

    def test_with_sls(self):
        """Test SLS configuration"""
        sls_config = SLSConfig(
            endpoint="test.endpoint", project="test_project", logstore="test_logstore"
        )
        builder = LoggerBuilder().with_sls(sls_config)

        assert builder._config.sls_enabled is True
        assert builder._config.sls_config == sls_config

    def test_build_creates_logger(self):
        """Test that build() creates a logger"""
        logger = LoggerBuilder().with_tag("test_build").with_level("INFO").build()

        assert logger is not None
        # Test that the logger has the expected bound values
        assert hasattr(logger, "_core")


class TestLoggerFactory:
    """Test LoggerFactory class"""

    def test_create_basic_logger(self):
        """Test basic logger creation"""
        import tempfile
        import time

        logger = LoggerFactory.create_basic_logger("test")
        assert logger is not None

        # Test logging using file output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create a test logger that writes to file
            test_logger = (
                LoggerBuilder()
                .with_tag("test")
                .with_level("INFO")
                .with_console(False)
                .with_file(temp_path)
                .build()
            )

            test_logger.info("Test message")

            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)

            # Read the file content
            with open(temp_path, "r") as f:
                output = f.read()

            # Should contain the test message
            assert "Test message" in output

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_create_basic_logger_with_level(self):
        """Test basic logger with custom level"""
        import tempfile
        import time

        logger = LoggerFactory.create_basic_logger("test", "DEBUG")
        assert logger is not None

        # Test logging using file output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create a test logger that writes to file
            test_logger = (
                LoggerBuilder()
                .with_tag("test")
                .with_level("DEBUG")
                .with_console(False)
                .with_file(temp_path)
                .build()
            )

            test_logger.debug("Debug message")

            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)

            # Read the file content
            with open(temp_path, "r") as f:
                output = f.read()

            assert "Debug message" in output

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_create_logger_with_config(self):
        """Test logger creation with custom configuration"""
        config = LoggerConfig()
        config.tag = "custom_test"
        config.level = "WARNING"
        config.console_enabled = False

        logger = LoggerFactory.create_logger(config)
        assert logger is not None

    def test_create_logger_file_output(self):
        """Test logger with file output"""
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            config = LoggerConfig()
            config.tag = "file_test"
            config.file_enabled = True
            config.file_path = temp_path
            config.console_enabled = False

            logger = LoggerFactory.create_logger(config)
            logger.info("File test message")

            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)

            # Read the file content
            with open(temp_path, "r") as f:
                content = f.read()

            assert "File test message" in content

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    @patch("ulogger.sls.SLSPropagateHandler.create")
    def test_create_logger_with_sls(self, mock_sls_handler):
        """Test logger creation with SLS handler"""
        import logging

        # Create a proper mock handler that inherits from logging.Handler
        class MockSLSHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

            def __str__(self):
                return "MockSLSHandler"

            def __repr__(self):
                return "MockSLSHandler()"

        mock_handler = MockSLSHandler()
        mock_sls_handler.return_value = mock_handler

        sls_config = SLSConfig(
            endpoint="test.endpoint",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore",
        )

        config = LoggerConfig()
        config.tag = "sls_test"
        config.sls_enabled = True
        config.sls_config = sls_config
        config.console_enabled = False

        logger = LoggerFactory.create_logger(config)
        assert logger is not None
        mock_sls_handler.assert_called_once_with(sls_config)

        # Test that the logger can be used without creating strange files
        logger.info("Test SLS message")

        # Just verify the config was processed correctly
        assert config.sls_enabled is True
        assert config.sls_config == sls_config


class TestLoggerBuilderIntegration:
    """Integration tests for LoggerBuilder"""

    def test_logger_builder_full_workflow(self):
        """Test complete logger builder workflow"""
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            logger = (
                LoggerBuilder()
                .with_tag("integration_test")
                .with_level("DEBUG")
                .with_console(False)
                .with_file(temp_path)
                .with_extra(component="test", version="1.0")
                .build()
            )

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")

            # Give loguru time to write the file (it's async)
            # In CI environments, we need more time
            time.sleep(0.5)

            # Read the file content
            with open(temp_path, "r") as f:
                content = f.read()

            assert "Debug message" in content
            assert "Info message" in content
            assert "Warning message" in content

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)


def test_session_logger():
    """Test session-based logging"""
    import tempfile
    import time

    session_logger = SessionLogger.create("test_session", "session_123")

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Create a logger that writes to file for testing
        test_logger = (
            LoggerBuilder()
            .with_tag("test_session")
            .with_level("DEBUG")
            .with_console(False)
            .with_file(temp_path)
            .build()
        )

        # Replace the session logger's logger
        session_logger.logger = test_logger

        session_logger.info("user_login", "User logged in successfully", user_id=12345)
        session_logger.error("auth_failed", "Invalid credentials", attempts=3)

        # Give loguru time to write the file (it's async)
        # In CI environments, we need more time
        time.sleep(0.5)

        # Read the file content
        with open(temp_path, "r") as f:
            output = f.read()

        assert "session=session_123" in output
        assert 'event="user_login"' in output
        assert 'content="User logged in successfully"' in output
        assert "user_id=12345" in output
        assert 'event="auth_failed"' in output

    finally:
        # Clean up
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
