"""Server command implementations."""
import sys
import yaml
import platform
import subprocess

from ...core import config
from ...services import llama_swap

LLAMA_SWAP_FILE_NAME = "llama-swappo"

def serve_command(args) -> None:
    """Run the llama-swap server with current configuration."""
    global_config = config.load_global_config()
    llama_server_path = global_config.get("llama_server_path")

    if not llama_server_path:
        raise ValueError("llama_server_path is not set. Run 'llamate set' to configure")

    # Find llama-swap in the bin directory
    bin_dir = config.constants.LLAMATE_HOME / "bin"
    swap_name = f"{LLAMA_SWAP_FILE_NAME}.exe" if platform.system() == 'Windows' else LLAMA_SWAP_FILE_NAME
    swap_path = bin_dir / swap_name

    if not swap_path.exists():
        raise ValueError("llama-swap not found. Run 'llamate init' to install")

    # Ensure the config file is up-to-date
    llama_swap.save_llama_swap_config()
    print(f"Generated llama-swap config at {config.constants.LLAMATE_CONFIG_FILE}")

    # Build the command
    cmd_list = [str(swap_path), "--config", str(config.constants.LLAMATE_CONFIG_FILE)]
    
    # Add the listen port from global config
    listen_port = global_config.get("llama_swap_listen_port", config.constants.LLAMA_SWAP_DEFAULT_PORT)
    host_port = None # TODO
    if host_port is None:
        listen_port = ":" + str(listen_port)
    else:
        listen_port = f"{host_port}:{listen_port}"
    cmd_list.extend(["--listen", listen_port])

    # Add any additional arguments after 'serve'
    cmd_list.extend(sys.argv[2:])
    print("Running command:", " ".join(cmd_list))

    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed with error: {e}")

def print_config_command(args) -> None:
    """Print the current llama-swap configuration."""
    models = {}
    if config.constants.MODELS_DIR.exists():
        for path in config.constants.MODELS_DIR.glob("*.yaml"):
            try:
                models[path.stem] = config.load_model_config(path.stem)
            except (ValueError, KeyError):
                continue
    
    swap_config = llama_swap.generate_config(models)
    if swap_config:
        yaml.dump(swap_config, sys.stdout, indent=2)
    else:
        print("No configuration found")