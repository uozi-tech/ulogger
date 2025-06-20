"""
Universal Logger Package

A flexible logging library built on top of loguru with support for
SLS (Alibaba Cloud Simple Log Service) and session-based logging.
"""

__version__ = "0.1.0"

from .core import LoggerFactory, LoggerBuilder
from .session import SessionLogger
from .capture import CaptureOutput
from .sls import SLSConfig, SLSClient
from logging import Logger

__all__ = [
    "LoggerFactory",
    "LoggerBuilder",
    "SessionLogger",
    "CaptureOutput",
    "SLSConfig",
    "SLSClient",
    "Logger",
]
