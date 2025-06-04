"""Initialization command implementation."""
from pathlib import Path

from ...core import config
from ...services import llama_swap

def init_command(args) -> None:
    """Initialize llamate.
    
    Args:
        args: Command line arguments containing arch override
    """
    first_run = not config.constants.LLAMATE_HOME.exists()
    if first_run:
        print("Welcome to llamate! 🦙\n")
        print("This appears to be your first run. llamate will:")
        print("1. Configure your llama-server path")
        print("2. Create configuration directory at ~/.config/llamate")
        print("3. Download the llama-swap binary\n")
        print("You'll need:")
        print("- A working llama.cpp server installation")
        print("- The full path to your llama-server binary\n")
        print("For more information on llama-server, visit: https://github.com/ggerganov/llama.cpp\n")

    # Create required directories
    config.constants.LLAMATE_HOME.mkdir(parents=True, exist_ok=True)
    global_config = config.load_global_config()
    config.constants.MODELS_DIR.mkdir(exist_ok=True, parents=True)
    config.constants.GGUFS_DIR.mkdir(exist_ok=True, parents=True)
    
    # Always prompt for llama-server path
    while True:
        current_path = global_config.get('llama_server_path', 'not set')
        print(f"\nCurrent llama-server path: {current_path}")
        new_path = input("Enter the full path to your llama-server binary: ").strip()
        
        if not new_path:
            print("Error: llama-server path cannot be empty.")
            continue
            
        path_obj = Path(new_path)
        
        if not path_obj.exists():
            print(f"Warning: Path '{new_path}' does not exist.")
            confirm = input("Do you want to use this path anyway? (y/N): ").lower()
            if confirm != 'y':
                continue
        
        if path_obj.exists() and not path_obj.is_file():
            print(f"Error: '{new_path}' is not a file.")
            continue
        
        global_config['llama_server_path'] = str(path_obj)
        config.save_global_config(global_config)
        if first_run:
            print("\nInitialization complete!")
        else:
            print(f"\nllama-server path set to: {new_path}")
        break

    bin_dir = config.constants.LLAMATE_HOME / "bin"
    bin_dir.mkdir(exist_ok=True)
    
    try:
        # Download and extract binary
        print("\nDownloading llama-swap binary...")
        archive = llama_swap.download_binary(bin_dir, args.arch)
        
        # Extract to bin_dir
        llama_swap.extract_binary(archive, bin_dir)
        archive.unlink(missing_ok=True)
        
        print("\nllama-swap installed successfully")
        print("\nInitialization complete! You can now:")
        print("1. Add models:    llamate add llama3:8b")
        print("2. Pull models:   llamate pull llama3:8b")
        print("3. List models:   llamate list")
        print("4. Serve models:  llamate serve")
        
    except Exception as e:
        print(f"\nWarning: Failed to download llama-swap: {e}")
        print("You may need to manually set 'llama_server_path' in config if the update failed.")
        raise