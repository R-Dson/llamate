"""Tests for llama server management functionality."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from llamate.services import llama_server
from llamate.core import config

@pytest.fixture
def mock_server_path(tmp_path):
    server_path = tmp_path / "llama-server"
    server_path.touch()
    server_path.chmod(0o755)  # Make executable
    return server_path

@pytest.fixture
def mock_config():
    with patch('llamate.core.config.load_global_config') as mock_load_global:
        mock_load_global.return_value = {"llama_server_path": "/fake/llama-server"}
        yield mock_load_global

def test_validate_server_path_exists(mock_server_path):
    """Test server path validation when path exists and is executable."""
    assert llama_server.validate_server_path(str(mock_server_path)) is True

def test_validate_server_path_not_exists():
    """Test server path validation when path does not exist."""
    assert llama_server.validate_server_path("/nonexistent/path") is False

def test_validate_server_path_is_directory(tmp_path):
    """Test server path validation when path is a directory."""
    assert llama_server.validate_server_path(str(tmp_path)) is False

def test_build_command_basic(mock_config):
    """Test building basic command with minimal configuration."""
    gguf_path = Path("/path/to/model.gguf")
    model_config = {
        "hf_repo": "test/repo",
        "hf_file": "model.gguf",
        "args": {}
    }
    
    cmd = llama_server.build_command(gguf_path, model_config)
    
    assert cmd == ["/fake/llama-server", "-m", str(gguf_path)]

def test_build_command_with_args(mock_config):
    """Test building command with model arguments."""
    gguf_path = Path("/path/to/model.gguf")
    model_config = {
        "hf_repo": "test/repo",
        "hf_file": "model.gguf",
        "args": {
            "n-gpu-layers": "30",
            "threads": "4",
            "verbose": "true"
        }
    }
    
    cmd = llama_server.build_command(gguf_path, model_config)
    
    assert cmd == [
        "/fake/llama-server",
        "-m", str(gguf_path),
        "--n-gpu-layers", "30",
        "--threads", "4",
        "--verbose"
    ]

def test_build_command_with_proxy_arg(mock_config):
    """Test building command with proxy argument (should be ignored)."""
    gguf_path = Path("/path/to/model.gguf")
    model_config = {
        "hf_repo": "test/repo",
        "hf_file": "model.gguf",
        "args": {
            "proxy": "http://localhost:8000",
            "threads": "4"
        }
    }
    
    cmd = llama_server.build_command(gguf_path, model_config)
    
    assert cmd == [
        "/fake/llama-server",
        "-m", str(gguf_path),
        "--threads", "4"
    ]
    assert "--proxy" not in cmd

def test_build_command_with_passthrough_args(mock_config):
    """Test building command with passthrough arguments."""
    gguf_path = Path("/path/to/model.gguf")
    model_config = {
        "hf_repo": "test/repo",
        "hf_file": "model.gguf",
        "args": {"threads": "4"}
    }
    passthrough_args = ["--n-ctx=2048", "--verbose"]
    
    cmd = llama_server.build_command(gguf_path, model_config, passthrough_args)
    
    assert cmd == [
        "/fake/llama-server",
        "-m", str(gguf_path),
        "--threads", "4",
        "--n-ctx", "2048",
        "--verbose"
    ]

def test_build_command_no_server_path():
    """Test building command when server path is not set."""
    with patch('llamate.core.config.load_global_config', return_value={}):
        with pytest.raises(ValueError, match="llama_server_path is not set"):
            llama_server.build_command(
                Path("/path/to/model.gguf"),
                {"hf_repo": "test/repo", "hf_file": "model.gguf", "args": {}}
            )

def test_run_server_success():
    """Test running server process successfully."""
    cmd = ["/fake/llama-server", "-m", "/path/to/model.gguf"]
    mock_process = MagicMock()
    
    with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
        process = llama_server.run_server(cmd)
        
        mock_popen.assert_called_once_with(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert process == mock_process

def test_run_server_failure():
    """Test running server process when it fails to start."""
    cmd = ["/fake/llama-server", "-m", "/path/to/model.gguf"]
    
    with patch('subprocess.Popen', side_effect=subprocess.SubprocessError("Failed to start")):
        with pytest.raises(RuntimeError, match="Failed to start llama server: Failed to start"):
            llama_server.run_server(cmd)
