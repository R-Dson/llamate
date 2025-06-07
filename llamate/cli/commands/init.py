"""Initialization command implementation."""
from pathlib import Path

from ...core import config, download
from ...services import llama_swap, llama_server

def init_command(args) -> None:
    """Initialize llamate.
    
    Args:
        args: Command line arguments containing arch override
    """
    first_run = not config.constants.LLAMATE_HOME.exists()
    if first_run:
        print("Welcome to llamate! 🦙\n")
        print("This appears to be your first run. llamate will:")
        print("1. Create configuration directory at ~/.config/llamate")
        print("2. Download llama-server and llama-swap binaries\n")
        print("For more information on llama-server, visit: https://github.com/ggerganov/llama.cpp\n")

    # Create required directories
    config.constants.LLAMATE_HOME.mkdir(parents=True, exist_ok=True)
    global_config = config.load_global_config()
    config.constants.MODELS_DIR.mkdir(exist_ok=True, parents=True)
    config.constants.GGUFS_DIR.mkdir(exist_ok=True, parents=True)
    
    bin_dir = config.constants.LLAMATE_HOME / "bin"
    bin_dir.mkdir(exist_ok=True)
    
    try:
        # Download and install llama-server
        print("\nDownloading llama-server...")
        server_path, server_release_sha = download.download_binary(bin_dir, 'https://api.github.com/repos/R-Dson/llama-server-compile/releases/latest', args.arch)
        server_path.chmod(0o755)  # Make executable
        global_config['llama_server_path'] = str(server_path)
        if server_release_sha:
            global_config['llama_server_installed_sha'] = server_release_sha # Store the SHA
        config.save_global_config(global_config)
        print(f"llama-server installed at: {server_path} (SHA: {server_release_sha})")
        
        # Download and install llama-swap
        print("\nDownloading llama-swap...")
        llama_swap_path, _ = download.download_binary(bin_dir, 'https://api.github.com/repos/R-Dson/llama-swap/releases/latest', args.arch)
        download.extract_binary(llama_swap_path, bin_dir)
        llama_swap_path.unlink(missing_ok=True)
        extracted_path = bin_dir / "llama-swap"
        if extracted_path.exists():
            extracted_path.chmod(0o755)  # Make executable
        print(f"llama-swap installed at: {extracted_path}")
        print("llama-swap installed successfully")

        print("\nInitialization complete! You can now:")
        print("1. Add models:    llamate add llama3:8b")
        print("2. Pull models:   llamate pull llama3:8b")
        print("3. List models:   llamate list")
        print("4. Serve models:  llamate serve")
        
    except Exception as e:
        print(f"\nWarning: Initialization failed: {e}")
        if first_run:
            print("You may need to manually set 'llama_server_path' in config if the download failed.")
        raise