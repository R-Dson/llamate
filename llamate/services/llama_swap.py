"""Llama swap integration and configuration."""
import yaml
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Any
import tarfile
import zipfile

from ..core import config, download, platform

def download_binary(dest_dir: Path, arch_override: str = None) -> Path:
    """Download the llama-swap binary.
    
    Args:
        dest_dir: Directory to download to
        arch_override: Optional architecture override
        
    Returns:
        Path: Path to the downloaded archive
        
    Raises:
        RuntimeError: If download fails or platform is not supported
    """
    os_name, auto_arch = platform.get_platform_info()
    arch = arch_override or auto_arch
    ext = '.zip' if os_name == 'windows' else '.tar.gz'

    try:
        # Fetch latest release info
        url = 'https://api.github.com/repos/R-Dson/llama-swappo/releases/latest'
        with urllib.request.urlopen(url) as r:
            data = json.load(r)
            assets = data['assets']
            asset = next((a for a in assets if
                        f'{os_name}_{arch}{ext}' in a['name']), None)
            if not asset:
                raise RuntimeError(f"No asset found for {os_name}/{arch}")

            # Download asset
            url = asset['browser_download_url']
            dest_file = dest_dir / asset['name']
            download.download_file(url, dest_file)
            return dest_file
            
    except Exception as e:
        raise RuntimeError(f"Failed to get release info: {e}")

def extract_binary(archive: Path, dest_dir: Path) -> None:
    """Extract the llama-swap binary from archive.
    
    Args:
        archive: Path to the downloaded archive
        dest_dir: Directory to extract to
    """
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive, 'r') as z:
            z.extractall(dest_dir)
    else:
        with tarfile.open(archive, 'r:gz') as t:
            t.extractall(dest_dir)
    
    # Handle folder structure
    extracted_dir = dest_dir / "bin"
    if extracted_dir.exists() and extracted_dir.is_dir():
        for item in extracted_dir.iterdir():
            destination = dest_dir / item.name
            if item.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(item), str(dest_dir))
            else:
                shutil.move(str(item), str(dest_dir))
        extracted_dir.rmdir()

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
    if swap_config:
        with open(config.constants.LLAMATE_CONFIG_FILE, 'w') as f:
            yaml.dump(swap_config, f, indent=2)

def load_config() -> Dict[str, Any]:
    """Load the llama-swap compatible config file."""
    config_file = config.constants.LLAMATE_CONFIG_FILE
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
    llama_path = global_config.get('llama_server_path', 'llama-server')
    for model_name, model_config in model_configs.items():
        gguf_path = Path(global_config['ggufs_storage_path']) / model_config['hf_file']
        
        # Build command parts
        cmd_parts = [
            llama_path,
            f"--model {gguf_path}"
        ]

        # Add configured arguments
        args = model_config.get('args', {})
        for key, value in args.items():
            if key == 'proxy':
                models.setdefault(model_name, {})
                models[model_name]['proxy'] = value
                continue
            
            cmd_parts.append(f"--{key}" if value == "true" else f"--{key} {value}")

        cmd_text = '\n'.join(cmd_parts) + '\n'
        # Initialize model entry if not already done by proxy handling
        model_entry = models.setdefault(model_name, {})
        model_entry['cmd'] = cmd_text

        # Add non-standard fields
        model_entry.update({
            k: v for k, v in model_config.items() 
            if k not in ['hf_repo', 'hf_file', 'args']
        })

    if models:
        result['models'] = models

    if 'groups' in global_config:
        result['groups'] = global_config['groups']

    return result