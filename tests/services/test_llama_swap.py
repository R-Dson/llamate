"""Tests for llama swap integration functionality."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import json
import yaml
import urllib.request
import shutil

from llamate.services import llama_swap
from llamate.core import config

@pytest.fixture
def mock_platform_info():
    with patch('llamate.core.platform.get_platform_info') as mock_get_platform:
        mock_get_platform.return_value = ("linux", "amd64")
        yield mock_get_platform

@pytest.fixture
def mock_download():
    with patch('llamate.core.download.download_file') as mock_download_file:
        yield mock_download_file

@pytest.fixture
def mock_github_response():
    mock_response = {
        "assets": [
            {
                "name": "llama-swap_linux_amd64.tar.gz",
                "browser_download_url": "https://example.com/download/llama-swap_linux_amd64.tar.gz"
            },
            {
                "name": "llama-swap_windows_amd64.zip",
                "browser_download_url": "https://example.com/download/llama-swap_windows_amd64.zip"
            }
        ]
    }
    return mock_response

# Custom mock class to simulate requests.Response
class MockResponse:
    def __init__(self, json_data, status_code):
        self._json_data = json_data
        self.status_code = status_code
        self.status = status_code  # Needed for urllib compatibility
        self.text = json.dumps(json_data) # Provide text attribute

    def json(self):
        return self._json_data

    def read(self):
        # Simulate reading the response body
        return json.dumps(self._json_data).encode('utf-8')

    # Add context manager methods
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass # Nothing to clean up for this mock

@patch('requests.get')
def test_download_binary_success(mock_get, tmp_path, mock_platform_info, mock_download, mock_github_response):
    """Test successful binary download."""
    # Use custom MockResponse
    mock_response = MockResponse({
        'assets': [
            # Updated asset name and download URL to match expected format
            {'name': 'llama-swap_linux_amd64.tar.gz', 'browser_download_url': 'https://example.com/download/llama-swap_linux_amd64.tar.gz'},
            {'name': 'other-asset', 'browser_download_url': 'http://example.com/other-asset'},
        ]
    }, 200)
    print(f"Mock response for success test: {mock_response.__dict__}") # Debug print
    mock_get.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_get.return_value):
        dest_file = llama_swap.download_binary(tmp_path)

    assert dest_file == tmp_path / "llama-swap_linux_amd64.tar.gz"
    mock_download.assert_called_once_with(
        "https://example.com/download/llama-swap_linux_amd64.tar.gz",
        dest_file
    )

@patch('requests.get')
def test_download_binary_arch_override(mock_get, tmp_path, mock_platform_info, mock_download, mock_github_response):
    """Test binary download with architecture override."""
    # Use custom MockResponse
    mock_response = MockResponse({
        'assets': [
            # Updated asset name and download URL to match expected format for arm64 override
            {'name': 'llama-swap_linux_arm64.tar.gz', 'browser_download_url': 'https://example.com/download/llama-swap_linux_arm64.tar.gz'},
            {'name': 'other-asset', 'browser_download_url': 'http://example.com/other-asset'},
        ]
    }, 200)
    print(f"Mock response for arch override test: {mock_response.__dict__}") # Debug print
    mock_get.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_get.return_value):
        dest_file = llama_swap.download_binary(tmp_path, arch_override="arm64")

    # Updated assertion to check for the arm64 filename
    assert dest_file == tmp_path / "llama-swap_linux_arm64.tar.gz"

@patch('requests.get')
def test_download_binary_no_matching_asset(mock_get, tmp_path, mock_platform_info, mock_download):
    """Test binary download when no matching asset is found."""
    # Use custom MockResponse
    mock_response = MockResponse({
        'assets': [
            {'name': 'other-asset', 'browser_download_url': 'http://example.com/other-asset'},
        ]
    }, 200)
    print(f"Mock response for no matching asset test: {mock_response.__dict__}") # Debug print
    mock_get.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_get.return_value):
        with pytest.raises(RuntimeError, match=r"No asset found for linux/amd64"):
            llama_swap.download_binary(tmp_path)

def test_download_binary_github_api_error(tmp_path, mock_platform_info, mock_download):
    """Test binary download when GitHub API request fails."""
    with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("API error")):
        with pytest.raises(RuntimeError, match=r"Failed to get release info \(Network error\): .*API error"):
            llama_swap.download_binary(tmp_path)

def test_extract_binary_zip(tmp_path):
    """Test extracting binary from zip archive."""
    archive = tmp_path / "test.zip"
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    bin_dir = dest_dir / "bin"
    bin_dir.mkdir()

    # Create test zip file
    with patch('zipfile.ZipFile') as mock_zip:
        llama_swap.extract_binary(archive, dest_dir)
        mock_zip.assert_called_once_with(archive, 'r')
        mock_zip.return_value.__enter__.return_value.extractall.assert_called_once_with(dest_dir)

def test_extract_binary_targz(tmp_path):
    """Test extracting binary from tar.gz archive."""
    archive = tmp_path / "test.tar.gz"
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    bin_dir = dest_dir / "bin"
    bin_dir.mkdir()

    # Create test tar.gz file
    with patch('tarfile.open') as mock_tar:
        llama_swap.extract_binary(archive, dest_dir)
        mock_tar.assert_called_once_with(archive, 'r:gz')
        mock_tar.return_value.__enter__.return_value.extractall.assert_called_once_with(dest_dir)

@patch('llamate.services.llama_swap.load_config')
def test_save_llama_swap_config(mock_load_config, tmp_path):
    """Test saving llama-swap configuration file."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    config_file = tmp_path / "llamate.yaml"

    # Create a mock model config file for the test to find
    (models_dir / "test_model.yaml").touch()

    mock_model_config = {
        "test_model": {
            "hf_repo": "test/repo",
            "hf_file": "model.gguf",
            "args": {
                "n-gpu-layers": "30",
                "proxy": "http://localhost:8000"
            }
        }
    }

    mock_global_config = {
        "llama_server_path": "/path/to/llama-server",
        "ggufs_storage_path": str(tmp_path / "ggufs"),
        "healthCheckTimeout": 30
    }

    # Explicitly set the return value of the mocked load_llama_swap_config
    mock_load_config.return_value = {
        'healthCheckTimeout': 30,
        'models': {}
    }

    with patch('llamate.core.config.constants.MODELS_DIR', models_dir), \
         patch('llamate.core.config.constants.LLAMATE_CONFIG_FILE', config_file), \
         patch('llamate.core.config.load_model_config', side_effect=lambda name: mock_model_config[name]), \
         patch('llamate.core.config.load_global_config', return_value=mock_global_config):

        # Call the actual save_llama_swap_config function
        llama_swap.save_llama_swap_config()

        # Assert that the config file exists
        assert config_file.exists()
        with open(config_file) as f:
            saved_config = yaml.safe_load(f)

        # Assert the content of the saved config
        assert "models" in saved_config
        assert "test_model" in saved_config["models"]
        assert "healthCheckTimeout" in saved_config
        assert saved_config["healthCheckTimeout"] == 30

    # Removed assertions related to the mocked save_config call

