"""Tests for configuration management"""
import pytest
from pathlib import Path
import yaml
from unittest.mock import patch

from llamate.core import config
from llamate import constants

# Fixture to mock constants and provide a temporary home directory
@pytest.fixture
def mock_constants(tmp_path):
    with patch('llamate.constants.LLAMATE_HOME', tmp_path / ".config" / "llamate"), \
         patch('llamate.constants.LLAMATE_CONFIG_FILE', tmp_path / ".config" / "llamate" / "llamate.yaml"), \
         patch('llamate.constants.MODELS_DIR', tmp_path / ".config" / "llamate" / "models"), \
         patch('llamate.constants.GGUFS_DIR', tmp_path / ".config" / "llamate" / "ggufs"), \
         patch('llamate.constants.DEFAULT_CONFIG', {
             "llama_server_path": "",
             "ggufs_storage_path": "",
             "llama_swap_listen_port": constants.LLAMA_SWAP_DEFAULT_PORT
         }):
        yield tmp_path

def test_init_paths_default(mock_constants):
    """Test init_paths with default path"""
    # Ensure constants are initially None or different
    constants.LLAMATE_HOME = None
    constants.LLAMATE_CONFIG_FILE = None
    constants.MODELS_DIR = None
    constants.GGUFS_DIR = None

    config.init_paths()

    assert constants.LLAMATE_HOME == Path.home() / ".config" / "llamate"
    assert constants.LLAMATE_CONFIG_FILE == Path.home() / ".config" / "llamate" / "llamate.yaml"
    assert constants.MODELS_DIR == Path.home() / ".config" / "llamate" / "models"
    assert constants.GGUFS_DIR == Path.home() / ".config" / "llamate" / "ggufs"
    assert constants.DEFAULT_CONFIG["ggufs_storage_path"] == str(constants.GGUFS_DIR)

def test_init_paths_custom(mock_constants):
    """Test init_paths with custom base path"""
    custom_path = mock_constants / "custom_llamate"
    config.init_paths(custom_path)

    assert constants.LLAMATE_HOME == custom_path
    assert constants.LLAMATE_CONFIG_FILE == custom_path / "llamate.yaml"
    assert constants.MODELS_DIR == custom_path / "models"
    assert constants.GGUFS_DIR == custom_path / "ggufs"
    assert constants.DEFAULT_CONFIG["ggufs_storage_path"] == str(constants.GGUFS_DIR)

def test_load_global_config_default(mock_constants):
    """Test loading global config when file does not exist"""
    global_config = config.load_global_config()
    assert global_config == constants.DEFAULT_CONFIG

def test_load_global_config_existing(mock_constants):
    """Test loading existing global config"""
    config_path = constants.LLAMATE_CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing_config = {"llama_server_path": "/path/to/server", "new_key": "value"}
    with open(config_path, 'w') as f:
        yaml.dump(existing_config, f)

    global_config = config.load_global_config()
    expected_config = {**constants.DEFAULT_CONFIG, **existing_config}
    assert global_config == expected_config

def test_save_global_config(mock_constants):
    """Test saving global config"""
    config_path = constants.LLAMATE_CONFIG_FILE
    new_config = {"llama_server_path": "/new/server/path", "another_key": 123}
    
    config.save_global_config(new_config)

    assert config_path.exists()
    with open(config_path, 'r') as f:
        loaded_config = yaml.safe_load(f)
    assert loaded_config == new_config

def test_load_model_config_existing(mock_constants):
    """Test loading existing model config"""
    model_name = "test_model"
    model_file = constants.MODELS_DIR / f"{model_name}.yaml"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    existing_config = {"hf_repo": "test/repo", "hf_file": "test.gguf", "args": {"param": "value"}}
    with open(model_file, 'w') as f:
        yaml.dump(existing_config, f)

    model_config = config.load_model_config(model_name)
    assert model_config == existing_config

def test_load_model_config_missing(mock_constants):
    """Test loading model config when file does not exist"""
    model_name = "non_existent_model"
    with pytest.raises(ValueError, match=f"Model '{model_name}' not found"):
        config.load_model_config(model_name)

def test_save_model_config(mock_constants):
    """Test saving model config"""
    model_name = "new_model"
    model_file = constants.MODELS_DIR / f"{model_name}.yaml"
    new_config = {"hf_repo": "new/repo", "hf_file": "new.gguf", "args": {"temp": "0.8"}}

    config.save_model_config(model_name, new_config)

    assert model_file.exists()
    with open(model_file, 'r') as f:
        loaded_config = yaml.safe_load(f)
    assert loaded_config == new_config

def test_load_model_config_backward_compatibility(mock_constants):
    """Test loading model config with old 'default_args' key"""
    model_name = "old_model"
    model_file = constants.MODELS_DIR / f"{model_name}.yaml"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    old_config = {"hf_repo": "old/repo", "hf_file": "old.gguf", "default_args": {"param": "value"}}
    expected_config = {"hf_repo": "old/repo", "hf_file": "old.gguf", "args": {"param": "value"}}
    with open(model_file, 'w') as f:
        yaml.dump(old_config, f)

    model_config = config.load_model_config(model_name)
    assert model_config == expected_config

def test_load_model_config_no_args(mock_constants):
    """Test loading model config with no args key"""
    model_name = "no_args_model"
    model_file = constants.MODELS_DIR / f"{model_name}.yaml"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    no_args_config = {"hf_repo": "no/args/repo", "hf_file": "no_args.gguf"}
    expected_config = {"hf_repo": "no/args/repo", "hf_file": "no_args.gguf", "args": {}}
    with open(model_file, 'w') as f:
        yaml.dump(no_args_config, f)

    model_config = config.load_model_config(model_name)
    assert model_config == expected_config
