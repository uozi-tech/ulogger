"""
Output capture functionality for logging
"""

import io
import sys
from contextlib import contextmanager
from typing import Optional, TextIO, Generator
from .core import LoggerFactory
from logging import Logger


class CaptureOutput:
    """
    Context manager for capturing stdout/stderr and logging the output
    """

    def __init__(self, tag: str, logger: Optional[Logger] = None):
        """
        Initialize output capture

        Args:
            tag: Logger tag identifier
            logger: Optional pre-configured logger instance
        """
        self.tag = tag

        if logger is None:
            self.logger = LoggerFactory.create_basic_logger(tag)
        else:
            self.logger = logger

        # Storage for captured output
        self._stdout_buffer: Optional[io.StringIO] = None
        self._stderr_buffer: Optional[io.StringIO] = None

        # Original streams
        self._original_stdout: Optional[TextIO] = None
        self._original_stderr: Optional[TextIO] = None

        # Captured output
        self.stdout_content: str = ""
        self.stderr_content: str = ""

    def __enter__(self):
        """Start capturing output"""
        self._stdout_buffer = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._stdout_buffer

        self._stderr_buffer = io.StringIO()
        self._original_stderr = sys.stderr
        sys.stderr = self._stderr_buffer

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stop capturing and log the output"""
        # Restore original streams
        if self._original_stdout:
            sys.stdout = self._original_stdout
            if self._stdout_buffer:
                self.stdout_content = self._stdout_buffer.getvalue()
                self._stdout_buffer.close()

        if self._original_stderr:
            sys.stderr = self._original_stderr
            if self._stderr_buffer:
                self.stderr_content = self._stderr_buffer.getvalue()
                self._stderr_buffer.close()

        # Log captured content
        if self.stdout_content.strip():
            self.logger.info(f"Captured stdout: {self.stdout_content.strip()}")

        if self.stderr_content.strip():
            self.logger.error(f"Captured stderr: {self.stderr_content.strip()}")


@contextmanager
def capture_output(
    tag: str, logger: Optional[Logger] = None
) -> Generator[CaptureOutput, None, None]:
    """
    Context manager for capturing both stdout and stderr

    Args:
        tag: Logger tag identifier
        logger: Optional pre-configured logger instance

    Yields:
        CaptureOutput instance
    """
    with CaptureOutput(tag, logger) as capture:
        yield capture
