"""Download functionality for llamate."""
import certifi
import sys
import requests # Use requests for better HTTP handling
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
        
        # Use requests for downloading
        response = requests.get(
            url,
            headers=headers,
            stream=True,
            verify=certifi.where(),
            timeout=30
        )
        response.raise_for_status() # Raise an exception for bad status codes

        total_size = int(response.headers.get('content-length', 0))
        if total_size == 0 and 'content-range' in response.headers:
             # Handle case where server returns Content-Range for resumed download
            content_range = response.headers['content-range']
            import re
            match = re.match(r'bytes \d+-(\d+)/(\d+)', content_range)
            if match:
                total_size = int(match.group(2)) - downloaded_bytes

        total_size += downloaded_bytes # Add previously downloaded bytes to total size

        mode = 'ab' if resume and downloaded_bytes > 0 else 'wb'
        
        with open(tmp_file, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
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

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"\nDownload failed: {error_msg}", file=sys.stderr)
        if total_downloaded > downloaded_bytes:
            try:
                with open(meta_file, 'w') as f:
                    f.write(str(total_downloaded))
            except IOError:
                pass  # Ignore errors writing meta file
        raise RuntimeError(f"Download failed: {error_msg}")
    except IOError as e:
         error_msg = str(e)
         print(f"\nDownload failed: {error_msg}", file=sys.stderr)
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