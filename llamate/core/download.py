from typing import Optional
"""Download functionality for llamate."""
import json
import os # Added for os.chmod
import shutil
import ssl
import tarfile
import zipfile
import certifi
import sys
import requests
import re
from pathlib import Path
from urllib.parse import urlparse
from ..core import platform
import urllib
from ..utils.exceptions import InvalidURLError, DownloadError

def format_bytes(size: int) -> str:
    """Convert bytes to human-readable format."""
    power = 2**10
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < power:
            return f"{size:.1f} {unit}"
        size /= power
    return f"{size:.1f} TB" # Handle values larger than TB

def validate_url(url: str) -> None:
    """Validate a URL for download.
    
    Args:
        url: URL to validate
        
    Raises:
        InvalidURLError: If URL is invalid
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL structure")
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("Unsupported URL scheme")
        if re.search(r'[^\w\-\.]', parsed.netloc):
            raise ValueError("Invalid characters in domain")
    except Exception as e:
        raise InvalidURLError(f"Invalid URL '{url}': {e}")

def download_file(
    url: str,
    destination: Path,
    resume: bool = True,
    timeout: int = 30,
    max_size: Optional[int] = None
) -> None:
    """Download a file with progress tracking and resume capability.
    
    Args:
        url: The URL to download from
        destination: Path where the file should be saved
        resume: Whether to attempt resuming an interrupted download
        timeout: Request timeout in seconds
        max_size: Maximum allowed download size in bytes (None for no limit)
        
    Raises:
        InvalidURLError: If URL is invalid
        DownloadError: If download fails
    """
    # Validate URL before proceeding
    validate_url(url)
    
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = destination.with_suffix(destination.suffix + ".tmp")
    meta_file = destination.with_suffix(destination.suffix + ".meta")
    
    # Clean up any existing partial files if not resuming
    if not resume and tmp_file.exists():
        tmp_file.unlink()
    if not resume and meta_file.exists():
        meta_file.unlink()

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
            timeout=timeout
        )
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        if total_size == 0 and 'content-range' in response.headers:
            content_range = response.headers['content-range']
            match = re.match(r'bytes \d+-(\d+)/(\d+)', content_range)
            if match:
                total_size = int(match.group(2)) - downloaded_bytes

        total_size += downloaded_bytes
        
        # Check size limits
        if max_size and total_size > max_size:
            raise DownloadError(f"File size {total_size} exceeds limit {max_size}")

        mode = 'ab' if resume and downloaded_bytes > 0 else 'wb'
        
        mode = 'ab' if resume and downloaded_bytes > 0 else 'wb'
        
        with open(tmp_file, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    break
                f.write(chunk)
                total_downloaded += len(chunk)
                
                # Check size during download
                if max_size and total_downloaded > max_size:
                    raise DownloadError(f"File size exceeds limit {max_size}")
                    
                if total_size > 0:
                    progress = total_downloaded / total_size * 100
                    print(f"\rDownloading: {format_bytes(total_downloaded)}/{format_bytes(total_size)} ({progress:.1f}%)",
                          end='', flush=True)
                with open(meta_file, 'w') as mf:
                    mf.write(str(total_downloaded))

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"\nDownload failed: {error_msg}", file=sys.stderr)
        # Clean up partial files on any error
        if tmp_file.exists():
            tmp_file.unlink()
        if meta_file.exists():
            meta_file.unlink()
        raise DownloadError(f"Download failed: {error_msg}")
    except IOError as e:
        error_msg = str(e)
        print(f"\nDownload failed: {error_msg}", file=sys.stderr)
        if tmp_file.exists():
            tmp_file.unlink()
        if meta_file.exists():
            meta_file.unlink()
        raise DownloadError(f"Download failed: {error_msg}")
    finally:
        print()
        try:
            if tmp_file.exists() and total_downloaded > downloaded_bytes:
                tmp_file.rename(destination)
                if meta_file.exists():
                    meta_file.unlink()
        except OSError:
            pass  # Ignore cleanup errors

from typing import Tuple # Import Tuple

from typing import Tuple, Optional # Import Optional



def download_binary(
    dest_dir: Path,
    api_url: str,
    timeout: int = 60,
    max_size: int = 500 * 1024 * 1024  # 500MB
) -> Tuple[Path, Optional[str]]:
    """Download the llama-swap binary.
    Args:
        dest_dir: Directory to download to
        api_url: GitHub API URL for the release
        timeout: Request timeout in seconds
        max_size: Maximum allowed download size in bytes
        
    Returns:
        Tuple[Path, Optional[str]]: Path to downloaded archive and release SHA
    Raises:
        DownloadError: If download fails
    """
    # Determine the optimal architecture for llama-server or use generic for llama-swap
    if 'llama-server-compile' in api_url:
        asset_name_fragment = f"llama-server-{platform.get_optimal_llama_server_architecture()}"
    else:
        asset_name_fragment = 'llama-swap' # Default for llama-swap

    try:
        # Create an SSL context using certifi's CA bundle
        context = ssl.create_default_context(cafile=certifi.where())

        # Make the request with the custom SSL context
        req = urllib.request.Request(api_url, headers={'Accept': 'application/vnd.github.v3+json'})
        with urllib.request.urlopen(req, context=context) as r:
            if r.status != 200:
                raise RuntimeError(f"GitHub API request failed with status {r.status}: {r.read().decode()}")
            data = json.load(r)

        assets = data.get('assets', [])
        found_asset = None
        for a in assets:
            name = a.get('name', '')
            # For llama-server, we expect the full architecture string in the name
            if 'llama-server-compile' in api_url:
                # Accept the asset if it is exactly the fragment (without extension) or if it contains the fragment and an extension
                if name == asset_name_fragment or (asset_name_fragment in name and ('.tar.gz' in name or '.zip' in name or '.exe' in name)):
                    found_asset = a
                    break
            
            # Fallback for llama-server: if specific arch not found, try generic 'llama-server'
            if not found_asset and 'llama-server-compile' in api_url:
                for a in assets:
                    name = a.get('name', '')
                    if name == 'llama-server' or name == 'llama-server.exe':
                        found_asset = a
                        break
            # For llama-swap, we need to select based on OS and architecture
            elif asset_name_fragment == 'llama-swap':
                os_name, arch = platform.get_platform_info()
                # Map arch to the format in the asset names
                arch_map = {'x64': 'amd64', 'arm64': 'arm64'}
                mapped_arch = arch_map.get(arch, arch)
                
                # Construct regex pattern for llama-swap assets based on OS and architecture
                # Example: llama-swap_124-custom_linux_amd64.tar.gz or llama-swap_124-custom_windows_amd64.zip
                if os_name == 'windows':
                    pattern = re.compile(rf'llama-swap.*_{os_name}_{mapped_arch}\.zip$', re.IGNORECASE)
                else:
                    pattern = re.compile(rf'llama-swap.*_{os_name}_{mapped_arch}\.tar\.gz$', re.IGNORECASE)
                
                if pattern.match(name):
                    found_asset = a
                    break
        
        if not found_asset:
            available_assets = [a.get('name') for a in assets if a.get('name')]
            error_msg = f"No asset found for '{asset_name_fragment}'. Available: {available_assets}"
            raise RuntimeError(error_msg)

        # Download asset
        download_url = found_asset['browser_download_url']
        dest_file = dest_dir / found_asset['name']
        try:
            download_file(
                download_url,
                dest_file,
                timeout=timeout,
                max_size=max_size
            )
        except Exception as e:
            # Clean up partial download on error
            if dest_file.exists():
                dest_file.unlink()
            raise
        
        # Extract SHA from the release name or tag_name
        release_sha = None
        sha_match = re.search(r'([0-9a-f]{40})', data.get('name', ''))
        if not sha_match:
            sha_match = re.search(r'([0-9a-f]{40})', data.get('tag_name', ''))
        if sha_match:
            release_sha = sha_match.group(1)
        else:
            print(f"Warning: No 40-char SHA found in release name or tag_name for {api_url}")
        
        return dest_file, release_sha

    except urllib.error.URLError as e: # Catch URLError specifically for network issues
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(f"Failed to get release info (SSL verification failed): {e.reason}. Ensure certifi is bundled correctly.") from e
        raise RuntimeError(f"Failed to get release info (Network error): {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse release info from GitHub API: {e}") from e
    except Exception as e:
        # Log the original exception type for better debugging
        raise RuntimeError(f"Failed to download or process llama-swap binary ({type(e).__name__}): {e}") from e

def extract_binary(archive: Path, dest_dir: Path) -> None:
    """Extract the llama-swap binary from archive.
    
    Args:
        archive: Path to the downloaded archive
        dest_dir: Directory to extract to
    """
    llama_server_bin_name = platform.get_llama_server_bin_name()
    final_binary_path = dest_dir / llama_server_bin_name

    # If the archive is already in the destination directory and is not a known archive type,
    # assume it's a direct binary that was downloaded directly to its final location.
    # We need to rename it to the expected binary name and make it executable.
    if archive.parent == dest_dir and \
       not (archive.suffix == '.zip' or archive.suffix == '.gz' or archive.suffix == '.tgz'):
        if archive != final_binary_path: # Only rename if current name is different
            print(f"DEBUG: extract_binary - Renaming direct binary: {archive} to {final_binary_path}")
            archive.rename(final_binary_path)
        if sys.platform != "win32":
            os.chmod(final_binary_path, os.stat(final_binary_path).st_mode | 0o111) # Add execute permissions
        print(f"DEBUG: extract_binary - Early return: Direct binary already in destination, renamed, and made executable: {final_binary_path}")
        return

    # Check if the file is a known archive type
    if archive.suffix == '.zip': # Handles .zip files
        with zipfile.ZipFile(archive, 'r') as z:
            z.extractall(dest_dir)
    elif archive.suffix == '.gz' or archive.suffix == '.tgz': # Handles .tar.gz and .tgz files
        with tarfile.open(archive, 'r:gz') as t:
            t.extractall(dest_dir)
    else: # Assume it's a direct binary if not a known archive type
        # Ensure destination directory exists
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove existing file/directory if it exists at the target path
        if final_binary_path.exists():
            if final_binary_path.is_dir():
                shutil.rmtree(final_binary_path)
            else:
                final_binary_path.unlink()
        
        # Move and rename the binary to the destination directory with the correct name
        shutil.move(str(archive), str(final_binary_path))
        
        # Make the binary executable on Unix-like systems
        if sys.platform != "win32":
            os.chmod(final_binary_path, os.stat(final_binary_path).st_mode | 0o111) # Add execute permissions
        return # Exit after moving the binary, no further extraction needed
    
    # Handle folder structure: if the archive extracted into a 'bin' folder, move its contents to the destination
    extracted_dir = dest_dir / "bin"
    if extracted_dir.exists() and extracted_dir.is_dir():
        for item in extracted_dir.iterdir():
            destination = dest_dir / item.name
            # Remove existing file/directory if it exists
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            shutil.move(str(item), str(dest_dir))
        extracted_dir.rmdir()
