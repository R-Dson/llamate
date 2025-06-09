"""Tests for the init command."""
import pytest
from unittest.mock import call
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
import llamate.core.platform as platform # Import platform for get_llama_server_bin_name

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
        patch('llamate.core.download.download_binary', return_value=tmp_path / "mock_archive.tar.gz") as mock_download,
        patch('llamate.core.download.extract_binary') as mock_extract,
        patch('llamate.constants.LLAMATE_HOME', tmp_path / ".config" / "llamate"),
        patch('llamate.constants.MODELS_DIR', tmp_path / ".config" / "llamate" / "models"),
        patch('llamate.constants.GGUFS_DIR', tmp_path / ".config" / "llamate" / "ggufs")
    ):
        
        # Ensure LLAMATE_HOME does not exist initially for first-run tests
        if constants.LLAMATE_HOME.exists():
            import shutil
            shutil.rmtree(constants.LLAMATE_HOME)
            
        # Create mock archive file that download_binary would return
        mock_archive = tmp_path / "mock_archive.tar.gz"
        mock_archive.touch()
        
        # Update mock_download to return a tuple (path, sha) to match new return type
        mock_download.return_value = (mock_archive, None)

        # Modify mock_extract to simulate extraction
        def mock_extract_side_effect(archive_path, dest_dir):
            # Create a dummy llama-server binary at the expected location
            llama_server_bin_name = platform.get_llama_server_bin_name()
            (dest_dir / llama_server_bin_name).touch()
        mock_extract.side_effect = mock_extract_side_effect

        yield {
            "mock_load_config": mock_load_config,
            "mock_save_config": mock_save_config,
            "mock_download": mock_download,
            "mock_extract": mock_extract,
            "llamate_home": constants.LLAMATE_HOME,
            "tmp_path": tmp_path,
            "mock_archive": mock_archive
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
    # Should be the extracted binary path
    assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Assert download and extract were called
    assert mocks["mock_download"].call_count == 2
    llama_server_call = call(mocks["llamate_home"] / "bin", 'https://api.github.com/repos/R-Dson/llama-server-compile/releases/latest')
    llama_swap_call = call(mocks["llamate_home"] / "bin", 'https://api.github.com/repos/R-Dson/llama-swap/releases/latest')
    assert llama_server_call in mocks["mock_download"].call_args_list
    assert llama_swap_call in mocks["mock_download"].call_args_list
    assert mocks["mock_extract"].call_count == 2
    extract_llama_server_call = call(mocks["mock_archive"], mocks["llamate_home"] / "bin")
    extract_llama_swap_call = call(mocks["mock_archive"], mocks["llamate_home"] / "bin")
    assert extract_llama_server_call in mocks["mock_extract"].call_args_list
    assert extract_llama_swap_call in mocks["mock_extract"].call_args_list

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
    # Should be the extracted binary path
    assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Assert download and extract were called (should still happen for updates)
    assert mocks["mock_download"].call_count == 2
    llama_server_call = call(mocks["llamate_home"] / "bin", 'https://api.github.com/repos/R-Dson/llama-server-compile/releases/latest')
    llama_swap_call = call(mocks["llamate_home"] / "bin", 'https://api.github.com/repos/R-Dson/llama-swap/releases/latest')
    assert llama_server_call in mocks["mock_download"].call_args_list
    assert llama_swap_call in mocks["mock_download"].call_args_list
    assert mocks["mock_extract"].call_count == 2
    extract_llama_server_call = call(mocks["mock_archive"], mocks["llamate_home"] / "bin")
    extract_llama_swap_call = call(mocks["mock_archive"], mocks["llamate_home"] / "bin")
    assert extract_llama_server_call in mocks["mock_extract"].call_args_list
    assert extract_llama_swap_call in mocks["mock_extract"].call_args_list

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
    # Should be the extracted binary path
    assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Output should contain success messages
    output = mock_stdout.getvalue()
    assert "Initialization complete!" in output

def test_init_command_non_existent_path_confirm(mock_init_command, mock_stdout):
    """Test init_command with non-existent path and user confirms"""
    mocks = mock_init_command
    mock_llama_server_path = "/non/existent/path/to/llama-server"        # Simulate entering non-existent path and confirming, then confirm download
    with patch_input([mock_llama_server_path, "y"], mock_stdout):
        init_command(MagicMock(arch=None))

        # Assert config was saved with the non-existent path
        mocks["mock_save_config"].assert_called_once()
        saved_config = mocks["mock_save_config"].call_args[0][0]
        # Should be the extracted binary path
        assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Output should contain success messages
    output = mock_stdout.getvalue()
    assert "Initialization complete!" in output

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
    # Should be the extracted binary path
    assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Output should contain success messages
    output = mock_stdout.getvalue()
    assert "Initialization complete!" in output

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
    # Should be the extracted binary path
    assert saved_config["llama_server_path"] == str(mocks["llamate_home"] / "bin" / "llama-server")

    # Output should contain success messages
    output = mock_stdout.getvalue()
    assert "Initialization complete!" in output

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
    # For download failure, config should not be saved
    mocks["mock_save_config"].assert_not_called()

    # Assert download was called, but extract was not
    mocks["mock_download"].assert_called_once()
    mocks["mock_extract"].assert_not_called()

    # Assert warning message was printed
    output = mock_stdout.getvalue()
    assert "Warning: Initialization failed: Download failed" in output
    assert "You may need to manually set 'llama_server_path' in config" in output
