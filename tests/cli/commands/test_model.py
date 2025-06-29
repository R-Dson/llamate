"""Tests for model management commands."""
from unittest.mock import MagicMock, patch

import pytest

from llamate import constants
from llamate.cli.commands import model as model_commands
from llamate.cli.commands.model import (
    model_add_command,
    model_list_command,
    model_remove_command,
)
from llamate.utils.exceptions import InvalidInputError


@pytest.fixture
def mock_model_commands(tmp_path):
    """Mock components needed for model command tests"""
    mock_global_config = {"llama_server_path": "/fake/server", "ggufs_storage_path": str(tmp_path / "ggufs")}
    mock_model_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}

    with (
        patch('llamate.core.config.load_global_config', return_value=mock_global_config) as mock_load_global_config,
        patch('llamate.core.config.save_global_config') as mock_save_global_config,
        patch('llamate.core.config.load_model_config', return_value=mock_model_config.copy()) as mock_load_model_config,
        patch('llamate.core.config.save_model_config') as mock_save_model_config,
        patch('llamate.core.model.parse_model_alias', return_value=None) as mock_parse_alias,
        patch('llamate.core.model.parse_hf_spec', return_value=("test/repo", "test.gguf")) as mock_parse_hf_spec,
        patch('llamate.core.model.validate_model_name', side_effect=lambda x: x) as mock_validate_name,
        patch('llamate.core.model.validate_args_list', side_effect=lambda x: {k.split('=')[0]: k.split('=')[1] for k in x} if x else {}) as mock_validate_args,
        patch('llamate.core.model.configure_gpu', side_effect=lambda cfg, name, **kwargs: cfg) as mock_configure_gpu,
        patch('llamate.constants.LLAMATE_HOME', tmp_path / ".config" / "llamate"),
        patch('llamate.constants.MODELS_DIR', tmp_path / ".config" / "llamate" / "models"),
        patch('llamate.constants.GGUFS_DIR', tmp_path / "ggufs"),
        patch('pathlib.Path.exists') as mock_path_exists, # Changed to not have a default return value
        patch('pathlib.Path.unlink') as mock_path_unlink,
        patch('llamate.services.llama_swap.save_llama_swap_config') as mock_save_llama_swap_config
    ):
        # Set the default return value for Path.exists
        mock_path_exists.return_value = True
        yield {
            "mock_load_global_config": mock_load_global_config,
            "mock_save_global_config": mock_save_global_config,
            "mock_load_model_config": mock_load_model_config,
            "mock_save_model_config": mock_save_model_config,
            "mock_parse_alias": mock_parse_alias,
            "mock_parse_hf_spec": mock_parse_hf_spec,
            "mock_validate_name": mock_validate_name,
            "mock_validate_args": mock_validate_args,
            "mock_configure_gpu": mock_configure_gpu,
            "llamate_home": constants.LLAMATE_HOME,
            "models_dir": constants.MODELS_DIR,
            "ggufs_dir": constants.GGUFS_DIR,
            "mock_path_exists": mock_path_exists,
            "mock_path_unlink": mock_path_unlink,
            "mock_save_llama_swap_config": mock_save_llama_swap_config,
            "tmp_path": tmp_path
        }

def test_model_add_command_invalid_alias(mock_model_commands, capsys):
    """Test adding a model with invalid alias format"""
    mocks = mock_model_commands
    mocks["mock_parse_alias"].side_effect = InvalidInputError("Invalid alias format")
    args = MagicMock(hf_spec="invalid@alias", alias=None, set=None, auto_gpu=True)

    with pytest.raises(InvalidInputError) as excinfo:
        model_add_command(args)

    assert "Invalid alias format" in str(excinfo.value)
    mocks["mock_save_model_config"].assert_not_called()

def test_model_add_command_invalid_hf_spec(mock_model_commands, capsys):
    """Test adding a model with invalid HF spec"""
    mocks = mock_model_commands
    mocks["mock_parse_hf_spec"].side_effect = InvalidInputError("Invalid HF spec")
    args = MagicMock(hf_spec="invalid/repo:spec", alias=None, set=None, auto_gpu=True)

    with pytest.raises(InvalidInputError) as excinfo:
        model_add_command(args)

    assert "Invalid HF spec" in str(excinfo.value)
    mocks["mock_save_model_config"].assert_not_called()

def test_model_add_command_not_initialized(mock_model_commands, capsys):
    """Test adding a model when llamate is not initialized."""
    mocks = mock_model_commands
    mocks["mock_path_exists"].return_value = False # Simulate LLAMATE_HOME does not exist
    args = MagicMock(hf_spec="user/repo:model.gguf", alias=None, set=None, auto_gpu=True)

    with pytest.raises(SystemExit) as excinfo:
        model_add_command(args)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "llamate is not initialized. Run 'llamate init' first." in captured.out
    mocks["mock_save_model_config"].assert_not_called()

