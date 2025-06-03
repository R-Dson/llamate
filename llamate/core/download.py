"""Download functionality for Llamate."""
import sys
import urllib.request
import urllib.error
from pathlib import Path


def format_bytes(size: int) -> str:
    """Convert bytes to human-readable format."""
    power = 2**10
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < power:
            return f"{size:.1f} {unit}"
        size /= power
    return f"{size:.1f} TB" # Handle values larger than TB

def download_file(url: str, destination: Path, resume: bool = True) -> None:
    """Download a file with progress tracking and resume capability.
    
    Args:
        url: The URL to download from
        destination: Path where the file should be saved
        resume: Whether to attempt resuming an interrupted download
        
    Raises:
        RuntimeError: If the download fails
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = destination.with_suffix(destination.suffix + ".tmp")
    meta_file = destination.with_suffix(destination.suffix + ".meta")

    downloaded_bytes = 0
    if resume and meta_file.exists():
        try:
            with open(meta_file, 'r') as f:
                downloaded_bytes = int(f.read().strip())
            print(f"Resuming download from {downloaded_bytes} bytes")
        except (ValueError, IOError) as e:
            print(f"Warning: Could not read download progress: {e}")
            downloaded_bytes = 0

    total_downloaded = downloaded_bytes

    try:
        # Create meta file before starting download
        with open(meta_file, 'w') as mf:
            mf.write(str(downloaded_bytes))
            
        headers = {'Range': f'bytes={downloaded_bytes}-'} if resume and downloaded_bytes > 0 else {}
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
            total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
            mode = 'ab' if resume and downloaded_bytes > 0 else 'wb'
            
            with open(tmp_file, mode) as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    total_downloaded += len(chunk)

                    if total_size > 0:
                        progress = total_downloaded / total_size * 100
                        print(f"\rDownloading: {format_bytes(total_downloaded)}/{format_bytes(total_size)} ({progress:.1f}%)", 
                              end='', flush=True)
                    with open(meta_file, 'w') as mf:
                        mf.write(str(total_downloaded))

    except (urllib.error.URLError, IOError) as e:
        error_msg = str(e)
        if isinstance(e, urllib.error.URLError):
            error_msg = error_msg.replace('<urlopen error ', '').rstrip('>')
        print(f"\nDownload failed: {error_msg}", file=sys.stderr)
        if total_downloaded > downloaded_bytes:
            try:
                with open(meta_file, 'w') as f:
                    f.write(str(total_downloaded))
            except IOError:
                pass  # Ignore errors writing meta file
        raise RuntimeError(f"Download failed: {error_msg}")
    finally:
        print()
        try:
            if tmp_file.exists() and total_downloaded > downloaded_bytes:
                tmp_file.rename(destination)
                if meta_file.exists():
                    meta_file.unlink()
        except OSError:
            pass  # Ignore cleanup errors