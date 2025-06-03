"""GPU detection and configuration utilities."""
import subprocess
from typing import Tuple, Optional

def get_nvidia_memory() -> Optional[float]:
    """Get total NVIDIA GPU memory in GB.
    
    Returns:
        float or None: Total GPU memory in GB, or None if not available
    """
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip()) / 1024  # Convert to GB
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        return None

def get_amd_memory() -> Optional[float]:
    """Get total AMD GPU memory in GB.
    
    Returns:
        float or None: Total GPU memory in GB, or None if not available
    """
    try:
        result = subprocess.run(['rocm-smi', '--showmeminfo'], 
                              capture_output=True, text=True, check=True)
        if 'GPU_MEMORY' in result.stdout:
            # AMD ROCm doesn't provide an easy way to get total memory
            # Return a conservative estimate
            return 8.0  # Assume 8GB minimum for a GPU
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return None

def calculate_gpu_layers(memory_gb: float) -> int:
    """Calculate suggested number of GPU layers based on memory.
    
    Args:
        memory_gb: Available GPU memory in GB
        
    Returns:
        int: Suggested number of layers to offload to GPU
    """
    # Rough heuristic: ~0.75GB per layer
    suggested = int(memory_gb / 0.75)
    return min(32, max(4, suggested))  # Keep between 4 and 32 layers