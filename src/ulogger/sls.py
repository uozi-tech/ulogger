"""
SLS (Simple Log Service) integration for Alibaba Cloud
"""

import logging
import logging.config
from typing import Optional
from dataclasses import dataclass


@dataclass
class SLSConfig:
    """SLS configuration data class"""
    endpoint: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    project: str = ""
    logstore: str = ""
    service_name: str = ""
    
    def is_valid(self) -> bool:
        """Check if all required fields are present"""
        return all([
            self.endpoint,
            self.access_key_id,
            self.access_key_secret,
            self.project,
            self.logstore
        ])


class SLSClient:
    """阿里云 SLS 客户端工具类"""

    def __init__(self, config: SLSConfig):
        self.config = config
        self._client = None
        
    @property
    def client(self):
        """Lazy initialization of SLS client"""
        if self._client is None:
            try:
                from aliyun.log import LogClient
                self._client = LogClient(
                    endpoint=self.config.endpoint,
                    accessKeyId=self.config.access_key_id,
                    accessKey=self.config.access_key_secret,
                )
            except ImportError:
                print("aliyun-log-python-sdk not installed, SLS client unavailable")
                return None
        return self._client

    def check_project_exists(self) -> bool:
        """检查项目是否存在"""
        if not self.client:
            return False
            
        try:
            from aliyun.log.logexception import LogException
            self.client.get_project(self.config.project)
            return True
        except LogException as e:
            if "ProjectNotExist" in str(e):
                print(f"Project {self.config.project} does not exist")
                return False
            else:
                print(f"Error checking project: {e}")
                raise e
        except Exception as e:
            print(f"Unexpected error checking project: {e}")
            return False

    def create_project(self, description: str = "Auto created project") -> bool:
        """创建项目"""
        if not self.client:
            return False
            
        try:
            from aliyun.log.logexception import LogException
            self.client.create_project(self.config.project, description)
            print(f"Project {self.config.project} created successfully")
            return True
        except LogException as e:
            if "ProjectAlreadyExist" in str(e):
                print(f"Project {self.config.project} already exists")
                return True
            else:
                print(f"Error creating project: {e}")
                return False
        except Exception as e:
            print(f"Unexpected error creating project: {e}")
            return False

    def check_logstore_exists(self) -> bool:
        """检查 logstore 是否存在"""
        if not self.client:
            return False
            
        try:
            from aliyun.log.logexception import LogException
            self.client.get_logstore(self.config.project, self.config.logstore)
            return True
        except LogException as e:
            if "LogStoreNotExist" in str(e):
                print(
                    f"Logstore {self.config.logstore} does not exist in project {self.config.project}"
                )
                return False
            else:
                print(f"Error checking logstore: {e}")
                raise e
        except Exception as e:
            print(f"Unexpected error checking logstore: {e}")
            return False

    def create_logstore(self, ttl: int = 30, shard_count: int = 2) -> bool:
        """
        创建 logstore

        Args:
            ttl: 数据保存时间(天)，默认30天
            shard_count: shard 数量，默认2个
        """
        if not self.client:
            return False
            
        try:
            from aliyun.log.logexception import LogException
            self.client.create_logstore(
                project_name=self.config.project,
                logstore_name=self.config.logstore,
                ttl=ttl,
                shard_count=shard_count,
            )
            print(
                f"Logstore {self.config.logstore} created successfully in project {self.config.project}"
            )
            return True
        except LogException as e:
            if "LogStoreAlreadyExist" in str(e):
                print(f"Logstore {self.config.logstore} already exists")
                return True
            else:
                print(f"Error creating logstore: {e}")
                return False
        except Exception as e:
            print(f"Unexpected error creating logstore: {e}")
            return False

    def ensure_logstore_exists(
        self,
        ttl: int = 30,
        shard_count: int = 2,
        project_description: str = "Auto created project",
    ) -> bool:
        """
        确保 logstore 存在，如果不存在则创建

        Args:
            ttl: 数据保存时间(天)，默认30天  
            shard_count: shard 数量，默认2个
            project_description: 项目描述

        Returns:
            bool: 是否成功确保 logstore 存在
        """
        try:
            # 检查配置是否完整
            if not self.config.is_valid():
                print("SLS configuration is incomplete")
                return False

            # 确保项目存在
            if not self.check_project_exists():
                if not self.create_project(project_description):
                    print("Failed to create project")
                    return False

            # 确保 logstore 存在
            if not self.check_logstore_exists():
                if not self.create_logstore(ttl, shard_count):
                    print("Failed to create logstore")
                    return False

            return True

        except Exception as e:
            print(f"Error ensuring logstore exists: {e}")
            return False


class SLSPropagateHandler(logging.Handler):
    """将 loguru 日志优雅地转发到 SLS Logger"""

    def __init__(self, sls_logger):
        super().__init__()
        self.sls_logger = sls_logger

    def emit(self, record: logging.LogRecord) -> None:
        if self.sls_logger and self.sls_logger.isEnabledFor(record.levelno):
            # Add service name to record
            if hasattr(self, 'service_name'):
                record.extra = getattr(record, 'extra', {})
                record.extra["service"] = self.service_name
            self.sls_logger.handle(record)

    @classmethod
    def create(cls, config: SLSConfig) -> Optional['SLSPropagateHandler']:
        """Create SLS handler if configuration is valid"""
        if not config.is_valid():
            return None
            
        try:
            # Setup SLS logger
            sls_logger = cls._setup_sls_logging(config)
            if sls_logger:
                # Ensure logstore exists
                client = SLSClient(config)
                client.ensure_logstore_exists()
                
                handler = cls(sls_logger)
                handler.service_name = config.service_name
                return handler
            return None
        except Exception as e:
            print(f"Failed to create SLS handler: {e}")
            return None

    @staticmethod
    def _setup_sls_logging(config: SLSConfig):
        """设置阿里云 SLS 日志记录器"""
        try:
            # Configure SLS handler  
            sls_conf = {
                "version": 1,
                "formatters": {
                    "raw": {"class": "logging.Formatter", "format": "%(message)s"}
                },
                "handlers": {
                    "sls": {
                        "()": "aliyun.log.QueuedLogHandler",
                        "level": "INFO",
                        "formatter": "raw",
                        # SLS connection
                        "end_point": config.endpoint,
                        "access_key_id": config.access_key_id,
                        "access_key": config.access_key_secret,
                        "project": config.project,
                        "log_store": config.logstore,
                        # KV auto-extraction
                        "extract_kv": True,
                    }
                },
                "loggers": {
                    "sls": {
                        "handlers": ["sls"],
                        "level": "INFO",
                        "propagate": False,
                    }
                },
            }

            logging.config.dictConfig(sls_conf)
            sls_logger = logging.getLogger("sls")
            return sls_logger

        except ImportError:
            print("aliyun-log-python-sdk not installed, skipping SLS setup")
            return None
        except Exception as e:
            print(f"Failed to setup SLS logging: {e}")
            return None
