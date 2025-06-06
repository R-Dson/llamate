import pytest
import sys
import requests # Added import
from unittest.mock import patch, MagicMock
from io import StringIO

from llamate.cli.commands.run import run_command
from llamate.core import config
from llamate import constants

@pytest.fixture
def mock_global_config():
    """Fixture to mock global configuration."""
    with patch('llamate.core.config.load_global_config') as mock_load_config:
        mock_load_config.return_value = {"llama_swap_listen_port": 8080}
        yield

@pytest.fixture
def mock_requests_post():
    """Fixture to mock requests.post for streaming responses."""
    with patch('requests.post') as mock_post:
        yield mock_post

def create_mock_response(chunks):
    """Helper to create a mock requests response object for streaming."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = (chunk.encode('utf-8') for chunk in chunks)
    mock_response.raise_for_status.return_value = None
    return mock_response

def test_run_command_successful_conversation(mock_global_config, mock_requests_post, capsys):
    """Test a successful continuous conversation with the run command."""
    mock_requests_post.return_value.__enter__.return_value = create_mock_response([
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
        'data: {"choices": [{"delta": {"content": " there"}}]}\n',
        'data: {"choices": [{"delta": {"content": "!"}}]}\n',
        'data: {"choices": [{"delta": {}}]}\n' # End of stream
    ])

    # Simulate user input: "hi", then "exit"
    with patch('builtins.input', side_effect=["hi", "exit"]):
        run_command(MagicMock(model_name="test-model"))

    captured = capsys.readouterr()
    assert "Starting conversation with model: test-model" in captured.out
    assert "<<< Assistant: Hello there!" in captured.out
    assert "Ending conversation." in captured.out
    mock_requests_post.assert_called_once()
    args, kwargs = mock_requests_post.call_args
    assert kwargs['json']['model'] == "test-model"
    assert kwargs['json']['messages'][0]['role'] == "user"
    assert kwargs['json']['messages'][0]['content'] == "hi"
    assert kwargs['json']['stream'] is True

def test_run_command_exit_command(mock_global_config, capsys):
    """Test that the run command exits on '/bye' or 'exit'."""
    with patch('builtins.input', side_effect=["/bye"]):
        run_command(MagicMock(model_name="test-model"))
    captured = capsys.readouterr()
    assert "Ending conversation." in captured.out
    assert "Starting conversation with model: test-model" in captured.out

    with patch('builtins.input', side_effect=["exit"]):
        run_command(MagicMock(model_name="test-model"))
    captured = capsys.readouterr()
    assert "Ending conversation." in captured.out
    assert "Starting conversation with model: test-model" in captured.out

def test_run_command_server_not_running(mock_global_config, mock_requests_post, capsys):
    """Test error handling when the server is not running."""
    mock_requests_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with patch('builtins.input', side_effect=["test message"]):
        run_command(MagicMock(model_name="test-model"))

    captured = capsys.readouterr()
    assert "Error: Could not connect to the llama-swap server at http://localhost:8080/v1/chat/completions." in captured.err
    assert "Please ensure 'llamate serve' is running." in captured.err
    mock_requests_post.assert_called_once()

def test_run_command_api_error(mock_global_config, mock_requests_post, capsys):
    """Test error handling for API-specific errors (e.g., 404, 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found for url: ...")
    mock_requests_post.return_value.__enter__.return_value = mock_response

    with patch('builtins.input', side_effect=["test message"]):
        run_command(MagicMock(model_name="test-model"))

    captured = capsys.readouterr()
    assert "Error during API request: 404 Client Error: Not Found for url: ..." in captured.err
    mock_requests_post.assert_called_once()

def test_run_command_empty_response_content(mock_global_config, mock_requests_post, capsys):
    """Test handling of responses with no content (e.g., only metadata)."""
    mock_requests_post.return_value.__enter__.return_value = create_mock_response([
        'data: {"choices": [{"delta": {}}]}\n', # Empty delta
        'data: {"choices": [{"delta": {}}]}\n' # End of stream
    ])

    with patch('builtins.input', side_effect=["hello", "exit"]):
        run_command(MagicMock(model_name="test-model"))

    captured = capsys.readouterr()
    assert "<<< Assistant: " in captured.out
    assert "Hello there!" not in captured.out # Ensure no content was printed
    assert "Ending conversation." in captured.out
    mock_requests_post.assert_called_once()
    args, kwargs = mock_requests_post.call_args
    # Ensure the assistant's empty response is still added to history
    assert kwargs['json']['messages'][1]['role'] == "assistant"
    assert kwargs['json']['messages'][1]['content'] == ""