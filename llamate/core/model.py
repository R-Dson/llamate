"""Model management functionality."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re
from .. import constants
from . import config
from . import platform
from ..data.model_aliases import MODEL_ALIASES
from ..utils.exceptions import InvalidInputError, ResourceError

def parse_model_alias(alias: str) -> Optional[Dict[str, Any]]:
    """Parse a model alias or HuggingFace repo path.
    
    Args:
        alias: Model alias (e.g., "llama3:8b") or HF repo path
        
    Returns:
        Optional[Dict[str, Any]]: Model configuration if found, None if not a known alias
        
    Raises:
        InvalidInputError: If alias format is invalid
    """
    if not alias:
        return None

    # Validate alias format
    if not re.match(r"^[\w\-:]+$", alias):
        raise InvalidInputError(f"Invalid alias format: '{alias}'. Only alphanumeric, -, :, and _ allowed")

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
        InvalidInputError: If the spec format is invalid
    """
    if not hf_spec:
        raise InvalidInputError("Repository specification cannot be empty")

    try:
        if hf_spec.startswith("https://huggingface.co/"):
            parts = hf_spec.split('/')
            user_index = parts.index("huggingface.co") + 1
            repo_index = user_index + 1
            
            if "resolve" in parts:
                file_index = parts.index("resolve") + 2
            elif "blob" in parts:
                file_index = parts.index("blob") + 2
            else:
                raise InvalidInputError("Invalid HuggingFace URL format. Must contain 'resolve' or 'blob' path segment")
                
            if user_index >= len(parts) or repo_index >= len(parts) or file_index >= len(parts):
                raise InvalidInputError(f"Invalid URL structure: {hf_spec}")
                
            return f"{parts[user_index]}/{parts[repo_index]}", '/'.join(parts[file_index:])

        if ':' in hf_spec:
            repo, file = hf_spec.split(':', 1)
            if not repo or not file:
                raise InvalidInputError("Both repository and file must be specified in REPO:FILE format")
                
            if not re.match(r"^[\w\-\/\.]+$", repo):
                raise InvalidInputError(f"Invalid repository format: '{repo}'. Only alphanumeric, ., -, /, and _ allowed")
                
            return repo, file
    except Exception as e:
        raise InvalidInputError(f"Failed to parse '{hf_spec}': {str(e)}. Format: REPO_ID:FILE or valid HF URL")

    raise InvalidInputError(f"Unrecognized repository specification format: {hf_spec}. Use REPO_ID:FILE or a valid HuggingFace URL")

def _validate_text(text: str, field_name: str, allow_empty: bool = False) -> str:
    """Internal helper to validate text fields.
    
    Args:
        text: Text to validate
        field_name: Name of the field for error messages
        allow_empty: Whether empty values are allowed
        
    Returns:
        str: The validated text
        
    Raises:
        InvalidInputError: If validation fails
    """
    if not text and not allow_empty:
        raise InvalidInputError(f"{field_name} cannot be empty")
    return text.strip()

def validate_model_name(model_name: str) -> str:
    """Validate and sanitize a model name.
    
    Args:
        model_name: The proposed model name
        
    Returns:
        str: Sanitized model name
        
    Raises:
        InvalidInputError: If the model name is invalid
    """
    model_name = _validate_text(model_name, "Model name")
    if not any(c.isalnum() for c in model_name):
        raise InvalidInputError("Model name must contain at least one alphanumeric character")
    return ''.join(c if c.isalnum() or c in "_-:" else '_' for c in model_name)

def validate_args_list(args_list: List[str]) -> Dict[str, str]:
    """Validate model arguments from command line.
    
    Args:
        args_list: List of KEY=VALUE strings
        
    Returns:
        Dict[str, str]: Validated arguments
        
    Raises:
        InvalidInputError: If any argument is invalid
    """
    if not args_list:
        return {}

    result = {}
    for arg in args_list:
        if '=' not in arg:
            raise InvalidInputError(f"Argument '{arg}' is not in KEY=VALUE format")
        
        key, value = arg.split('=', 1)
        if not key:
            raise InvalidInputError("Argument key cannot be empty")
            
        key = _validate_text(key, "Argument key")
        if not all(c.isalnum() or c in "-_" for c in key):
            raise InvalidInputError(f"Invalid argument key format: {key}. Only alphanumeric, - and _ allowed")
        
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
        
    Raises:
        ResourceError: If GPU detection fails
    """
    if not auto_detect or 'n-gpu-layers' in model_config.get('args', {}):
        return model_config

    try:
        has_gpu, suggested_layers = platform.detect_gpu()
        if has_gpu and suggested_layers:
            model_config.setdefault('args', {})['n-gpu-layers'] = str(suggested_layers)
            print(f"Auto-configured n-gpu-layers={suggested_layers} based on detected GPU")
            print(f"To override: llamate config set {model_name} n-gpu-layers <value>")
    except Exception as e:
        raise ResourceError(f"GPU detection failed: {str(e)}")

    return model_config