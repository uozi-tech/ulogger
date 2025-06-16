"""
Core logging functionality using Factory and Builder patterns
"""

import sys
from typing import Optional, Dict, Any
from loguru import logger as _logger
from .sls import SLSConfig, SLSPropagateHandler


class LoggerConfig:
    """Logger configuration data class"""
    
    def __init__(self):
        self.tag: str = ""
        self.level: str = "INFO"
        self.format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <light-blue>{extra[tag]}:{line}</light-blue> | {message}"
        self.console_enabled: bool = True
        self.file_enabled: bool = False
        self.file_path: Optional[str] = None
        self.sls_enabled: bool = False
        self.sls_config: Optional[SLSConfig] = None
        self.extra: Dict[str, Any] = {}


class LoggerBuilder:
    """Builder pattern for creating configured loggers"""
    
    def __init__(self):
        self._config = LoggerConfig()
    
    def with_tag(self, tag: str) -> 'LoggerBuilder':
        """Set logger tag"""
        self._config.tag = tag
        return self
    
    def with_level(self, level: str) -> 'LoggerBuilder':
        """Set log level"""
        self._config.level = level
        return self
    
    def with_format(self, format_str: str) -> 'LoggerBuilder':
        """Set log format"""
        self._config.format = format_str
        return self
    
    def with_console(self, enabled: bool = True) -> 'LoggerBuilder':
        """Enable/disable console output"""
        self._config.console_enabled = enabled
        return self
    
    def with_file(self, file_path: str) -> 'LoggerBuilder':
        """Enable file output"""
        self._config.file_enabled = True
        self._config.file_path = file_path
        return self
    
    def with_sls(self, sls_config: SLSConfig) -> 'LoggerBuilder':
        """Enable SLS output"""
        self._config.sls_enabled = True
        self._config.sls_config = sls_config
        return self
    
    def with_extra(self, **kwargs) -> 'LoggerBuilder':
        """Add extra context data"""
        self._config.extra.update(kwargs)
        return self
    
    def build(self):
        """Build and return configured logger"""
        return LoggerFactory.create_logger(self._config)


class LoggerFactory:
    """Factory for creating different types of loggers"""
    
    @staticmethod
    def create_logger(config: LoggerConfig):
        """Create logger based on configuration"""
        # Remove existing handlers
        _logger.remove()
        
        # Bind tag and extra data to logger
        bound_logger = _logger.bind(tag=config.tag, **config.extra)
        
        # Add console handler if enabled
        if config.console_enabled:
            bound_logger.add(
                sys.stdout,
                format=config.format,
                level=config.level,
                enqueue=True
            )
        
        # Add file handler if enabled
        if config.file_enabled and config.file_path:
            bound_logger.add(
                config.file_path,
                format=config.format,
                level=config.level,
                enqueue=True
            )
        
        # Add SLS handler if enabled
        if config.sls_enabled and config.sls_config:
            sls_handler = SLSPropagateHandler.create(config.sls_config)
            if sls_handler:
                bound_logger.add(
                    sls_handler,
                    format="{message}",
                    level=config.level
                )
        
        return bound_logger
    
    @staticmethod
    def create_basic_logger(tag: str = "default", level: str = "INFO"):
        """Create a basic logger with minimal configuration"""
        return (LoggerBuilder()
                .with_tag(tag)
                .with_level(level)
                .with_console()
                .build())
