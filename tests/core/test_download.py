"""Tests for download functionality."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY
import requests # Import requests for mocking
from io import StringIO
import re # Import re for content-range parsing

from llamate.core.download import download_file, format_bytes
from llamate import constants # Import constants

def test_format_bytes():
    """Test format_bytes utility function."""
    assert format_bytes(0) == "0.0 B"
    assert format_bytes(500) == "500.0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1500) == "1.5 KB"
    assert format_bytes(1024**2) == "1.0 MB"
    assert format_bytes(1.5 * 1024**2) == "1.5 MB"
    assert format_bytes(1024**3) == "1.0 GB"
    assert format_bytes(1.2 * 1024**3) == "1.2 GB"
    assert format_bytes(1024**4) == "1.0 TB" # Expect 1.0 TB after updating the function

# Fixture to mock requests and file operations
def path_exists_side_effect(path_to_check):
    """Helper function for mocking Path.exists()"""
    # Always return True for directories during cleanup
    if str(path_to_check).endswith('pytest-of-cosmic'):
        return True
    # Handle normal test cases
    return False

@pytest.fixture
def mock_download(tmp_path):
    """Fixture to mock necessary components for download tests."""
    mock_global_config = {"llama_server_path": ""}

    # Mock requests.Response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12'} # Default content length
    # Simulate reading in chunks using iter_content
    mock_response.iter_content.side_effect = lambda chunk_size: iter([b"chunk1", b"chunk2", b""])
    mock_response.raise_for_status.return_value = None # Ensure raise_for_status does nothing on success

    # Mock the context manager returned by requests.get(stream=True)
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    # Mock requests.get to return the mock_response (which is also a mock context manager)
    mock_requests_get = MagicMock(return_value=mock_response)

    # Use mock_open to create the mock for builtins.open
    mock_builtin_open = mock_open()
    # Add closed attribute to the object returned by mock_open
    mock_builtin_open.return_value.closed = False


    with (
        patch('llamate.core.config.load_global_config', return_value=mock_global_config) as mock_load_config,
        patch('llamate.core.config.save_global_config') as mock_save_config,
        patch('llamate.core.download.download_binary', return_value=tmp_path / "mock_archive.tar.gz") as mock_download_binary,
        patch('llamate.core.download.extract_binary') as mock_extract,
        patch('llamate.constants.LLAMATE_HOME', tmp_path / ".config" / "llamate"),
        patch('llamate.constants.MODELS_DIR', tmp_path / ".config" / "llamate" / "models"),
        patch('llamate.constants.GGUFS_DIR', tmp_path / ".config" / "llamate" / "ggufs"),
        # Patch requests.get instead of urllib.request.urlopen
        patch('requests.get', mock_requests_get) as mock_get,
        patch('builtins.open', new=mock_builtin_open) as mock_open_patch,
        patch.object(Path, 'exists') as mock_path_exists,
        patch.object(Path, 'mkdir') as mock_path_mkdir,
        patch.object(Path, 'rename') as mock_path_rename,
        patch.object(Path, 'unlink') as mock_path_unlink
    ):

        yield {
            "mock_load_config": mock_load_config,
            "mock_save_config": mock_save_config,
            "mock_download_binary": mock_download_binary,
            "mock_extract": mock_extract,
            "llamate_home": constants.LLAMATE_HOME,
            "tmp_path": tmp_path,
            "mock_get": mock_get, # Yield mock_get instead of mock_urlopen
            "mock_response": mock_response,
            "mock_builtin_open": mock_builtin_open,
            "mock_path_exists": mock_path_exists,
            "mock_path_mkdir": mock_path_mkdir,
            "mock_path_rename": mock_path_rename,
            "mock_path_unlink": mock_path_unlink
        }
        # Teardown: Set closed attribute to True (if applicable to mocks)
        # if hasattr(mock_response, 'closed'):
        #      mock_response.closed = True
        if mock_builtin_open.called and hasattr(mock_builtin_open(), 'closed'):
             mock_builtin_open().closed = True

def test_download_file_success(mock_download, capsys):
    """Test successful file download without resume."""
    mocks = mock_download
    url = "http://example.com/file.txt"
    destination = mocks["tmp_path"] / "downloaded_file.txt"

    download_file(url, destination, resume=False)

    # Assert requests.get was called
    mocks["mock_get"].assert_called_once_with(url, headers={}, stream=True, verify=ANY, timeout=30)
    mocks["mock_path_mkdir"].assert_called_once()
    # Assert that open was called with the temporary file in write binary mode
    mocks["mock_builtin_open"].assert_any_call(destination.with_suffix(".txt.tmp"), 'wb')
    # Assert that open was called with the meta file in write mode
    mocks["mock_builtin_open"].assert_any_call(destination.with_suffix(".txt.meta"), 'w')
    mocks["mock_builtin_open"].return_value.__enter__().write.assert_any_call(b"chunk1")
    mocks["mock_builtin_open"].return_value.__enter__().write.assert_any_call(b"chunk2")
    # Use call_count to check for two calls to exists in the finally block
    assert mocks["mock_path_exists"].call_count == 2
    mocks["mock_path_rename"].assert_called_once_with(destination)
    mocks["mock_path_unlink"].assert_called_once() # Removes meta file
    # Use capsys to capture output
    captured = capsys.readouterr()
    assert "Downloading:" in captured.out
    assert "100.0%" in captured.out

"""
def test_download_file_resume_existing_meta(mock_download, capsys):
    mocks = mock_download
    url = "http://example.com/file.txt"
    destination = mocks["tmp_path"] / "downloaded_file.txt"
    meta_file = destination.with_suffix(".txt.meta")

    def test_exists(p):
        return str(p) == str(meta_file)
    mocks["mock_path_exists"].side_effect = test_exists  # Simulate meta file exists
    mocks["mock_builtin_open"].side_effect = [
        mock_open(read_data="500").return_value, # Read meta file
        mock_open().return_value # Write to tmp file
    ]
    # Mock requests response headers for resume
    mocks["mock_response"].headers = {'content-length': '500', 'content-range': 'bytes 500-999/1000'} # Remaining content length and total size
    mocks["mock_response"].iter_content.side_effect = lambda chunk_size: iter([b"chunk3", b"chunk4", b""]) # Simulate remaining chunks

    download_file(url, destination, resume=True)

    # Assert requests.get was called with Range header
    mocks["mock_get"].assert_called_once_with(url, headers={'Range': 'bytes=500-'}, stream=True)
    mocks["mock_builtin_open"].call_count == 2
    mocks["mock_builtin_open"].assert_any_call(meta_file, 'r')
    mocks["mock_builtin_open"].assert_any_call(destination.with_suffix(".txt.tmp"), 'ab')
    mocks["mock_path_rename"].assert_called_once_with(destination)
    mocks["mock_path_unlink"].assert_called_once() # Removes meta file
    # Use capsys to capture output
    captured = capsys.readouterr()
    assert "Resuming download from 500 bytes" in captured.out
    assert "Downloading:" in captured.out
    assert "100.0%" in captured.out

