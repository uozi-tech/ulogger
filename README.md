# ULogger

Universal Python logging utilities with SLS and session support

一个基于 loguru 的通用日志包，支持阿里云 SLS 和会话日志。

## 特性

- 🏭 **工厂模式和建造者模式** - 灵活的日志配置
- 📊 **会话日志** - 结构化的事件日志记录
- ☁️ **SLS 集成** - 阿里云简单日志服务支持
- 🎯 **输出捕获** - 捕获和记录程序输出
- 🔧 **环境配置** - 支持环境变量配置
- 🧪 **完整测试** - 全面的测试覆盖

## 安装

```bash
# 使用 uv 从 Git 安装
uv add git+https://git.uozi.org/uozi/ulogger.git@v0.1.1

# 或者本地开发安装
cd ulogger
uv pip install -e .
```

## 快速开始

### 基础用法

```python
from ulogger import LoggerFactory

# 创建基本日志器
logger = LoggerFactory.create_basic_logger("my_app", "INFO")
logger.info("Hello, World!")
logger.warning("This is a warning")
logger.error("This is an error")
```

## 核心模块 (Core)

### LoggerFactory - 工厂模式创建日志器

```python
from ulogger import LoggerFactory

# 1. 创建基本日志器
logger = LoggerFactory.create_basic_logger(tag="basic", level="INFO")

# 2. 创建文件日志器（同时输出到控制台和文件）
logger = LoggerFactory.create_file_logger(
    tag="file_logger", 
    file_path="app.log", 
    level="DEBUG"
)

# 3. 创建 SLS 日志器
from ulogger import SLSConfig
sls_config = SLSConfig(
    endpoint="https://your-region.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="your_project",
    logstore="your_logstore",
    service_name="your_service"
)
logger = LoggerFactory.create_sls_logger("sls_app", sls_config, "INFO")
```

### LoggerBuilder - 建造者模式

```python
from ulogger import LoggerBuilder

# 使用建造者模式创建复杂配置
logger = (LoggerBuilder()
          .with_tag("web_api")
          .with_level("DEBUG")
          .with_console()
          .with_file("app.log")
          .with_extra(version="1.0.0", environment="production")
          .build())

logger.debug("Debug message with context")
logger.info("Service started")
```

### LoggerBuilder 完整方法列表

```python
from ulogger import LoggerBuilder, SLSConfig

builder = LoggerBuilder()

# 设置标签
builder.with_tag("my_service")

# 设置日志级别
builder.with_level("DEBUG")  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 设置日志格式
custom_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[tag]}:{line}</cyan> | {message}"
builder.with_format(custom_format)

# 控制台输出控制
builder.with_console()  # 启用控制台输出
builder.with_console(False)  # 禁用控制台输出

# 文件输出
builder.with_file("application.log")

# SLS 输出
sls_config = SLSConfig(
    endpoint="https://your-region.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="your_project",
    logstore="your_logstore",
    service_name="your_service"
)
builder.with_sls(sls_config)

# 添加额外上下文数据
builder.with_extra(
    service="user-api",
    version="2.1.0",
    environment="production",
    region="us-west-2"
)

# 构建日志器
logger = builder.build()
```

## 会话日志 (Session)

### SessionLogger 基础用法

```python
from ulogger import SessionLogger

# 1. 创建基本会话日志器
session_logger = SessionLogger.create("api_service", "session_12345")

# 2. 使用结构化日志记录
session_logger.info("request_start", "/api/users", method="GET", user_id=123)
session_logger.success("request_complete", "Data retrieved successfully", status_code=200, rows=50)
session_logger.error("validation_error", "Invalid email format", field="email", value="invalid-email")
session_logger.warning("rate_limit", "Approaching rate limit", current=95, limit=100)
```

### SessionLogger 工厂方法

```python
from ulogger import SessionLogger, SLSConfig

# 1. 基本会话日志器
session_logger = SessionLogger.create("service", "session_id")

# 2. 带文件输出的会话日志器
session_logger = SessionLogger.create_with_file("service", "session_id", "session.log")

# 3. 带 SLS 支持的会话日志器
sls_config = SLSConfig(
    endpoint="https://your-region.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="your_project",
    logstore="your_logstore",
    service_name="your_service"
)
session_logger = SessionLogger.create_with_sls("service", "session_id", sls_config)

# 4. 自定义配置的会话日志器
from ulogger import LoggerBuilder
builder = (LoggerBuilder()
           .with_tag("custom_session")
           .with_level("INFO")
           .with_file("session.log")
           .with_extra(module="auth", version="2.0.0"))

session_logger = SessionLogger.create_custom("auth", "sess_789", builder)
```

### SessionLogger 完整方法列表

```python
session_logger = SessionLogger.create("api", "session_123")

# 各种日志级别
session_logger.debug("debug_event", "Debug information", step=1)
session_logger.info("info_event", "Process started", pid=1234)
session_logger.warning("warning_event", "Memory usage high", usage="85%")
session_logger.error("error_event", "Database connection failed", retry_count=3)
session_logger.success("success_event", "Operation completed", duration=1.23)
session_logger.critical("critical_event", "System failure", error_code=500)
session_logger.exception("exception_event", "Unhandled exception")  # 自动包含异常信息

# 绑定额外上下文
contextual_logger = session_logger.bind(request_id="req_456")

# 创建带上下文的新会话日志器
new_session = session_logger.with_context(
    request_id="req_456",
    trace_id="trace_123",
    user_id=789
)
new_session.info("user_action", "User logged in", ip="192.168.1.1")
```

