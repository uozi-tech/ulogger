"""
Tests for SLS (Simple Log Service) functionality
"""

import pytest
from unittest.mock import MagicMock, patch
import logging

from ulogger.sls import SLSConfig, SLSClient, SLSPropagateHandler


class TestSLSConfig:
    """Test SLSConfig class"""
    
    def test_default_config(self):
        """Test default SLS configuration"""
        config = SLSConfig()
        
        assert config.endpoint == ""
        assert config.access_key_id == ""
        assert config.access_key_secret == ""
        assert config.project == ""
        assert config.logstore == ""
        assert config.service_name == ""
    
    def test_config_with_values(self):
        """Test SLS configuration with values"""
        config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key_id",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore",
            service_name="test_service"
        )
        
        assert config.endpoint == "https://test.log.aliyuncs.com"
        assert config.access_key_id == "test_key_id"
        assert config.access_key_secret == "test_secret"
        assert config.project == "test_project"
        assert config.logstore == "test_logstore"
        assert config.service_name == "test_service"
    
    def test_is_valid_complete_config(self):
        """Test is_valid with complete configuration"""
        config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore"
        )
        
        assert config.is_valid() is True
    
    def test_is_valid_incomplete_config(self):
        """Test is_valid with incomplete configuration"""
        # Missing endpoint
        config = SLSConfig(
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore"
        )
        assert config.is_valid() is False
        
        # Missing project
        config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            logstore="test_logstore"
        )
        assert config.is_valid() is False
        
        # Missing logstore
        config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project"
        )
        assert config.is_valid() is False
    
    def test_is_valid_empty_config(self):
        """Test is_valid with empty configuration"""
        config = SLSConfig()
        assert config.is_valid() is False


