"""Tests for model management commands."""
import pytest
from unittest.mock import patch, MagicMock

from llamate.cli.commands.model import model_add_command, model_list_command, model_remove_command
from llamate import constants

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
        patch('pathlib.Path.exists', return_value=True) as mock_path_exists,
        patch('pathlib.Path.unlink') as mock_path_unlink
    ):
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
            "tmp_path": tmp_path
        }

# TODO: Fix test function signatures and Click command handling
"""
@patch('llamate.cli.commands.model.parse_model_alias')
@patch('llamate.cli.commands.model.add_model')
def test_model_add_command_hf_spec(mock_add_model, mock_parse_model_alias, capsys):
    # Test adding a model using HF spec
    mocks = mock_model_commands
    args = MagicMock(hf_spec="user/repo:model.gguf", alias=None, set=None, auto_gpu=True)

    model_add_command(args)

    mocks["mock_parse_alias"].assert_called_once_with("user/repo:model.gguf")
    mocks["mock_parse_hf_spec"].assert_called_once_with("user/repo:model.gguf")
    mocks["mock_validate_name"].assert_called_once_with("model")
    mocks["mock_configure_gpu"].assert_called_once()
    mocks["mock_validate_args"].assert_called_once_with(None)
    mocks["mock_save_model_config"].assert_called_once()
    saved_config = mocks["mock_save_model_config"].call_args[0][1]
    assert saved_config["hf_repo"] == "test/repo"
    assert saved_config["hf_file"] == "test.gguf"

@patch('llamate.cli.commands.model.parse_model_alias')
@patch('llamate.cli.commands.model.add_model')
def test_model_add_command_alias(mock_add_model, mock_parse_model_alias, capsys):
    # Test adding a model using a known alias
    mocks = mock_model_commands
    mock_alias_config = {"hf_repo": "alias/repo", "hf_file": "alias.gguf", "args": {"temp": "0.5"}}
    mocks["mock_parse_alias"].return_value = mock_alias_config
    args = MagicMock(hf_spec="my_alias", alias=None, set=None, auto_gpu=True)

    model_add_command(args)

    mocks["mock_parse_alias"].assert_called_once_with("my_alias")
    mocks["mock_parse_hf_spec"].assert_not_called()
    mocks["mock_validate_name"].assert_called_once_with("alias")
    mocks["mock_configure_gpu"].assert_called_once()
    mocks["mock_validate_args"].assert_called_once_with(None)
    mocks["mock_save_model_config"].assert_called_once()
    saved_config = mocks["mock_save_model_config"].call_args[0][1]
    assert saved_config["hf_repo"] == "alias/repo"
    assert saved_config["hf_file"] == "alias.gguf"
    assert saved_config["args"] == {"temp": "0.5"}

@patch('llamate.cli.commands.model.parse_model_alias')
@patch('llamate.cli.commands.model.add_model')
@patch('llamate.cli.commands.model.save_model_config')
def test_model_add_command_with_alias_override(mock_save_config, mock_add_model, mock_parse_model_alias, capsys):
    # Test adding a model using HF spec with alias override
    mocks = mock_model_commands
    args = MagicMock(hf_spec="user/repo:model.gguf", alias="custom_name", set=None, auto_gpu=True)

    model_add_command(args)

    mocks["mock_validate_name"].assert_called_once_with("custom_name")
    mocks["mock_save_model_config"].assert_called_once_with("custom_name", MagicMock())

@patch('llamate.cli.commands.model.parse_model_alias')
@patch('llamate.cli.commands.model.add_model')
@patch('llamate.cli.commands.model.save_model_config')
def test_model_add_command_with_set_args(mock_save_config, mock_add_model, mock_parse_model_alias, capsys):
    # Test adding a model with --set arguments
    mocks = mock_model_commands
    set_args = ["param1=value1", "param2=value2"]
    args = MagicMock(hf_spec="user/repo:model.gguf", alias=None, set=set_args, auto_gpu=True)

    model_add_command(args)

    mocks["mock_validate_args"].assert_called_once_with(set_args)
    mocks["mock_save_model_config"].assert_called_once()
    saved_config = mocks["mock_save_model_config"].call_args[0][1]
    assert saved_config["args"] == {"param1": "value1", "param2": "value2"}
    mocks = mock_model_commands
    args = MagicMock(hf_spec="user/repo:model.gguf", alias=None, set=None, auto_gpu=False)

    model_add_command(args)

    mocks["mock_configure_gpu"].assert_called_with(MagicMock(), "model", auto_detect=False)
"""

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

# TODO: Fix get_model_dir function and test
"""
def test_model_list_command_with_models(tmp_path, capsys):
    # Test listing models when models exist
    mocks = mock_model_commands
    mocks["mock_path_exists"].return_value = True
    
    # Create dummy model files
    model1_path = mocks["models_dir"] / "model1.yaml"
    model2_path = mocks["models_dir"] / "model2.yaml"
    mocks["models_dir"].glob = MagicMock(return_value=[model1_path, model2_path])

    # Configure mock load_model_config to return different configs
    def mock_load_side_effect(model_name):
        if (model_name == "model1"):
            return {"hf_repo": "repo1", "hf_file": "file1.gguf", "args": {}}
        elif (model_name == "model2"):
            return {"hf_repo": "repo2", "hf_file": "file2.gguf", "args": {}}
        else:
            raise ValueError("Unknown model")

    mocks["mock_load_model_config"].side_effect = mock_load_side_effect

    args = MagicMock()
    model_list_command(args)

    captured = capsys.readouterr()
    assert "Defined models:" in captured.out
    assert "model1: repo1 (file1.gguf)" in captured.out
    assert "model2: repo2 (file2.gguf)" in captured.out
    assert mocks["mock_load_model_config"].call_count == 2
"""

def test_model_list_command_no_models_dir(mock_model_commands, capsys):
    """Test listing models when models directory does not exist."""
    mocks = mock_model_commands
    mocks["mock_path_exists"].return_value = False
    args = MagicMock()

    model_list_command(args)

    captured = capsys.readouterr()
    assert "No models defined" in captured.out
    mocks["mock_load_model_config"].assert_not_called()

def test_model_remove_command_success(mock_model_commands, capsys):
    """Test removing a model successfully."""
    mocks = mock_model_commands
    model_name = "test_model"
    args = MagicMock(model_name=model_name, delete_gguf=False)

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    mocks["mock_path_unlink"].assert_called_once() # For the model yaml file
    mocks["mock_load_global_config"].assert_not_called()
    captured = capsys.readouterr()
    assert f"Model '{model_name}' definition removed." in captured.out
    assert "GGUF file" not in captured.out

def test_model_remove_command_delete_gguf(mock_model_commands, capsys):
    """Test removing a model and deleting the GGUF file."""
    mocks = mock_model_commands
    model_name = "test_model"
    mocks["mock_load_model_config"].return_value = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {}}
    args = MagicMock(model_name=model_name, delete_gguf=True)

    model_remove_command(args)

    mocks["mock_load_model_config"].assert_called_once_with(model_name)
    assert mocks["mock_path_unlink"].call_count == 2 # For the model yaml and the gguf file
    mocks["mock_load_global_config"].assert_called_once()
    captured = capsys.readouterr()
    assert f"Model '{model_name}' definition removed." in captured.out
    assert f"GGUF file 'test.gguf' removed." in captured.out

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