def test_generate_config():
    """Test generating llama-swap configuration."""
    mock_global_config = {
        "llama_server_path": "/path/to/llama-server",
        "ggufs_storage_path": "/path/to/ggufs",
        "healthCheckTimeout": 30,
        "logLevel": "debug",
        "groups": {"group1": ["model1"]}
    }

    model_configs = {
        "model1": {
            "hf_repo": "repo1",
            "hf_file": "model1.gguf",
            "args": {
                "n-gpu-layers": "30",
                "threads": "4",
                "proxy": "http://localhost:8000"
            }
        }
    }

    with patch('llamate.core.config.load_global_config', return_value=mock_global_config):
        config = llama_swap.generate_config(model_configs)

        assert "models" in config
        assert "model1" in config["models"]
        assert "healthCheckTimeout" in config
        assert "logLevel" in config
        assert "groups" in config
        
        # Check model command generation
        model1_cmd = config["models"]["model1"]["cmd"]
        assert "/path/to/llama-server" in model1_cmd
        assert "--n-gpu-layers 30" in model1_cmd
        assert "--threads 4" in model1_cmd
        assert "proxy" not in model1_cmd  # Should be in model config, not command
        assert config["models"]["model1"]["proxy"] == "http://localhost:8000"

def test_generate_config_no_models():
    """Test generating config with no models."""
    mock_global_config = {
        "llama_server_path": "/path/to/llama-server",
        "ggufs_storage_path": "/path/to/ggufs"
    }

    with patch('llamate.core.config.load_global_config', return_value=mock_global_config):
        config = llama_swap.generate_config({})
        
        assert "models" not in config  # No models section when no models configured
