"""
Session-based logging functionality
"""

from logging import Logger
from typing import Optional
from .core import LoggerFactory


class SessionLogger:
    """
    Session-based logger with structured logging support
    """

    def __init__(self, tag: str, session_id: str, logger: Optional[Logger] = None):
        """
        Initialize session logger

        Args:
            tag: Logger tag identifier
            session_id: Unique session identifier
            logger: Optional pre-configured logger instance
        """
        self.session_id = session_id
        self.tag = tag

        if logger is None:
            # Create default logger if none provided
            self.logger = LoggerFactory.create_basic_logger(tag)
        else:
            self.logger = logger

    @classmethod
    def create(cls, tag: str, session_id: str) -> "SessionLogger":
        """Factory method to create a basic session logger"""
        return cls(tag, session_id)

    def _format_message(self, event: str, content: str = "", **kwargs) -> str:
        """Format structured log message"""
        parts = [f"session={self.session_id}", f'event="{event}"']

        if content:
            parts.append(f'content="{content}"')

        # Add any additional key-value pairs
        for key, value in kwargs.items():
            if isinstance(value, str):
                parts.append(f'{key}="{value}"')
            else:
                parts.append(f"{key}={value}")

        return " ".join(parts)

    def info(self, event: str, content: str = "", **kwargs):
        """Log info level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).info(message)

    def debug(self, event: str, content: str = "", **kwargs):
        """Log debug level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).debug(message)

    def warning(self, event: str, content: str = "", **kwargs):
        """Log warning level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).warning(message)

    def error(self, event: str, content: str = "", **kwargs):
        """Log error level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).error(message)

    def success(self, event: str, content: str = "", **kwargs):
        """Log success level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).success(message)

    def critical(self, event: str, content: str = "", **kwargs):
        """Log critical level message with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).critical(message)

    def exception(self, event: str, content: str = "", **kwargs):
        """Log exception with session context"""
        message = self._format_message(event, content, **kwargs)
        self.logger.opt(depth=2).exception(message)

    def bind(self, **kwargs):
        """Bind additional context to the logger"""
        self.logger = self.logger.bind(**kwargs)
        return self

    def with_context(self, **kwargs) -> "SessionLogger":
        """Create a new session logger with additional context"""
        new_logger = self.logger.bind(**kwargs)
        return SessionLogger(self.tag, self.session_id, new_logger)
