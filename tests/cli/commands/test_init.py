"""Tests for the init command."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from llamate.cli.commands.init import init_command
from llamate.core import config
from llamate import constants

# Fixture to mock necessary components for init_command tests
@pytest.fixture(autouse=True)
def mock_stdout():
    stdout = StringIO()

    def mock_print(*args, **kwargs):
        output = ' '.join(str(arg) for arg in args)
        if 'file' in kwargs:
            kwargs['file'].write(output + '\n')
        else:
            stdout.write(output + '\n')

    def default_input(prompt=''):
        stdout.write(prompt)  # Capture the prompt
        return ''

    with patch('builtins.print', mock_print):
        yield stdout

def patch_input(side_effects, stdout):
    """Helper function to patch input while capturing prompts"""
    def mock_input(prompt):
        stdout.write(prompt)  # Capture the prompt
        return side_effects.pop(0)
    return patch('builtins.input', mock_input)

@pytest.fixture
def mock_init_command(tmp_path):
    mock_global_config = {"llama_server_path": ""}

    with (
        patch('llamate.core.config.load_global_config', return_value=mock_global_config) as mock_load_config,
        patch('llamate.core.config.save_global_config') as mock_save_config,
        patch('llamate.services.llama_swap.download_binary', return_value=tmp_path / "mock_archive.tar.gz") as mock_download,
        patch('llamate.services.llama_swap.extract_binary') as mock_extract,
        patch('llamate.constants.LLAMATE_HOME', tmp_path / ".config" / "llamate"),
        patch('llamate.constants.MODELS_DIR', tmp_path / ".config" / "llamate" / "models"),
        patch('llamate.constants.GGUFS_DIR', tmp_path / ".config" / "llamate" / "ggufs")
    ):
        
        # Ensure LLAMATE_HOME does not exist initially for first-run tests
        if constants.LLAMATE_HOME.exists():
            import shutil
            shutil.rmtree(constants.LLAMATE_HOME)

        yield {
            "mock_load_config": mock_load_config,
            "mock_save_config": mock_save_config,
            "mock_download": mock_download,
            "mock_extract": mock_extract,
            "llamate_home": constants.LLAMATE_HOME,
            "tmp_path": tmp_path
        }

def test_init_command_first_run_success(mock_init_command, mock_stdout):
    """Test successful first-time initialization"""
    mocks = mock_init_command
    mock_llama_server_path = "/fake/path/to/llama-server"

    # Mock both the path input and the confirmation since the path doesn't exist
    with patch_input([mock_llama_server_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

    # Assert directories were created
    assert mocks["llamate_home"].exists()
    assert constants.MODELS_DIR.exists()
    assert constants.GGUFS_DIR.exists()

    # Assert config was loaded and saved with the correct path
    mocks["mock_load_config"].assert_called_once()
    mocks["mock_save_config"].assert_called_once()
    saved_config = mocks["mock_save_config"].call_args[0][0]
    assert saved_config["llama_server_path"] == mock_llama_server_path

    # Assert download and extract were called
    mocks["mock_download"].assert_called_once_with(mocks["llamate_home"] / "bin", None)
    mocks["mock_extract"].assert_called_once_with(mocks["tmp_path"] / "mock_archive.tar.gz", mocks["llamate_home"] / "bin")

    # Assert success messages were printed (basic check)
    output = mock_stdout.getvalue()
    assert "Welcome to llamate!" in output
    assert "Initialization complete!" in output

def test_init_command_already_initialized(mock_init_command, mock_stdout):
    """Test initialization when llamate is already initialized"""
    mocks = mock_init_command
    mocks["llamate_home"].mkdir(parents=True, exist_ok=True)
    mock_llama_server_path = "/fake/path/to/llama-server"

    # Mock both the path input and the confirmation since the path doesn't exist
    with patch_input([mock_llama_server_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

    # Assert directories were created (idempotent)
    assert mocks["llamate_home"].exists()
    assert constants.MODELS_DIR.exists()
    assert constants.GGUFS_DIR.exists()

    # Assert config was loaded and saved with the correct path
    mocks["mock_load_config"].assert_called_once()
    mocks["mock_save_config"].assert_called_once()
    saved_config = mocks["mock_save_config"].call_args[0][0]
    assert saved_config["llama_server_path"] == mock_llama_server_path

    # Assert download and extract were called (should still happen for updates)
    mocks["mock_download"].assert_called_once_with(mocks["llamate_home"] / "bin", None)
    mocks["mock_extract"].assert_called_once_with(mocks["tmp_path"] / "mock_archive.tar.gz", mocks["llamate_home"] / "bin")

    # Assert welcome message is NOT printed
    output = mock_stdout.getvalue()
    assert "Welcome to llamate!" not in output
    assert "Initialization complete!" in output

def test_init_command_empty_path_input(mock_init_command, mock_stdout):
    """Test init_command with empty llama-server path input"""
    mocks = mock_init_command
    mock_llama_server_path = "/fake/path/to/llama-server"        # Simulate entering empty path then a valid path with confirmation
    with patch_input(["", mock_llama_server_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

    # Assert config was saved with the correct path after the second input
    mocks["mock_save_config"].assert_called_once()
    saved_config = mocks["mock_save_config"].call_args[0][0]
    assert saved_config["llama_server_path"] == mock_llama_server_path

    # Assert error message for empty path was printed
    output = mock_stdout.getvalue()
    assert "Error: llama-server path cannot be empty." in output

def test_init_command_non_existent_path_confirm(mock_init_command, mock_stdout):
    """Test init_command with non-existent path and user confirms"""
    mocks = mock_init_command
    mock_llama_server_path = "/non/existent/path/to/llama-server"        # Simulate entering non-existent path and confirming, then confirm download
    with patch_input([mock_llama_server_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

        # Assert config was saved with the non-existent path
        mocks["mock_save_config"].assert_called_once()
        saved_config = mocks["mock_save_config"].call_args[0][0]
        assert saved_config["llama_server_path"] == mock_llama_server_path

    # Assert warning and confirmation prompt were printed
    output = mock_stdout.getvalue()
    assert f"Warning: Path '{mock_llama_server_path}' does not exist." in output
    assert "Do you want to use this path anyway? (y/N):" in output

def test_init_command_non_existent_path_deny_then_valid(mock_init_command, mock_stdout):
    """Test init_command with non-existent path, user denies, then enters valid path"""
    mocks = mock_init_command
    non_existent_path = "/non/existent/path"
    valid_path = "/fake/valid/path"        # Simulate entering non-existent path, denying, then entering valid path with confirmation
    with patch_input([non_existent_path, "n", valid_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

    # Assert config was saved with the valid path
    mocks["mock_save_config"].assert_called_once()
    saved_config = mocks["mock_save_config"].call_args[0][0]
    assert saved_config["llama_server_path"] == valid_path

    # Assert warning and confirmation prompt were printed, and then the prompt for path again
    output = mock_stdout.getvalue()
    assert f"Warning: Path '{non_existent_path}' does not exist." in output
    assert "Do you want to use this path anyway? (y/N):" in output
    assert "Enter the full path to your llama-server binary:" in output # Should prompt again

def test_init_command_path_is_directory(mock_init_command, mock_stdout):
    """Test init_command when the provided path is a directory"""
    mocks = mock_init_command
    directory_path = mocks["tmp_path"] / "a_directory"
    directory_path.mkdir()
    valid_path = "/fake/valid/path"        # Simulate entering a directory path, then a valid path with confirmation
    with patch_input([str(directory_path), valid_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

    # Assert config was saved with the valid path
    mocks["mock_save_config"].assert_called_once()
    saved_config = mocks["mock_save_config"].call_args[0][0]
    assert saved_config["llama_server_path"] == valid_path

    # Assert error message for directory was printed
    output = mock_stdout.getvalue()
    expected_error_message = f"Error: '{directory_path}' is not a file."
    assert expected_error_message in output

def test_init_command_download_failure(mock_init_command, mock_stdout):
    """Test init_command when download_binary fails"""
    mocks = mock_init_command
    mock_llama_server_path = "/fake/path/to/llama-server"

    mocks["mock_download"].side_effect = Exception("Download failed")

    # Mock the path input, the confirmation for non-existent path, and potential confirmations after download failure
    with patch_input([mock_llama_server_path, "y"], mock_stdout):
        with pytest.raises(Exception, match="Download failed"):
            init_command(MagicMock(arch=None))

    # Assert directories were created and config saved despite download failure
    assert mocks["llamate_home"].exists()
    assert constants.MODELS_DIR.exists()
    assert constants.GGUFS_DIR.exists()
    mocks["mock_save_config"].assert_called_once()

    # Assert download was called, but extract was not
    mocks["mock_download"].assert_called_once()
    mocks["mock_extract"].assert_not_called()

    # Assert warning message was printed
    output = mock_stdout.getvalue()
    assert "Warning: Failed to download llama-swap: Download failed" in output
