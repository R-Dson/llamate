"""Platform-specific functionality."""
from pathlib import Path
import platform
import subprocess
from typing import Tuple, Optional

from ..core import config
from .. import constants

def get_platform_info() -> Tuple[str, str]:
    """Get platform information and validate against supported architectures.
    
    Returns:
        tuple: (os_name, arch) where both values are guaranteed to be supported
        
    Raises:
        ValueError: If the platform/architecture combination is not supported
    """
    # Check for architecture override in global config
    try:
        global_config = config.load_global_config()
        if 'arch_override' in global_config:
            override = global_config['arch_override']
            # Map to consistent arch names
            if override in ['amd64', 'x64']:
                arch = 'x64'
            elif override in ['arm64', 'aarch64']:
                arch = 'arm64'
            else:
                arch = override
            
            system = platform.system()
            os_name = constants.SYSTEM_MAP.get(system)
            if not os_name:
                raise ValueError(f"Unsupported platform: {system}")
            
            # Validate the override against supported platforms
            if os_name in constants.SUPPORTED_PLATFORMS and arch in constants.SUPPORTED_PLATFORMS[os_name]:
                return os_name, arch
            else:
                raise ValueError(
                    f"Overridden platform {os_name}/{arch} is not supported. Supported platforms are:\n" +
                    "\n".join(f"- {os}: {', '.join(archs)}" for os, archs in constants.SUPPORTED_PLATFORMS.items())
                )
    except Exception as e:
        # If there's any issue with the override, fall back to normal detection
        pass
    
    # Normal detection
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

def get_optimal_llama_server_architecture() -> str:
    """Determine the optimal llama-server binary architecture string.

    Returns:
        str: The architecture string (e.g., 'cuda-linux-x86_64', 'metal-macos-arm64')

    Raises:
        ValueError: If the platform/architecture combination is not supported for llama-server.
    """
    os_name, arch = get_platform_info()

    if os_name == 'darwin':
        if arch == 'arm64':
            return 'metal-macos-arm64'
        else:
            raise ValueError("Unsupported macOS architecture for llama-server: only arm64 is supported for Metal backend.")
    elif os_name == 'linux':
        if arch == 'x64': # All provided Linux binaries are x86_64
            # Check for NVIDIA GPU
            try:
                subprocess.run(['nvidia-smi'], capture_output=True, check=True)
                return 'cuda-linux-x86_64'
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass # No NVIDIA GPU or nvidia-smi not found

            # Check for AMD ROCm GPU
            try:
                # Check for ROCm-specific files/commands
                if Path('/dev/kfd').exists() and Path('/dev/dri/renderD128').exists():
                    subprocess.run(['rocm-smi'], capture_output=True, check=True) # Verify rocm-smi exists
                    return 'rocm-linux-x86_64'
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass # No AMD GPU or rocm-smi not found

            # Fallback to Vulkan if no specific GPU backend detected
            return 'vulkan-linux-x86_64'
        else:
            raise ValueError(f"Unsupported Linux architecture for llama-server: {arch}. Only x86_64 is supported.")
    elif os_name == 'windows':
        raise ValueError("Windows is not currently supported for llama-server downloads. Please use Linux or macOS.")
    else:
        raise ValueError(f"Unsupported OS for llama-server: {os_name}")

def get_llama_server_bin_name() -> str:
    """Get the platform-specific llama-server binary name.
    
    Returns:
        str: 'llama-server.exe' on Windows, 'llama-server' elsewhere
    """
    # The actual binary name will be derived from the architecture string,
    # but for consistency, we'll return a base name.
    # The download and execution logic will use the full architecture string.
    return "llama-server.exe" if is_windows() else "llama-server"

def get_llama_swap_bin_name() -> str:
    """Get the platform-specific llama-swap binary name.
    
    Returns:
        str: 'llama-swap.exe' on Windows, 'llama-swap' elsewhere
    """
    return "llama-swap.exe" if is_windows() else "llama-swap"