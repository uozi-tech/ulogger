"""SLS (Simple Log Service) integration for Alibaba Cloud."""

import hashlib
import json
import logging
import os
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class PackIdGenerator:
    """生成符合阿里云 PackId 规范的标识符，线程安全"""

    _PREFIX_LENGTH = 16

    def __init__(self, prefix: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._counter = 0
        self._prefix = (prefix or self._build_prefix()).upper()

    def generate(self) -> str:
        """生成新的 PackId，格式为 <前缀>-<递增十六进制序号>"""
        with self._lock:
            self._counter += 1
            sequence = self._counter
        return f"{self._prefix}-{sequence:X}"

    def _build_prefix(self) -> str:
        hostname = socket.gethostname()
        pid = os.getpid()
        now_ns = time.time_ns()
        entropy = secrets.token_hex(8)
        payload = f"{hostname}|{pid}|{now_ns}|{entropy}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest().upper()
        return digest[: self._PREFIX_LENGTH]


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
        return all(
            [
                self.endpoint,
                self.access_key_id,
                self.access_key_secret,
                self.project,
                self.logstore,
            ]
        )


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
    """自定义日志 Handler，使用阿里云 SDK 直接写入 SLS，支持纳秒级时间戳"""

    def __init__(
        self,
        client,
        config: SLSConfig,
        log_item_cls,
        put_logs_request_cls,
        log_exception_cls,
    ) -> None:
        super().__init__()
        self._client = client
        self._config = config
        self._LogItem = log_item_cls
        self._PutLogsRequest = put_logs_request_cls
        self._LogException = log_exception_cls
        self._lock = threading.Lock()
        self._pack_id_generator = PackIdGenerator()

    def emit(self, record: logging.LogRecord) -> None:
        if not self._client:
            return

        try:
            contents = self._build_contents(record)

            log_item = self._LogItem()
            seconds, nano_part = self._resolve_timestamp(record)
            log_item.set_time(seconds)
            if hasattr(log_item, "set_time_nano_part"):
                log_item.set_time_nano_part(nano_part)

            log_item.set_contents(self._to_content_pairs(contents))

            request = self._PutLogsRequest(
                self._config.project,
                self._config.logstore,
                logitems=[log_item],
            )

            pack_id = self._pack_id_generator.generate()
            self._attach_pack_id(request, pack_id)

            with self._lock:
                self._client.put_logs(request)

        except self._LogException as exc:  # type: ignore[misc]
            logging.getLogger(__name__).warning(
                "Failed to put logs to SLS project=%s logstore=%s: %s",
                self._config.project,
                self._config.logstore,
                exc,
            )
        except Exception as exc:  # noqa: BLE001 - logging handlers must swallow errors
            logging.getLogger(__name__).warning(
                "Unexpected error while sending log to SLS: %s", exc
            )

    def _build_contents(self, record: logging.LogRecord) -> Dict[str, str]:
        contents: Dict[str, str] = {
            "message": record.getMessage(),
            "levelname": record.levelname,
            "name": record.name,
        }

        if record.module:
            contents["module"] = record.module
        if record.funcName:
            contents["funcName"] = record.funcName
        if record.pathname:
            contents["pathname"] = record.pathname
        if record.process:
            contents["process"] = str(record.process)
        if getattr(record, "processName", None):
            contents["processName"] = record.processName
        if record.thread:
            contents["thread"] = str(record.thread)
        if getattr(record, "threadName", None):
            contents["threadName"] = record.threadName
        if record.lineno:
            contents["lineno"] = str(record.lineno)

        if self._config.service_name:
            contents["service"] = self._config.service_name

        extras = getattr(record, "extra", None)
        extra_payload: Dict[str, str] = {}
        if isinstance(extras, dict):
            for key, value in extras.items():
                serialized = self._serialize_value(value)
                extra_payload[key] = serialized
                if key not in contents:
                    contents[key] = serialized

        if "tag" not in contents:
            tag = getattr(record, "tag", None)
            if tag is not None:
                serialized_tag = self._serialize_value(tag)
                contents["tag"] = serialized_tag
                extra_payload.setdefault("tag", serialized_tag)

        if record.exc_info:
            contents.setdefault("exc", self.formatException(record.exc_info))

        if self._config.service_name:
            extra_payload.setdefault("service", self._config.service_name)

        if extra_payload:
            contents["extra"] = json.dumps(extra_payload, ensure_ascii=False)

        contents.setdefault("path", record.pathname or "")

        return contents

    @staticmethod
    def _serialize_value(value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return repr(value)

    @staticmethod
    def _to_content_pairs(contents: Dict[str, str]) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []
        for key, value in contents.items():
            if value is not None:
                pairs.append((key, str(value)))
        return pairs

    @staticmethod
    def _resolve_timestamp(record: logging.LogRecord) -> Tuple[int, int]:
        created = getattr(record, "created", 0.0)
        if created:
            seconds = int(created)
            nano_part = int((created - seconds) * 1_000_000_000)
            if 0 <= nano_part < 1_000_000_000:
                return seconds, nano_part

        now_ns = time.time_ns()
        return now_ns // 1_000_000_000, now_ns % 1_000_000_000

    def _attach_pack_id(self, request, pack_id: str) -> None:
        tag_payload = [("__pack_id__", pack_id)]

        set_logtags = getattr(request, "set_logtags", None)
        if callable(set_logtags):
            set_logtags(tag_payload)
            return

        set_log_tags = getattr(request, "set_log_tags", None)
        if callable(set_log_tags):
            set_log_tags(tag_payload)
            return

        if hasattr(request, "logtags"):
            request.logtags = tag_payload
            return

        request.log_tags = tag_payload

    @classmethod
    def create(cls, config: SLSConfig) -> Optional["SLSPropagateHandler"]:
        """Create SLS handler if configuration is valid"""
        if not config.is_valid():
            return None

        try:
            from aliyun.log import LogItem, PutLogsRequest
            from aliyun.log.logexception import LogException
        except ImportError:
            print(
                "aliyun-log-python-sdk>=0.8.11 is required for SLS integration with nanosecond precision"
            )
            return None

        try:
            client_wrapper = SLSClient(config)
            if not client_wrapper.ensure_logstore_exists():
                return None

            client = client_wrapper.client
            if not client:
                return None

            handler = cls(client, config, LogItem, PutLogsRequest, LogException)
            return handler
        except Exception as exc:
            print(f"Failed to create SLS handler: {exc}")
            return None
