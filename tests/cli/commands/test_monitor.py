"""Tests for the monitoring functions in serve.py."""
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llamate.cli.commands.serve import monitor_config_files, terminate_process


@pytest.fixture
def mock_process():
    """Create a mock process for testing."""
    process = MagicMock()
    process.poll.return_value = None  # Process is running
    process.pid = 12345
    return process


@pytest.fixture
def mock_environment():
    """Create a mock environment with config and model files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_file = temp_path / "config.yaml"
        models_dir = temp_path / "models"
        models_dir.mkdir(exist_ok=True)

        # Create main config file
        with open(config_file, "w") as f:
            f.write("initial config content")

        # Create a model file
        model_file = models_dir / "model1.yaml"
        with open(model_file, "w") as f:
            f.write("initial model content")

        yield {
            "temp_dir": temp_path,
            "config_file": config_file,
            "models_dir": models_dir,
            "model_file": model_file,
        }


def test_monitor_config_file_change(mock_process, mock_environment):
    """Test that monitor_config_files detects changes to the main config file."""
    stop_event = threading.Event()
    process_terminated = threading.Event()

    # Override terminate_process to record that it was called
    def mock_terminate(proc):
        process_terminated.set()

    with patch("llamate.cli.commands.serve.terminate_process", mock_terminate):
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_config_files,
            args=(
                mock_environment["config_file"],
                mock_environment["models_dir"],
                mock_process,
                stop_event,
            ),
        )
        monitor_thread.daemon = True
        monitor_thread.start()

        # Give monitoring time to initialize
        time.sleep(1)

        # Modify the config file
        with open(mock_environment["config_file"], "w") as f:
            f.write("modified config content")

        # Give time for the monitor to detect the change
        timeout = 10
        start_time = time.time()
        while not process_terminated.is_set() and time.time() - start_time < timeout:
            time.sleep(0.5)

        # Stop the monitoring thread
        stop_event.set()
        monitor_thread.join(timeout=5)

        # Assert that terminate_process was called
        assert process_terminated.is_set(), "Process termination was not triggered by config file change"


def test_monitor_model_file_change(mock_process, mock_environment):
    """Test that monitor_config_files detects changes to model config files."""
    stop_event = threading.Event()
    process_terminated = threading.Event()

    # Override terminate_process to record that it was called
    def mock_terminate(proc):
        process_terminated.set()

    with patch("llamate.cli.commands.serve.terminate_process", mock_terminate):
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_config_files,
            args=(
                mock_environment["config_file"],
                mock_environment["models_dir"],
                mock_process,
                stop_event,
            ),
        )
        monitor_thread.daemon = True
        monitor_thread.start()

        # Give monitoring time to initialize
        time.sleep(1)

        # Modify the model file
        with open(mock_environment["model_file"], "w") as f:
            f.write("modified model content")

        # Give time for the monitor to detect the change
        timeout = 10
        start_time = time.time()
        while not process_terminated.is_set() and time.time() - start_time < timeout:
            time.sleep(0.5)

        # Stop the monitoring thread
        stop_event.set()
        monitor_thread.join(timeout=5)

        # Assert that terminate_process was called
        assert process_terminated.is_set(), "Process termination was not triggered by model file change"


def test_monitor_new_model_file(mock_process, mock_environment):
    """Test that monitor_config_files detects when a new model file is added."""
    stop_event = threading.Event()
    process_terminated = threading.Event()

    # Override terminate_process to record that it was called
    def mock_terminate(proc):
        process_terminated.set()

    with patch("llamate.cli.commands.serve.terminate_process", mock_terminate):
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_config_files,
            args=(
                mock_environment["config_file"],
                mock_environment["models_dir"],
                mock_process,
                stop_event,
            ),
        )
        monitor_thread.daemon = True
        monitor_thread.start()

        # Give monitoring time to initialize
        time.sleep(1)

        # Create a new model file
        new_model_file = mock_environment["models_dir"] / "new_model.yaml"
        with open(new_model_file, "w") as f:
            f.write("new model content")

        # Give time for the monitor to detect the change
        timeout = 10
        start_time = time.time()
        while not process_terminated.is_set() and time.time() - start_time < timeout:
            time.sleep(0.5)

        # Stop the monitoring thread
        stop_event.set()
        monitor_thread.join(timeout=5)

        # Clean up the new file
        try:
            os.unlink(new_model_file)
        except:
            pass

        # Assert that terminate_process was called
        assert process_terminated.is_set(), "Process termination was not triggered by new model file"


def test_monitor_delete_model_file(mock_process, mock_environment):
    """Test that monitor_config_files detects when a model file is deleted."""
    stop_event = threading.Event()
    process_terminated = threading.Event()

    # Override terminate_process to record that it was called
    def mock_terminate(proc):
        process_terminated.set()

    with patch("llamate.cli.commands.serve.terminate_process", mock_terminate):
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_config_files,
            args=(
                mock_environment["config_file"],
                mock_environment["models_dir"],
                mock_process,
                stop_event,
            ),
        )
        monitor_thread.daemon = True
        monitor_thread.start()

        # Give monitoring time to initialize
        time.sleep(1)

        # Delete the model file
        os.unlink(mock_environment["model_file"])

        # Give time for the monitor to detect the change
        timeout = 10
        start_time = time.time()
        while not process_terminated.is_set() and time.time() - start_time < timeout:
            time.sleep(0.5)

        # Stop the monitoring thread
        stop_event.set()
        monitor_thread.join(timeout=5)

        # Assert that terminate_process was called
        assert process_terminated.is_set(), "Process termination was not triggered by model file deletion"


def test_terminate_process_windows():
    """Test process termination on Windows."""
    mock_process = MagicMock()

    with patch("platform.system", return_value="Windows"):
        terminate_process(mock_process)

    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()


def test_terminate_process_unix():
    """Test process termination on Unix-like systems."""
    mock_process = MagicMock()

    with patch("platform.system", return_value="Linux"), \
         patch("os.kill") as mock_kill:
        terminate_process(mock_process)

    mock_kill.assert_called_once_with(mock_process.pid, 15)  # SIGTERM
    mock_process.wait.assert_called_once()


def test_terminate_process_force_kill():
    """Test that process is force-killed if termination fails."""
    mock_process = MagicMock()
    mock_process.wait.side_effect = Exception("Timeout")

    with patch("platform.system", return_value="Linux"), \
         patch("os.kill"):
        terminate_process(mock_process)

    mock_process.kill.assert_called_once()
    assert mock_process.wait.call_count == 2
