"""Llama swap integration and configuration."""
import yaml
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, Any

from ..core import config


def save_llama_swap_config() -> None:
    """Save the llama-swap compatible config file."""
    models = {}
    if config.constants.MODELS_DIR.exists():
        for path in config.constants.MODELS_DIR.glob("*.yaml"):
            try:
                models[path.stem] = config.load_model_config(path.stem)
            except (ValueError, KeyError):
                continue
    
    # Generate and save config
    swap_config = generate_config(models)
    config.constants.LLAMA_SWAP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
    with open(config.constants.LLAMA_SWAP_CONFIG_FILE, 'w') as f:
        yaml.dump(swap_config, f, indent=2, width=1000000) # Use a large width to avoid line breaks

def load_config() -> Dict[str, Any]:
    """Load the llama-swap compatible config file."""
    config_file = config.constants.LLAMA_SWAP_CONFIG_FILE
    if not config_file.exists():
        return {}
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error loading llama-swap config file {config_file}: {e}")
        return {}

def generate_config(model_configs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate llama-swap compatible config structure.
    
    Args:
        model_configs: Dictionary of model configurations
        
    Returns:
        dict: Generated llama-swap config
    """
    result = {}
    models = {}
    global_config = config.load_global_config()

    # Add relevant global settings
    for key in ['healthCheckTimeout', 'logLevel', 'startPort', 'macros']:
        if key in global_config:
            result[key] = global_config[key]

    # Generate models config
    from ..core import platform
    default_llama_path = str(config.constants.LLAMATE_HOME / "bin" / platform.get_llama_server_bin_name())
    llama_path = global_config.get('llama_server_path', default_llama_path)
    for model_name, model_config in model_configs.items():
        model_entry = models.setdefault(model_name, {})   # moved here

        gguf_path = Path(global_config['ggufs_storage_path']) / model_config['hf_file']
        
        # Build command parts
        cmd_parts = [
            llama_path,
            f"--model {gguf_path}"
        ]

        # Add configured arguments
        args = model_config.get('args', {})
        for key, value in args.items():
            if key == "proxy":
                continue
            cmd_parts.append(f"--{key}" if value == "true" else f"--{key} {value}")

        # Add port from proxy if available
        if model_config.get('proxy'):
            try:
                proxy = model_config['proxy']
                print(proxy)
                parsed = urlparse(proxy)
                if parsed.port:
                    cmd_parts.append(f"--port {parsed.port}")
            except Exception as e:
                print(f"Error parsing proxy URL for model {model_name}: {e}")

        cmd_text = ' '.join(cmd_parts)
        print(cmd_text)
        model_entry['cmd'] = cmd_text
# If proxy is in the args, set it in the model_entry
        if 'proxy' in args:
            model_entry['proxy'] = args['proxy']
        # Add non-standard fields
        model_entry.update({
            k: v for k, v in model_config.items() 
            if k not in ['hf_repo', 'hf_file', 'args']
        })

    if models:
        result['models'] = models

    if 'groups' in global_config:
        result['groups'] = global_config['groups']
    else:
        result['groups'] = {} # Ensure groups key is always present, even if empty

    return result