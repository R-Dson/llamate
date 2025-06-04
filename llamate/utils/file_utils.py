"""File utility functions for llamate"""

from pathlib import Path

def write_file(path: Path, content: str) -> None:
    """Write content to a file"""
    path.write_text(content)

def read_file(path: Path) -> str:
    """Read content from a file"""
    return path.read_text()

def ensure_path_exists(path: Path) -> None:
    """Create directory if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)