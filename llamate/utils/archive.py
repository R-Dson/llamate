"""Archive handling utilities."""
import os
from pathlib import Path
import zipfile
import tarfile
import platform

def extract_archive(archive_path: Path, extract_dir: Path) -> None:
    """Extract a zip or tar.gz archive.
    
    Args:
        archive_path: Path to the archive file
        extract_dir: Directory to extract to
        
    Raises:
        ValueError: If archive format is not supported
    """
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    if archive_path.suffix == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif archive_path.name.endswith('.tar.gz'):
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            # Check for zipslip vulnerability
            def is_within_directory(directory: Path, target: Path) -> bool:
                abs_directory = directory.resolve()
                abs_target = target.resolve()
                prefix = os.path.commonpath([abs_directory])
                return prefix == os.path.commonpath([prefix, abs_target])

            def safe_extract(tar, path: Path) -> None:
                for member in tar.getmembers():
                    member_path = path / member.name
                    if not is_within_directory(path, member_path):
                        raise ValueError("Attempted path traversal in archive")
                # Handle Python 3.12+ where filter argument is required
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path, filter='data')
                else:
                    tar.extractall(path)

            safe_extract(tar_ref, extract_dir)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.suffix}")
        
def get_platform_archive_ext() -> str:
    """Get the appropriate archive extension for the current platform.
    
    Returns:
        str: '.zip' for Windows, '.tar.gz' for others
    """
    return '.zip' if platform.system() == 'Windows' else '.tar.gz'