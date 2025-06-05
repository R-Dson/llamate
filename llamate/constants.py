"""Global constants and default configurations for llamate."""
from pathlib import Path

# Global paths will be initialized by core.config
LLAMATE_HOME = None
LLAMATE_CONFIG_FILE = None
MODELS_DIR = None
GGUFS_DIR = None
LLAMA_SWAP_CONFIG_FILE = None # Added for consistency, though it's set in config.py
LLAMA_SWAP_DEFAULT_PORT = 11434

# Default configuration
DEFAULT_CONFIG = {
    "llama_server_path": "",
    "ggufs_storage_path": "",  # Set during initialization
    "llama_swap_listen_port": LLAMA_SWAP_DEFAULT_PORT
}

DEFAULT_MODEL_CONFIG = {
    "hf_repo": "",
    "hf_file": "",
    "args": {}
}

# Platform support information
SUPPORTED_PLATFORMS = {
    'macos': ['x64', 'arm64'],
    'linux': ['x64', 'arm64'],
    'windows': ['x64'],
    'freebsd': ['x64']
}

# System name mappings
SYSTEM_MAP = {
    'Darwin': 'macos',
    'Windows': 'windows',
    'Linux': 'linux',
    'FreeBSD': 'freebsd'
}

ARCH_MAP = {
    'x86_64': 'x64',
    'AMD64': 'x64',
    'aarch64': 'arm64',
    'arm64': 'arm64'
}