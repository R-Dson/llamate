"""Configuration management for llamate."""
from pathlib import Path
import yaml
import json
from typing import Dict, Any, Optional, NoReturn
from yaml.representer import SafeRepresenter

from .. import constants

# Custom string representer for literal blocks
class literal_str(str): pass

def literal_presenter(dumper, data):
    """Present multi-line strings as literal blocks in YAML."""
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

yaml.add_representer(literal_str, literal_presenter)

def init_paths(base_path: Optional[Path] = None) -> None:
    """Initialize global paths for llamate.
    
    Args:
        base_path: Optional custom base path. If None, uses ~/.config/llamate
        
    Raises:
        ValueError: If base_path is not writable
    """
    if base_path is not None and not (base_path.exists() or base_path.parent.exists()):
        raise ValueError(f"Base path {base_path} does not exist and cannot be created")
    
    constants.LLAMATE_HOME = base_path or Path.home() / ".config" / "llamate"
    constants.LLAMATE_CONFIG_FILE = constants.LLAMATE_HOME / "config.yaml"
    constants.MODELS_DIR = constants.LLAMATE_HOME / "models"
    constants.GGUFS_DIR = constants.LLAMATE_HOME / "ggufs"
    constants.DEFAULT_CONFIG["ggufs_storage_path"] = str(constants.GGUFS_DIR)

def _ensure_config_dir() -> None:
    """Ensure configuration directory exists.
    
    Raises:
        RuntimeError: If directory cannot be created
    """
    try:
        constants.LLAMATE_HOME.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise RuntimeError(f"Failed to create config directory {constants.LLAMATE_HOME}: {e}")

def load_global_config() -> Dict[str, Any]:
    """Load global configuration from YAML file."""
    if not constants.LLAMATE_CONFIG_FILE.exists():
        return constants.DEFAULT_CONFIG.copy()
        
    try:
        with open(constants.LLAMATE_CONFIG_FILE, 'r') as f:
            user_config = yaml.safe_load(f) or {}
            return user_config  # Return user config directly without merging with defaults
    except yaml.YAMLError as e:
        raise RuntimeError(f"Failed to load config file {constants.LLAMATE_CONFIG_FILE}: {e}")

def save_global_config(config: Dict[str, Any]) -> None:
    """Save global configuration to YAML file.
    
    Args:
        config: Configuration dictionary to save
        
    Raises:
        RuntimeError: If config cannot be saved
    """
    _ensure_config_dir()
    try:
        with open(constants.LLAMATE_CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)
    except (yaml.YAMLError, OSError) as e:
        raise RuntimeError(f"Failed to save config file {constants.LLAMATE_CONFIG_FILE}: {e}")

def load_model_config(model_name: str) -> Dict[str, Any]:
    """Load configuration for a specific model.
    
    Args:
        model_name: Name of the model to load
        
    Returns:
        Dict[str, Any]: Model configuration with defaults
        
    Raises:
        ValueError: If model doesn't exist
        RuntimeError: If config file exists but cannot be read
    """
    model_file = constants.MODELS_DIR / f"{model_name}.yaml"
    if not model_file.exists():
        raise ValueError(f"Model '{model_name}' not found")
    
    try:
        with open(model_file, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # Handle backward compatibility
        if "default_args" in config:
            config["args"] = config.pop("default_args")
        config.setdefault("args", {})
        return config
    except (yaml.YAMLError, OSError) as e:
        raise RuntimeError(f"Failed to read model config {model_file}: {e}")

def save_model_config(model_name: str, config: Dict[str, Any]) -> None:
    """Save configuration for a specific model.
    
    Args:
        model_name: Name of the model
        config: Model configuration to save
        
    Raises:
        RuntimeError: If config cannot be saved
    """
    try:
        constants.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_file = constants.MODELS_DIR / f"{model_name}.yaml"
        with open(model_file, 'w') as f:
            yaml.dump(config, f)
    except (yaml.YAMLError, OSError) as e:
        raise RuntimeError(f"Failed to save model config {model_file}: {e}")