class TestSLSClient:
    """Test SLSClient class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore"
        )
        self.client = SLSClient(self.config)
    
    def test_init(self):
        """Test SLSClient initialization"""
        assert self.client.config == self.config
        assert self.client._client is None
    
    @patch('aliyun.log.LogClient')
    def test_client_property_lazy_initialization(self, mock_log_client):
        """Test lazy initialization of SLS client"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        # First access should create the client
        client = self.client.client
        
        mock_log_client.assert_called_once_with(
            endpoint=self.config.endpoint,
            accessKeyId=self.config.access_key_id,
            accessKey=self.config.access_key_secret
        )
        assert client == mock_client_instance
        
        # Second access should return the same instance
        client2 = self.client.client
        assert client2 == mock_client_instance
        # LogClient should only be called once
        assert mock_log_client.call_count == 1
    
    def test_client_property_import_error(self):
        """Test client property when aliyun-log-python-sdk is not available"""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'aliyun.log'")):
            client = self.client.client
            assert client is None
    
    @patch('aliyun.log.LogClient')
    def test_check_project_exists_success(self, mock_log_client):
        """Test successful project existence check"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        result = self.client.check_project_exists()
        
        assert result is True
        mock_client_instance.get_project.assert_called_once_with(self.config.project)
    
    def test_check_project_exists_not_found(self):
        """Test project existence check when project doesn't exist"""
        # Create a mock client instance
        mock_client_instance = MagicMock()
        
        # Create a mock LogException that behaves like the real one
        class MockLogException(Exception):
            pass
        
        exception = MockLogException("ProjectNotExist: The specified project does not exist")
        mock_client_instance.get_project.side_effect = exception
        
        # Mock both the client property and the LogException import
        with patch.object(SLSClient, 'client', new_callable=lambda: property(lambda self: mock_client_instance)), \
             patch('builtins.__import__') as mock_import:
            
            def import_side_effect(name, *args, **kwargs):
                if name == 'aliyun.log.logexception':
                    mock_module = MagicMock()
                    mock_module.LogException = MockLogException
                    return mock_module
                else:
                    return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = import_side_effect
            
            result = self.client.check_project_exists()
        
        assert result is False
    
    def test_check_project_exists_no_client(self):
        """Test project existence check when client is None"""
        # Mock the client property to return None
        with patch.object(SLSClient, 'client', new_callable=lambda: property(lambda self: None)):
            result = self.client.check_project_exists()
            assert result is False
    
    @patch('aliyun.log.LogClient')
    def test_create_project_success(self, mock_log_client):
        """Test successful project creation"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        result = self.client.create_project("Test project")
        
        assert result is True
        mock_client_instance.create_project.assert_called_once_with(
            self.config.project, "Test project"
        )
    
    def test_create_project_already_exists(self):
        """Test project creation when project already exists"""
        # Create a mock client instance
        mock_client_instance = MagicMock()
        
        # Create a mock LogException that behaves like the real one
        class MockLogException(Exception):
            pass
        
        exception = MockLogException("ProjectAlreadyExist: The specified project already exists")
        mock_client_instance.create_project.side_effect = exception
        
        # Mock both the client property and the LogException import
        with patch.object(SLSClient, 'client', new_callable=lambda: property(lambda self: mock_client_instance)), \
             patch('builtins.__import__') as mock_import:
            
            def import_side_effect(name, *args, **kwargs):
                if name == 'aliyun.log.logexception':
                    mock_module = MagicMock()
                    mock_module.LogException = MockLogException
                    return mock_module
                else:
                    return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = import_side_effect
            
            result = self.client.create_project()
        
        assert result is True
    
    def test_create_project_no_client(self):
        """Test project creation when client is None"""
        # Mock the client property to return None
        with patch.object(SLSClient, 'client', new_callable=lambda: property(lambda self: None)):
            result = self.client.create_project()
            assert result is False
    
    @patch('aliyun.log.LogClient')
    def test_check_logstore_exists_success(self, mock_log_client):
        """Test successful logstore existence check"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        result = self.client.check_logstore_exists()
        
        assert result is True
        mock_client_instance.get_logstore.assert_called_once_with(
            self.config.project, self.config.logstore
        )
    
    @patch('aliyun.log.LogClient')
    def test_create_logstore_success(self, mock_log_client):
        """Test successful logstore creation"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        result = self.client.create_logstore(ttl=60, shard_count=4)
        
        assert result is True
        mock_client_instance.create_logstore.assert_called_once_with(
            project_name=self.config.project,
            logstore_name=self.config.logstore,
            ttl=60,
            shard_count=4
        )
    
    @patch('aliyun.log.LogClient')
    def test_ensure_logstore_exists_success(self, mock_log_client):
        """Test successful ensure logstore exists"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        # Mock both project and logstore exist
        self.client.check_project_exists = MagicMock(return_value=True)
        self.client.check_logstore_exists = MagicMock(return_value=True)
        
        result = self.client.ensure_logstore_exists()
        
        assert result is True
        self.client.check_project_exists.assert_called_once()
        self.client.check_logstore_exists.assert_called_once()
    
    @patch('aliyun.log.LogClient')
    def test_ensure_logstore_exists_create_project_and_logstore(self, mock_log_client):
        """Test ensure logstore exists when both need to be created"""
        mock_client_instance = MagicMock()
        mock_log_client.return_value = mock_client_instance
        
        # Mock neither exists, but creation succeeds
        self.client.check_project_exists = MagicMock(return_value=False)
        self.client.create_project = MagicMock(return_value=True)
        self.client.check_logstore_exists = MagicMock(return_value=False)
        self.client.create_logstore = MagicMock(return_value=True)
        
        result = self.client.ensure_logstore_exists()
        
        assert result is True
        self.client.check_project_exists.assert_called_once()
        self.client.create_project.assert_called_once()
        self.client.check_logstore_exists.assert_called_once()
        self.client.create_logstore.assert_called_once()
    
    def test_ensure_logstore_exists_invalid_config(self):
        """Test ensure logstore exists with invalid configuration"""
        invalid_config = SLSConfig()  # Empty config
        invalid_client = SLSClient(invalid_config)
        
        result = invalid_client.ensure_logstore_exists()
        
        assert result is False


