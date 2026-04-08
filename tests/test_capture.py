"""
Tests for output capture functionality
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from ulogger.capture import CaptureOutput, capture_output
from ulogger import LoggerFactory


class TestCaptureOutput:
    """Test CaptureOutput class"""

    def test_capture_output_init_default_logger(self):
        """Test CaptureOutput initialization with default logger"""
        capture = CaptureOutput("test_tag")

        assert capture.tag == "test_tag"
        assert capture.logger is not None
        assert capture.stdout_content == ""
        assert capture.stderr_content == ""

    def test_capture_output_init_custom_logger(self):
        """Test CaptureOutput initialization with custom logger"""
        custom_logger = LoggerFactory.create_basic_logger("custom")
        capture = CaptureOutput("test_tag", custom_logger)

        assert capture.tag == "test_tag"
        assert capture.logger == custom_logger

    def test_capture_stdout(self):
        """Test capturing stdout"""
        with CaptureOutput("test_capture") as capture:
            print("Hello, stdout!")
            print("Another stdout line")

        assert "Hello, stdout!" in capture.stdout_content
        assert "Another stdout line" in capture.stdout_content
        assert capture.stderr_content == ""

    def test_capture_stderr(self):
        """Test capturing stderr"""
        with CaptureOutput("test_capture") as capture:
            print("Error message", file=sys.stderr)
            print("Another error", file=sys.stderr)

        assert "Error message" in capture.stderr_content
        assert "Another error" in capture.stderr_content
        assert capture.stdout_content == ""

    def test_capture_both_stdout_stderr(self):
        """Test capturing both stdout and stderr"""
        with CaptureOutput("test_capture") as capture:
            print("Standard output")
            print("Error output", file=sys.stderr)

        assert "Standard output" in capture.stdout_content
        assert "Error output" in capture.stderr_content

    def test_streams_restored_after_capture(self):
        """Test that original streams are restored after capture"""
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with CaptureOutput("test_capture") as capture:  # noqa: F841
            # Streams should be redirected during capture
            assert sys.stdout != original_stdout
            assert sys.stderr != original_stderr

        # Streams should be restored after capture
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr

    def test_capture_with_exception(self):
        """Test that streams are restored even if exception occurs"""
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            with CaptureOutput("test_capture") as capture:
                print("Before exception")
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Streams should still be restored
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr
        assert "Before exception" in capture.stdout_content

    def test_empty_capture(self):
        """Test capture with no output"""
        with CaptureOutput("test_capture") as capture:
            pass  # No output

        assert capture.stdout_content == ""
        assert capture.stderr_content == ""

    def test_whitespace_handling(self):
        """Test handling of whitespace in captured output"""
        with CaptureOutput("test_capture") as capture:
            print("   ")  # Only whitespace
            print("", file=sys.stderr)  # Empty line

        # Captured content should include whitespace
        assert capture.stdout_content.strip() == ""
        assert capture.stderr_content.strip() == ""

    @patch("ulogger.capture.LoggerFactory.create_basic_logger")
    def test_logging_captured_content(self, mock_create_logger):
        """Test that captured content is logged"""
        mock_logger = MagicMock()
        mock_create_logger.return_value = mock_logger

        with CaptureOutput("test_capture") as capture:  # noqa: F841
            print("Test stdout message")
            print("Test stderr message", file=sys.stderr)

        # Verify logger was called with captured content
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_called_once()

        # Check the logged messages contain the captured content
        info_call_args = mock_logger.info.call_args[0][0]
        error_call_args = mock_logger.error.call_args[0][0]

        assert "Test stdout message" in info_call_args
        assert "Test stderr message" in error_call_args


class TestCaptureOutputContextManager:
    """Test the capture_output context manager function"""

    def test_capture_output_function(self):
        """Test the capture_output context manager function"""
        with capture_output("test_tag") as capture:
            print("Function test")
            assert isinstance(capture, CaptureOutput)
            assert capture.tag == "test_tag"

        assert "Function test" in capture.stdout_content

    def test_capture_output_function_with_custom_logger(self):
        """Test capture_output function with custom logger"""
        custom_logger = LoggerFactory.create_basic_logger("custom")

        with capture_output("test_tag", custom_logger) as capture:
            print("Custom logger test")
            assert capture.logger == custom_logger

        assert "Custom logger test" in capture.stdout_content

    def test_multiple_captures(self):
        """Test multiple sequential captures"""
        # First capture
        with capture_output("first") as capture1:
            print("First capture")

        # Second capture
        with capture_output("second") as capture2:
            print("Second capture")

        assert "First capture" in capture1.stdout_content
        assert "Second capture" in capture2.stdout_content
        assert capture1.stdout_content != capture2.stdout_content

    def test_nested_captures(self):
        """Test nested capture contexts"""
        with capture_output("outer") as outer_capture:
            print("Outer message")

            with capture_output("inner") as inner_capture:
                print("Inner message")

            # Inner capture should have captured the inner message
            assert "Inner message" in inner_capture.stdout_content
            assert "Outer message" not in inner_capture.stdout_content

        # Outer capture should have captured only the outer message
        # because stdout was redirected to inner capture during inner context
        assert "Outer message" in outer_capture.stdout_content


class TestCaptureOutputPerformance:
    """Test performance aspects of CaptureOutput"""

    def test_large_output_capture(self):
        """Test capturing large amounts of output"""
        large_text = "x" * 10000

        with capture_output("large_test") as capture:
            print(large_text)

        assert large_text in capture.stdout_content
        assert len(capture.stdout_content) >= 10000

    def test_many_small_outputs(self):
        """Test capturing many small outputs"""
        with capture_output("many_small") as capture:
            for i in range(100):
                print(f"Line {i}")

        for i in range(100):
            assert f"Line {i}" in capture.stdout_content


if __name__ == "__main__":
    pytest.main([__file__])
