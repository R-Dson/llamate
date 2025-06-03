"""Model management functionality."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
from .. import constants
from . import config
from . import platform
from ..data.model_aliases import MODEL_ALIASES

def parse_model_alias(alias: str) -> Optional[Dict[str, Any]]:
    """Parse a model alias or HuggingFace repo path.
    
    Args:
        alias: Model alias (e.g., "llama3:8b") or HF repo path
        
    Returns:
        Optional[Dict[str, Any]]: Model configuration if found, None if not a known alias
    """
    if not alias:
        return None

    # Check direct alias first
    if alias in MODEL_ALIASES:
        return MODEL_ALIASES[alias].copy()

    # Check if the input matches any alias's repo path
    for alias_name, config in MODEL_ALIASES.items():
        if alias == config["hf_repo"]:
            print(f"Using pre-configured alias {alias_name} for {alias}")
            return config.copy()
    return None

def parse_hf_spec(hf_spec: str) -> Tuple[str, str]:
    """Parse repository specification.
    
    Args:
        hf_spec: Repository specification in format "repo_id:file" or HF URL
        
    Returns:
        Tuple[str, str]: (repo_id, file_path)
        
    Raises:
        ValueError: If the spec format is invalid
    """
    if not hf_spec:
        raise ValueError(f"Invalid repo spec: {hf_spec}. Use REPO_ID:FILE or HF_URL")

    if hf_spec.startswith("https://huggingface.co/"):
        parts = hf_spec.split('/')
        try:
            user_index = parts.index("huggingface.co") + 1
            repo_index = user_index + 1
            file_index = parts.index("resolve") + 2
            if user_index >= len(parts) or repo_index >= len(parts) or file_index >= len(parts):
                raise ValueError(f"Invalid repo spec: {hf_spec}. Use REPO_ID:FILE or HF_URL")
            return f"{parts[user_index]}/{parts[repo_index]}", '/'.join(parts[file_index:])
        except (ValueError, IndexError):
            raise ValueError(f"Invalid repo spec: {hf_spec}. Use REPO_ID:FILE or HF_URL")

    if ':' in hf_spec:
        repo, file = hf_spec.split(':', 1)
        if not repo or not file or not all(c.isalnum() or c in "-_/" for c in repo):
            raise ValueError(f"Invalid repo spec: {hf_spec}. Use REPO_ID:FILE or HF_URL")
        return repo, file
    
    raise ValueError(f"Invalid repo spec: {hf_spec}. Use REPO_ID:FILE or HF_URL")

def _validate_text(text: str, field_name: str, allow_empty: bool = False) -> str:
    """Internal helper to validate text fields.
    
    Args:
        text: Text to validate
        field_name: Name of the field for error messages
        allow_empty: Whether empty values are allowed
        
    Returns:
        str: The validated text
        
    Raises:
        ValueError: If validation fails
    """
    if not text and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")
    return text.strip()

def validate_model_name(model_name: str) -> str:
    """Validate and sanitize a model name.
    
    Args:
        model_name: The proposed model name
        
    Returns:
        str: Sanitized model name
        
    Raises:
        ValueError: If the model name is invalid
    """
    model_name = _validate_text(model_name, "Model name")
    if not any(c.isalnum() for c in model_name):
        raise ValueError("Model name must contain at least one alphanumeric character")
    return ''.join(c if c.isalnum() or c in "_-" else '' for c in model_name)

def validate_args_list(args_list: List[str]) -> Dict[str, str]:
    """Validate model arguments from command line.
    
    Args:
        args_list: List of KEY=VALUE strings
        
    Returns:
        Dict[str, str]: Validated arguments
        
    Raises:
        ValueError: If any argument is invalid
    """
    if not args_list:
        return {}

    result = {}
    for arg in args_list:
        if '=' not in arg:
            raise ValueError(f"Argument '{arg}' is not in KEY=VALUE format")
        
        key, value = arg.split('=', 1)
        if not key:
            raise ValueError("Argument key cannot be empty")
            
        key = _validate_text(key, "Argument key")
        if not all(c.isalnum() or c in "-_" for c in key):
            raise ValueError(f"Invalid argument key format: {key}")
        
        value = _validate_text(value, "Argument value", allow_empty=True)
        result[key] = value
    return result

def configure_gpu(model_config: Dict[str, Any], model_name: str, auto_detect: bool = True) -> Dict[str, Any]:
    """Configure GPU settings for a model.
    
    Args:
        model_config: The model configuration to update
        model_name: Name of the model (for messages)
        auto_detect: Whether to attempt GPU detection
        
    Returns:
        Dict[str, Any]: Updated model configuration with GPU settings
    """
    if not auto_detect or 'n-gpu-layers' in model_config.get('args', {}):
        return model_config

    has_gpu, suggested_layers = platform.detect_gpu()
    if has_gpu and suggested_layers:
        model_config.setdefault('args', {})['n-gpu-layers'] = str(suggested_layers)
        print(f"Auto-configured n-gpu-layers={suggested_layers} based on detected GPU")
        print(f"To override: llamate config set {model_name} n-gpu-layers <value>")

    return model_config