"""llamate - Simple model management for llama-swap."""
from .cli.cli import main
from .core.config import init_paths

# Initialize global paths
init_paths()

__version__ = "0.1.0"
__all__ = ['main']