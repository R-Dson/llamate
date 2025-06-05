"""Platform-specific functionality."""
import platform
import subprocess
from typing import Tuple, Optional

from .. import constants

def get_platform_info() -> Tuple[str, str]:
    """Get platform information and validate against supported architectures.
    
    Returns:
        tuple: (os_name, arch) where both values are guaranteed to be supported
        
    Raises:
        ValueError: If the platform/architecture combination is not supported
    """
    system = platform.system()
    machine = platform.machine().lower()
    
    os_name = constants.SYSTEM_MAP.get(system)
    if not os_name:
        raise ValueError(f"Unsupported platform: {system}")
        
    arch = 'x64' if machine in ('x86_64', 'amd64') else 'arm64' if machine in ('arm64', 'aarch64') else None
    if not arch or os_name not in constants.SUPPORTED_PLATFORMS or arch not in constants.SUPPORTED_PLATFORMS[os_name]:
        raise ValueError(
            f"Platform {os_name}/{arch} is not supported. Supported platforms are:\n" +
            "\n".join(f"- {os}: {', '.join(archs)}" for os, archs in constants.SUPPORTED_PLATFORMS.items())
        )
    
    return os_name, arch

def get_platform_arch() -> str:
    """Get standardized platform architecture.
    
    Returns:
        str: Standardized architecture string ('x64' for x86_64/AMD64, 'arm64' for ARM64/aarch64)
        
    Raises:
        ValueError: If the architecture is not supported
    """
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64'):
        return 'x64'
    elif machine in ('arm64', 'aarch64'):
        return 'arm64'
    raise ValueError(f'Unsupported architecture: {machine}')

def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"

def get_swap_platform() -> str:
    """Get the platform identifier for llama-swap."""
    os_name, arch = get_platform_info()
    return f"{os_name}-{arch}"

def detect_gpu() -> Tuple[bool, Optional[int]]:
    """Detect GPU and suggest number of layers to offload.
    
    Returns:
        tuple: (has_gpu, suggested_layers) where suggested_layers is None if no GPU
    """
    # Try NVIDIA GPU first
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True
        )
        memory_gb = float(result.stdout.strip()) / 1024  # Convert to GB
        suggested_layers = min(32, max(4, int(memory_gb / 0.75)))  # Rough heuristic
        return True, suggested_layers
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    # Try AMD GPU
    try:
        result = subprocess.run(['rocm-smi', '--showmeminfo'], capture_output=True, text=True, check=True)
        if 'GPU_MEMORY' in result.stdout:
            return True, 20  # Conservative default for AMD
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return False, None

def get_llama_server_bin_name() -> str:
    """Get the platform-specific llama-server binary name.
    
    Returns:
        str: 'llama-server.exe' on Windows, 'llama-server' elsewhere
    """
    return "llama-server.exe" if platform.system() == "Windows" else "llama-server"