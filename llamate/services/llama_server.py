"""Llama server management functionality."""
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core import config

def validate_server_path(server_path: str) -> bool:
    """Validate that the server path exists and is executable.
    
    Args:
        server_path: Path to the llama server binary
        
    Returns:
        bool: True if valid, False otherwise
    """
    path = Path(server_path)
    if not path.exists():
        return False
        
    if not path.is_file():
        return False
        
    return True

def build_command(gguf_path: Path, model_config: Dict[str, Any], 
                 passthrough_args: Optional[List[str]] = None) -> List[str]:
    """Build command line arguments for running llama-server.
    
    Args:
        gguf_path: Path to the GGUF model file
        model_config: Model configuration dictionary
        passthrough_args: Additional command line arguments to pass through
        
    Returns:
        list: Command line arguments list
    """
    global_config = config.load_global_config()
    server_path = global_config.get("llama_server_path")
    if not server_path:
        raise ValueError("llama_server_path is not set")

    cmd = [server_path, "-m", str(gguf_path)]

    # Add configured arguments
    args = model_config.get("args", {})
    for key, value in args.items():
        if key == 'proxy':  # Skip proxy, it's for llama-swap
            continue
        if value == "true":
            cmd.append(f"--{key}")
        else:
            cmd.extend([f"--{key}", value])
    
    # Add any passthrough arguments
    if passthrough_args:
        for arg in passthrough_args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                cmd.extend([key, value])
            else:
                cmd.append(arg)

    return cmd

def run_server(cmd: List[str]) -> subprocess.Popen:
    """Run the llama server process.
    
    Args:
        cmd: Command list to execute
        
    Returns:
        subprocess.Popen: The server process
        
    Raises:
        RuntimeError: If the server fails to start
    """
    try:
        # Run server in non-blocking mode with output suppressed
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        return process
    except subprocess.SubprocessError as e:
        raise RuntimeError(f"Failed to start llama server: {e}") from e