def test_model_add_command_invalid_args(mock_model_commands, capsys):
    """Test adding a model with invalid arguments"""
    mocks = mock_model_commands
    mocks["mock_validate_args"].side_effect = InvalidInputError("Invalid argument format")
    args = MagicMock(hf_spec="user/repo:model.gguf", alias=None, set=["invalid=arg"], auto_gpu=True)

    with pytest.raises(InvalidInputError) as excinfo:
        model_add_command(args)

    assert "Invalid argument format" in str(excinfo.value)
    mocks["mock_save_model_config"].assert_not_called()

def test_model_list_command_no_models_dir(mock_model_commands, capsys):
    """Test listing models when models directory does not exist."""
    mocks = mock_model_commands
    mocks["mock_path_exists"].return_value = False
    args = MagicMock()

    model_list_command(args)

    captured = capsys.readouterr()
    assert "No models defined" in captured.out
    mocks["mock_load_model_config"].assert_not_called()

def test_model_remove_command_success(mock_model_commands, capsys, monkeypatch):
    """Test removing a model successfully with prompt response 'n'."""
    mocks = mock_model_commands
    model_name = "test_model"
    args = MagicMock(model_name=model_name, delete_gguf=False)

    # Simulate user input 'n'
    monkeypatch.setattr('builtins.input', lambda prompt=None: 'n')

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    mocks["mock_path_unlink"].assert_called_once() # For the model yaml file
    mocks["mock_load_global_config"].assert_called_once()
    mocks["mock_save_global_config"].assert_not_called()  # No aliases to remove in this test
    captured = capsys.readouterr()
    assert f"Model '{model_name}' definition removed." in captured.out
    assert "Do you want to remove the GGUF file" in captured.out
    # Check that the removal message is not present
    assert "GGUF file 'test.gguf' removed." not in captured.out

def test_model_remove_command_prompt_yes(mock_model_commands, capsys, monkeypatch):
    """Test removing a model with prompt response 'y'."""
    mocks = mock_model_commands
    model_name = "test_model"
    mocks["mock_load_model_config"].return_value = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    args = MagicMock(model_name=model_name, delete_gguf=False)

    # Simulate user input 'y'
    monkeypatch.setattr('builtins.input', lambda prompt=None: 'y')

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    assert mocks["mock_path_unlink"].call_count == 2 # For the model yaml and the gguf file
    mocks["mock_load_global_config"].assert_called()
    assert mocks["mock_load_global_config"].call_count == 1
    captured = capsys.readouterr()
    assert f"Model '{model_name}' definition removed." in captured.out
    assert "Do you want to remove the GGUF file" in captured.out
    assert "GGUF file 'test.gguf' removed." in captured.out

def test_model_remove_command_delete_gguf(mock_model_commands, capsys, monkeypatch):
    """Test removing a model with --delete-gguf flag (no prompt)."""
    mocks = mock_model_commands
    model_name = "test_model"
    mocks["mock_load_model_config"].return_value = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    args = MagicMock(model_name=model_name, delete_gguf=True)

    # Ensure input isn't called
    monkeypatch.setattr('builtins.input', lambda _: pytest.fail("Input should not be called with --delete-gguf"))

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    assert mocks["mock_path_unlink"].call_count == 2 # For the model yaml and the gguf file
    mocks["mock_load_global_config"].assert_called()
    assert mocks["mock_load_global_config"].call_count == 1
    captured = capsys.readouterr()
    assert f"Model '{model_name}' definition removed." in captured.out
    assert "GGUF file 'test.gguf' removed." in captured.out
    assert "Do you want to remove the GGUF file" not in captured.out

def test_model_remove_command_model_not_found(mock_model_commands, capsys):
    """Test removing a non-existent model."""
    mocks = mock_model_commands
    model_name = "non_existent"
    mocks["mock_load_model_config"].side_effect = ValueError(f"Model '{model_name}' not found")
    args = MagicMock(model_name=model_name, delete_gguf=False)

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    mocks["mock_path_unlink"].assert_not_called()
    captured = capsys.readouterr()
    assert f"Error: Model '{model_name}' not found" in captured.out

def test_model_copy_command_success(mock_model_commands, capsys):
    """Test copying a model successfully."""
    mocks = mock_model_commands
    source_model_name = "source_model"
    new_model_name = "new_model"

    # Mock resolve_model_name to return the source_model_name directly
    with patch('llamate.cli.commands.model.resolve_model_name', return_value=source_model_name) as mock_resolve_model_name:
        # Mock model_file.exists() to return False for the new model
        new_model_path = mocks["models_dir"] / f"{new_model_name}.yaml"
        # Set up the mock for path.exists to return False for the new model file and True for others
        mocks["mock_path_exists"].side_effect = [True, False]
        mocks["mock_load_global_config"].return_value = {"aliases": {}}

        args = MagicMock(source_model=source_model_name, new_model_name=new_model_name)

        model_commands.model_copy_command(args)

        mock_resolve_model_name.assert_called_once_with(source_model_name)
        mocks["mock_load_model_config"].assert_called_once_with(source_model_name)
        mocks["mock_save_model_config"].assert_called_with(new_model_name, mocks["mock_load_model_config"].return_value)
        captured = capsys.readouterr()
        assert f"Model '{source_model_name}' copied to '{new_model_name}'." in captured.out