class TestSLSPropagateHandler:
    """Test SLSPropagateHandler class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore",
            service_name="test_service"
        )
    
    def test_init(self):
        """Test SLSPropagateHandler initialization"""
        mock_sls_logger = MagicMock()
        handler = SLSPropagateHandler(mock_sls_logger)
        
        assert handler.sls_logger == mock_sls_logger
        assert isinstance(handler, logging.Handler)
    
    def test_emit(self):
        """Test emit method"""
        mock_sls_logger = MagicMock()
        mock_sls_logger.isEnabledFor.return_value = True
        
        handler = SLSPropagateHandler(mock_sls_logger)
        handler.service_name = "test_service"
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Verify the logger was called
        mock_sls_logger.handle.assert_called_once_with(record)
        
        # Verify extra service info was added
        assert hasattr(record, 'extra')
        assert record.extra["service"] == "test_service"
    
    def test_emit_logger_disabled(self):
        """Test emit method when logger is disabled for the level"""
        mock_sls_logger = MagicMock()
        mock_sls_logger.isEnabledFor.return_value = False
        
        handler = SLSPropagateHandler(mock_sls_logger)
        
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Logger should not be called
        mock_sls_logger.handle.assert_not_called()
    
    def test_emit_no_logger(self):
        """Test emit method when sls_logger is None"""
        handler = SLSPropagateHandler(None)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Should not raise an exception
        handler.emit(record)
    
    @patch('ulogger.sls.SLSPropagateHandler._setup_sls_logging')
    @patch('ulogger.sls.SLSClient')
    def test_create_success(self, mock_sls_client_class, mock_setup_sls):
        """Test successful handler creation"""
        mock_sls_logger = MagicMock()
        mock_setup_sls.return_value = mock_sls_logger
        
        mock_client_instance = MagicMock()
        mock_client_instance.ensure_logstore_exists.return_value = True
        mock_sls_client_class.return_value = mock_client_instance
        
        handler = SLSPropagateHandler.create(self.config)
        
        assert isinstance(handler, SLSPropagateHandler)
        assert handler.sls_logger == mock_sls_logger
        assert handler.service_name == self.config.service_name
        
        mock_setup_sls.assert_called_once_with(self.config)
        mock_client_instance.ensure_logstore_exists.assert_called_once()
    
    def test_create_invalid_config(self):
        """Test handler creation with invalid configuration"""
        invalid_config = SLSConfig()  # Empty config
        
        handler = SLSPropagateHandler.create(invalid_config)
        
        assert handler is None
    
    @patch('ulogger.sls.SLSPropagateHandler._setup_sls_logging')
    def test_create_setup_failure(self, mock_setup_sls):
        """Test handler creation when SLS setup fails"""
        mock_setup_sls.return_value = None
        
        handler = SLSPropagateHandler.create(self.config)
        
        assert handler is None
    
    @patch('logging.config.dictConfig')
    @patch('logging.getLogger')
    def test_setup_sls_logging_success(self, mock_get_logger, mock_dict_config):
        """Test successful SLS logging setup"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        result = SLSPropagateHandler._setup_sls_logging(self.config)
        
        assert result == mock_logger
        mock_dict_config.assert_called_once()
        mock_get_logger.assert_called_once_with("sls")
        
        # Verify the configuration structure
        call_args = mock_dict_config.call_args[0][0]
        assert call_args["version"] == 1
        assert "formatters" in call_args
        assert "handlers" in call_args
        assert "loggers" in call_args
        
        # Verify SLS handler configuration
        sls_handler = call_args["handlers"]["sls"]
        assert sls_handler["end_point"] == self.config.endpoint
        assert sls_handler["access_key_id"] == self.config.access_key_id
        assert sls_handler["access_key"] == self.config.access_key_secret
        assert sls_handler["project"] == self.config.project
        assert sls_handler["log_store"] == self.config.logstore
    
    def test_setup_sls_logging_import_error(self):
        """Test SLS logging setup when aliyun SDK is not available"""
        with patch('logging.config.dictConfig', side_effect=ImportError("No module")):
            result = SLSPropagateHandler._setup_sls_logging(self.config)
            assert result is None
    
    @patch('logging.config.dictConfig')
    def test_setup_sls_logging_config_error(self, mock_dict_config):
        """Test SLS logging setup when configuration fails"""
        mock_dict_config.side_effect = Exception("Configuration error")
        
        result = SLSPropagateHandler._setup_sls_logging(self.config)
        
        assert result is None


class TestSLSIntegration:
    """Integration tests for SLS functionality"""
    
    def test_end_to_end_handler_creation(self):
        """Test end-to-end handler creation workflow"""
        config = SLSConfig(
            endpoint="https://test.log.aliyuncs.com",
            access_key_id="test_key",
            access_key_secret="test_secret",
            project="test_project",
            logstore="test_logstore",
            service_name="integration_test"
        )
        
        # Mock all external dependencies
        with patch('ulogger.sls.SLSClient') as mock_client_class, \
             patch('ulogger.sls.SLSPropagateHandler._setup_sls_logging') as mock_setup:
            
            # Setup mocks
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger
            
            mock_client = MagicMock()
            mock_client.ensure_logstore_exists.return_value = True
            mock_client_class.return_value = mock_client
            
            # Create handler
            handler = SLSPropagateHandler.create(config)
            
            # Verify handler was created successfully
            assert handler is not None
            assert isinstance(handler, SLSPropagateHandler)
            assert handler.service_name == "integration_test"
            
            # Verify the workflow was executed
            mock_setup.assert_called_once_with(config)
            mock_client.ensure_logstore_exists.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 