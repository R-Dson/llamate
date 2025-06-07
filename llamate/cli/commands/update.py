"""Update command implementation."""
import subprocess
import re
import sys # Import sys
import requests # Import requests
from pathlib import Path
import os

from ...core import config, download, version

def _get_latest_llama_server_sha() -> str | None:
    """Get the latest llama-server SHA from GitHub releases."""
    try:
        response = requests.get('https://api.github.com/repos/R-Dson/llama-server-compile/releases/latest')
        response.raise_for_status()
        data = response.json()
        
        # Extract SHA from the release name or tag_name
        sha_match = re.search(r'([0-9a-f]{40})', data.get('name', ''))
        if not sha_match:
            sha_match = re.search(r'([0-9a-f]{40})', data.get('tag_name', ''))
        
        if sha_match:
            return sha_match.group(1)
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch latest llama-server release info: {e}")
    return None

def update_command(args) -> None:
    """Update llamate CLI, llama-server, and llama-swap binaries."""
    print("Updating llamate CLI...")
    try:
        # Update llamate CLI itself by re-running the install script
        subprocess.run(
            "curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash",
            shell=True,
            check=True
        )
        print("llamate CLI updated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error updating llamate CLI: {e}", file=sys.stderr)
        print("Please try running the install script manually: curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash")
        return

    print(f"\nCurrent llamate version: {version.get_version()}")

    global_config = config.load_global_config()
    bin_dir = config.constants.LLAMATE_HOME / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Update llama-server
    print("\nChecking for llama-server updates...")
    installed_sha = global_config.get('llama_server_installed_sha')

    latest_full_sha = _get_latest_llama_server_sha()

    needs_server_update = False
    if not installed_sha:
        print("llama-server not found or version could not be determined. Downloading latest...")
        needs_server_update = True
    elif latest_full_sha and installed_sha != latest_full_sha:
        print(f"Installed llama-server SHA: {installed_sha}")
        print(f"Latest available llama-server SHA: {latest_full_sha}")
        print("New llama-server version available. Downloading...")
        needs_server_update = True
    else:
        print("llama-server is already up to date.")

    if needs_server_update:
        try:
            server_path, new_server_release_sha = download.download_binary(bin_dir, 'https://api.github.com/repos/R-Dson/llama-server-compile/releases/latest', args.arch if hasattr(args, 'arch') else None)
            server_path.chmod(0o755)
            global_config['llama_server_path'] = str(server_path)
            if new_server_release_sha:
                global_config['llama_server_installed_sha'] = new_server_release_sha # Store the new SHA
            config.save_global_config(global_config)
            print(f"llama-server updated to: {server_path} (SHA: {new_server_release_sha})")
        except Exception as e:
            print(f"Error updating llama-server: {e}", file=sys.stderr)

    # Update llama-swap (always download latest as no version check)
    print("\nDownloading latest llama-swap...")
    try:
        llama_swap_path, _ = download.download_binary(bin_dir, 'https://api.github.com/repos/R-Dson/llama-swap/releases/latest', args.arch if hasattr(args, 'arch') else None)
        download.extract_binary(llama_swap_path, bin_dir)
        llama_swap_path.unlink(missing_ok=True)
        extracted_path = bin_dir / "llama-swap"
        if extracted_path.exists():
            extracted_path.chmod(0o755)
        print(f"llama-swap installed at: {extracted_path}")
        print("llama-swap updated successfully.")
    except Exception as e:
        print(f"Error updating llama-swap: {e}", file=sys.stderr)

    print("\nUpdate process complete.")