def test_model_copy_command_source_alias(mock_model_commands, capsys):
    """Test copying a model using an alias as the source."""
    mocks = mock_model_commands
    source_alias = "my_alias"
    actual_source_model = "actual_source_model"
    new_model_name = "new_model_from_alias"

    with patch('llamate.cli.commands.model.resolve_model_name', return_value=actual_source_model) as mock_resolve_model_name:
        new_model_path = mocks["models_dir"] / f"{new_model_name}.yaml"
        mocks["mock_path_exists"].side_effect = [True, False]


        mocks["mock_load_global_config"].return_value = {"aliases": {}}

        args = MagicMock(source_model=source_alias, new_model_name=new_model_name)

        model_commands.model_copy_command(args)

        mock_resolve_model_name.assert_called_once_with(source_alias)
        mocks["mock_load_model_config"].assert_called_once_with(actual_source_model)
        mocks["mock_save_model_config"].assert_called_with(new_model_name, mocks["mock_load_model_config"].return_value)
        captured = capsys.readouterr()
        assert f"Model '{actual_source_model}' copied to '{new_model_name}'." in captured.out

def test_model_copy_command_same_name_error(mock_model_commands, capsys):
    """Test copying a model to the same name."""
    mocks = mock_model_commands
    model_name = "test_model"

    with patch('llamate.cli.commands.model.resolve_model_name', return_value=model_name):
        args = MagicMock(source_model=model_name, new_model_name=model_name)

        with pytest.raises(SystemExit) as excinfo:
            model_commands.model_copy_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Source and new model names must be different." in captured.err
        mocks["mock_save_model_config"].assert_not_called()

def test_model_copy_command_new_name_exists_as_model(mock_model_commands, capsys):
    """Test copying a model when the new name already exists as a model."""
    mocks = mock_model_commands
    source_model_name = "source_model"
    existing_model_name = "existing_model"

    with patch('llamate.cli.commands.model.resolve_model_name', return_value=source_model_name):
        # Rely on default mock_path_exists behavior (returns True for all paths)
        args = MagicMock(source_model=source_model_name, new_model_name=existing_model_name)

        with pytest.raises(SystemExit) as excinfo:
            model_commands.model_copy_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: Model '{existing_model_name}' already exists." in captured.err
        mocks["mock_save_model_config"].assert_not_called()

def test_model_copy_command_new_name_exists_as_alias(mock_model_commands, capsys):
    """Test copying a model when the new name already exists as an alias."""
    mocks = mock_model_commands
    source_model_name = "source_model"
    existing_alias = "existing_alias"

    with patch('llamate.cli.commands.model.resolve_model_name', return_value=source_model_name):
        mocks["mock_path_exists"].side_effect = [True, False]
        mocks["mock_load_global_config"].return_value = {"aliases": {existing_alias: "some_other_model"}}

        args = MagicMock(source_model=source_model_name, new_model_name=existing_alias)

        with pytest.raises(SystemExit) as excinfo:
            model_commands.model_copy_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: '{existing_alias}' is already used as an alias for model 'some_other_model'." in captured.err
        mocks["mock_save_model_config"].assert_not_called()

def test_model_copy_command_source_not_found(mock_model_commands, capsys):
    """Test copying a model when the source model is not found."""
    mocks = mock_model_commands
    source_model_name = "non_existent_source"
    new_model_name = "new_model"

    with patch('llamate.cli.commands.model.resolve_model_name', side_effect=ValueError(f"Model '{source_model_name}' not found")) as mock_resolve_model_name:
        args = MagicMock(source_model=source_model_name, new_model_name=new_model_name)

        with pytest.raises(SystemExit) as excinfo:
            model_commands.model_copy_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: Model '{source_model_name}' not found" in captured.err
        mocks["mock_save_model_config"].assert_not_called()

def test_model_copy_command_not_initialized(mock_model_commands, capsys):
    """Test copying a model when llamate is not initialized."""
    mocks = mock_model_commands
    # Use *args and **kwargs to handle calls without arguments during teardown
    mocks["mock_path_exists"].side_effect = [False, True]
    source_model_name = "source_model"
    new_model_name = "new_model"

    args = MagicMock(source_model=source_model_name, new_model_name=new_model_name)

    with pytest.raises(SystemExit) as excinfo:
        model_commands.model_copy_command(args)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "llamate is not initialized. Run 'llamate init' first." in captured.out
    mocks["mock_save_model_config"].assert_not_called()