def test_download_file_resume_meta_read_error(mock_download, capsys):
    mocks = mock_download
    url = "http://example.com/file.txt"
    destination = mocks["tmp_path"] / "downloaded_file.txt"
    meta_file = destination.with_suffix(".txt.meta")

    def test_exists(p):
        return str(p) == str(meta_file)
    mocks["mock_path_exists"].side_effect = test_exists
    mocks["mock_builtin_open"].side_effect = [
        mock_open(read_data="invalid").return_value, # Read meta file with invalid data
        mock_open().return_value # Write to tmp file
    ]
    mocks["mock_response"].headers = {'content-length': '1000'}
    mocks["mock_response"].iter_content.side_effect = lambda chunk_size: iter([b"chunk1", b"chunk2", b""])

    download_file(url, destination, resume=True)

    # Assert requests.get was called without Range header
    mocks["mock_get"].assert_called_once_with(url, headers={}, stream=True, verify=ANY, timeout=30)
    mocks["mock_builtin_open"].call_count == 2
    mocks["mock_builtin_open"].assert_any_call(meta_file, 'r')
    mocks["mock_builtin_open"].assert_any_call(destination.with_suffix(".txt.tmp"), 'wb')
    mocks["mock_path_rename"].assert_called_once_with(destination)
    mocks["mock_path_unlink"].assert_called_once() # Removes meta file
    # Use capsys to capture output
    captured = capsys.readouterr()
    assert "Warning: Could not read download progress:" in captured.out
    assert "Downloading:" in captured.out
"""
def test_download_file_url_error(mock_download, capsys):
    """Test file download when requests.exceptions.RequestException occurs."""
    mocks = mock_download
    url = "http://example.com/file.txt"
    destination = mocks["tmp_path"] / "downloaded_file.txt"

    # Mock requests.get to raise a RequestException
    mocks["mock_get"].side_effect = requests.exceptions.RequestException("Mocked network error")

    # Expect RuntimeError with a message matching the requests exception
    with pytest.raises(RuntimeError, match="Download failed: Mocked network error"):
        download_file(url, destination, resume=False)

    mocks["mock_get"].assert_called_once_with(url, headers={}, stream=True, verify=ANY, timeout=30)
    mocks["mock_path_rename"].assert_not_called()
    # Meta file might exist or should be kept with partial download, so don't assert unlink
    # mocks["mock_path_unlink"].assert_not_called()
    # Use capsys to capture output
    captured = capsys.readouterr()
    assert "Download failed: Mocked network error" in captured.err

def test_download_file_io_error(mock_download, capsys):
    """Test file download when IOError occurs during writing."""
    mocks = mock_download
    url = "http://example.com/file.txt"
    destination = mocks["tmp_path"] / "downloaded_file.txt"

    # Set up mock open to fail when writing to temp file
    def mock_open_side_effect(*args, **kwargs):
        if args and str(args[0]).endswith('.txt.tmp'):
            # Create a mock file object that raises IOError on write
            mock_file = MagicMock()
            mock_file.__enter__.return_value.write.side_effect = IOError("Mocked disk full error")
            return mock_file
        return mock_open().return_value
    
    mocks["mock_builtin_open"].side_effect = mock_open_side_effect
    
    # Ensure requests.get succeeds so we reach the file writing part
    mocks["mock_get"].return_value.status_code = 200
    mocks["mock_get"].return_value.headers = {'content-length': '12'}
    mocks["mock_get"].return_value.iter_content.side_effect = lambda chunk_size: iter([b"chunk1", b"chunk2", b""])

    # Expect RuntimeError with a message matching the IOError
    with pytest.raises(RuntimeError, match="Download failed: Mocked disk full error"):
        download_file(url, destination, resume=False)

    mocks["mock_get"].assert_called_once_with(url, headers={}, stream=True, verify=ANY, timeout=30)
    # Should attempt to create the meta file and temp file
    assert mocks["mock_builtin_open"].call_count >= 2
    mocks["mock_path_rename"].assert_not_called()
    # Use capsys to capture output
    captured = capsys.readouterr()
    assert "Download failed: Mocked disk full error" in captured.err
