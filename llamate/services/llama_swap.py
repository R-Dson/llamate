"""Llama swap integration and configuration."""
import yaml
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Any
import tarfile
import zipfile
import certifi
import ssl

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
    os_name, auto_arch = platform.get_platform_info() # Use the helper or your original
    arch = arch_override or auto_arch

    if os_name == 'linux' and arch == 'x64': # Match your original logic
        arch = 'amd64'
    # Add other mappings if needed, e.g., arm64 might be 'aarch64' in some release names
    elif os_name == 'darwin' and arch == 'arm64': # Example for macOS ARM
        pass # or arch = 'arm64' if it's consistent

    ext = '.zip' if os_name == 'windows' else '.tar.gz'

    try:
        # Fetch latest release info
        api_url = 'https://api.github.com/repos/R-Dson/llama-swappo/releases/latest'

        # Create an SSL context using certifi's CA bundle
        context = ssl.create_default_context(cafile=certifi.where()) # <--- THE FIX

        # Make the request with the custom SSL context
        req = urllib.request.Request(api_url, headers={'Accept': 'application/vnd.github.v3+json'})
        with urllib.request.urlopen(req, context=context) as r: # <--- PASS CONTEXT
            if r.status != 200:
                raise RuntimeError(f"GitHub API request failed with status {r.status}: {r.read().decode()}")
            data = json.load(r)

        assets = data.get('assets', [])
        # Construct the expected asset name fragment carefully
        asset_name_fragment = f'{os_name}_{arch}{ext}'
        # More robust check, allow for full names or common variations like 'llama-swap-v1.0.0-linux-amd64.tar.gz'
        found_asset = None
        for a in assets:
            if asset_name_fragment in a.get('name', ''):
                found_asset = a
                break
        
        if not found_asset:
            available_assets = [a.get('name') for a in assets if a.get('name')]
            raise RuntimeError(f"No asset found for {os_name}/{arch} (looking for '{asset_name_fragment}'). Available: {available_assets}")

        # Download asset
        download_url = found_asset['browser_download_url']
        dest_file = dest_dir / found_asset['name']
        print(f"Downloading asset: {found_asset['name']} from {download_url}") # Debug print
        download.download_file(download_url, dest_file) # This already uses requests with certifi
        return dest_file

    except urllib.error.URLError as e: # Catch URLError specifically for network issues
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(f"Failed to get release info (SSL verification failed): {e.reason}. Ensure certifi is bundled correctly.") from e
        raise RuntimeError(f"Failed to get release info (Network error): {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse release info from GitHub API: {e}") from e
    except Exception as e:
        # Log the original exception type for better debugging
        raise RuntimeError(f"Failed to download or process llama-swap binary ({type(e).__name__}): {e}") from e

    
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
        config.constants.LLAMA_SWAP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
        with open(config.constants.LLAMA_SWAP_CONFIG_FILE, 'w') as f:
            yaml.dump(swap_config, f, indent=2)

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