## SLS 集成 (Alibaba Cloud Simple Log Service)

### SLSConfig 配置

```python
from ulogger import SLSConfig

# 1. 直接创建配置
sls_config = SLSConfig(
    endpoint="https://cn-hangzhou.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="my_project",
    logstore="my_logstore",
    service_name="my_service"
)

# 2. 检查配置有效性
if sls_config.is_valid():
    print("SLS configuration is valid")
else:
    print("SLS configuration is incomplete")
```

### SLSClient 管理工具

```python
from ulogger import SLSConfig, SLSClient

sls_config = SLSConfig(
    endpoint="https://your-region.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="your_project",
    logstore="your_logstore",
    service_name="your_service"
)
client = SLSClient(sls_config)

# 检查项目是否存在
if client.check_project_exists():
    print("Project exists")

# 创建项目
client.create_project("My auto-created project")

# 检查 logstore 是否存在
if client.check_logstore_exists():
    print("Logstore exists")

# 创建 logstore
client.create_logstore(ttl=30, shard_count=2)  # 保存30天，2个分片

# 确保 logstore 存在（推荐方法）
success = client.ensure_logstore_exists(
    ttl=30,
    shard_count=2,
    project_description="Auto created project for logging"
)
```

## 输出捕获 (Capture)

```python
from ulogger import capture_output

with capture_output("capture") as capture:
    print("Normal output")
```

## 高级用法

### 1. 组合使用多种功能

```python
from ulogger import LoggerBuilder, SessionLogger, SLSConfig, CaptureOutput

# 创建复杂配置的日志器
sls_config = SLSConfig(
    endpoint="https://your-region.log.aliyuncs.com",
    access_key_id="your_access_key_id",
    access_key_secret="your_access_key_secret",
    project="your_project",
    logstore="your_logstore",
    service_name="your_service"
)

builder = (LoggerBuilder()
           .with_tag("complex_app")
           .with_level("DEBUG")
           .with_console()
           .with_file("app.log")
           .with_sls(sls_config)
           .with_extra(
               service="user-management",
               version="3.1.0",
               environment="production"
           ))

# 使用自定义日志器创建会话日志器
session_logger = SessionLogger.create_custom("user_service", "session_456", builder)

# 结合输出捕获
with CaptureOutput("operation_capture", session_logger.logger) as capture:
    session_logger.info("operation_start", "Starting user registration")
    print("Processing user data...")
    session_logger.success("operation_complete", "User registered successfully")
```

### 2. 日志上下文管理

```python
from ulogger import SessionLogger

# 创建基础会话日志器
base_session = SessionLogger.create("api_gateway", "0E3EC17C-1B16-4181-BB27-5D0D5FC1561")

# 为不同请求创建独立上下文
request_logger = base_session.with_context(
    request_id="req_789",
    trace_id="trace_456",
    user_id=123,
    endpoint="/api/v1/users"
)

# 记录请求处理过程
request_logger.info("request_received", "GET /api/v1/users", 
                   method="GET", ip="192.168.1.100")
request_logger.info("auth_check", "Validating user token")
request_logger.info("db_query", "Fetching user data", query_time=0.045)
request_logger.success("response_sent", "Request completed", 
                      status=200, response_time=0.123)
```

### 3. 错误处理和异常记录

```python
from ulogger import SessionLogger

session_logger = SessionLogger.create("error_handling", "0E3EC17C-1B16-4181-BB27-5D0D5FC1561")

try:
    # 模拟一些操作
    result = 10 / 0
except Exception as e:
    # 记录异常信息
    session_logger.exception("division_error", "Division by zero occurred",
                           operation="10/0", error_type=type(e).__name__)
    
    # 或者记录错误详情
    session_logger.error("calculation_failed", "Mathematical operation failed",
                        operation="division", dividend=10, divisor=0,
                        error_message=str(e))
```

## 测试

```bash
# 运行测试
uv run pytest
```

## 代码检查

```bash
uv run ruff check
```

## 项目结构

```
ulogger/
├── src/
│   └── ulogger/
│       ├── __init__.py       # 包初始化和导出
│       ├── core.py           # 核心日志功能 (LoggerFactory, LoggerBuilder)
│       ├── sls.py            # SLS 集成 (SLSConfig, SLSClient, SLSPropagateHandler)
│       ├── session.py        # 会话日志 (SessionLogger)
│       └── capture.py        # 输出捕获 (CaptureOutput)
├── tests/
│   └── test_core.py         # 核心功能测试
├── examples/
│   └── basic_usage.py       # 使用示例
├── pyproject.toml           # 项目配置
├── README.md               # 说明文档
└── main.py                 # 演示脚本
```

## API 参考

### 导出的类和函数

```python
from ulogger import (
    # 核心日志功能
    LoggerFactory,    # 日志器工厂
    LoggerBuilder,    # 日志器构建器
    
    # 会话日志
    SessionLogger,    # 会话日志器
    
    # SLS 集成
    SLSConfig,        # SLS 配置
    SLSClient,        # SLS 客户端
    
    # 全部输出捕获
    capture_output,
)
```

## 原理和设计

### 设计模式

- **工厂模式** - `LoggerFactory` 提供简单的创建接口
- **建造者模式** - `LoggerBuilder` 支持复杂配置
- **策略模式** - 不同的日志输出策略（控制台、文件、SLS）

### 架构优势

1. **解耦合** - 不直接依赖原始配置，使用独立的配置类
2. **可扩展** - 易于添加新的日志输出方式
3. **类型安全** - 使用类型提示确保参数正确
4. **测试友好** - 模块化设计便于单元测试
