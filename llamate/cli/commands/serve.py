"""Server command implementations."""
import os
import platform
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import yaml

from ...core import config
from ...services import llama_swap

LLAMA_SWAP_FILE_NAME = "llama-swap"

def monitor_config_files(config_file: Path, models_dir: Path, process: subprocess.Popen, stop_event: threading.Event) -> None:
    """Monitor the config file and model files for changes and restart the process when changes are detected.

    Args:
        config_file: Path to the main config file to monitor
        models_dir: Path to the directory containing model config files
        process: The process to restart
        stop_event: Event to signal stopping the monitoring
    """
    # If main config file doesn't exist initially, wait for it to be created
    if not config_file.exists():
        print(f"Config file {config_file} does not exist. Waiting for creation...")

    # Get initial modified time if file exists, otherwise None
    main_config_time = os.path.getmtime(config_file) if config_file.exists() else None

    # Track model config files
    model_files = {}
    if models_dir.exists():
        for model_file in models_dir.glob("*.yaml"):
            model_files[model_file] = os.path.getmtime(model_file)

    while not stop_event.is_set():
        time.sleep(5)  # Check every 5 seconds

        try:
            # Handle main config file changes
            file_exists = config_file.exists()

            # Main config file was created
            if not main_config_time and file_exists:
                print("Config file created. Restarting llama-swap...")
                main_config_time = os.path.getmtime(config_file)
                terminate_process(process)
                return

            # Main config file was deleted
            elif main_config_time and not file_exists:
                print("Config file deleted. Waiting for recreation...")
                main_config_time = None
                continue

            # Main config file exists and existed before - check for modifications
            elif file_exists and main_config_time:
                current_time = os.path.getmtime(config_file)
                if current_time != main_config_time:
                    print("Config file changed. Restarting llama-swap...")
                    main_config_time = current_time
                    terminate_process(process)
                    return

            # Check model config files in the models directory
            if models_dir.exists():
                # Look for new or modified model files
                current_model_files = {}
                for model_file in models_dir.glob("*.yaml"):
                    current_model_files[model_file] = os.path.getmtime(model_file)

                    # Check if this is a new model file or if it was modified
                    if (model_file not in model_files or
                        current_model_files[model_file] != model_files.get(model_file)):
                        print(f"Model file {model_file.name} changed. Restarting llama-swap...")
                        model_files = current_model_files  # Update our tracking dictionary
                        terminate_process(process)
                        return

                # Check for deleted model files
                if len(current_model_files) < len(model_files):
                    deleted_files = set(model_files.keys()) - set(current_model_files.keys())
                    print(f"Model file(s) deleted: {', '.join(str(f.name) for f in deleted_files)}. Restarting llama-swap...")
                    model_files = current_model_files  # Update our tracking dictionary
                    terminate_process(process)
                    return

        except Exception as e:
            print(f"Error monitoring config files: {e}")
            time.sleep(20)  # Wait longer on errors to avoid rapid retries

def terminate_process(process: subprocess.Popen) -> None:
    """Terminate a process gracefully.

    Args:
        process: The process to terminate
    """
    try:
        # Terminate the current process
        if platform.system() == 'Windows':
            process.terminate()
        else:
            os.kill(process.pid, signal.SIGTERM)

        # Wait for process to terminate
        process.wait(timeout=5)
    except Exception as e:
        print(f"Error terminating process: {e}")
        # Try to force kill if termination failed
        try:
            process.kill()
            process.wait(timeout=2)
        except Exception as e:
            print("Failed to kill process. Giving up.")

def serve_command(args) -> None:
    """Run the llama-swap server with current configuration."""
    global_config = config.load_global_config()
    llama_server_path = global_config.get("llama_server_path")

    if not llama_server_path:
        raise ValueError("llama_server_path is not set. Run 'llamate set' to configure")

    # Find llama-swap in the bin directory
    bin_dir = config.constants.LLAMATE_HOME / "bin"
    swap_name = f"{LLAMA_SWAP_FILE_NAME}.exe" if platform.system() == 'Windows' else LLAMA_SWAP_FILE_NAME
    # Ensure bin_dir is initialized to avoid None reference
    if bin_dir is None:
        bin_dir = Path.home() / ".config" / "llamate" / "bin"
    swap_path = bin_dir / swap_name

    if not swap_path.exists():
        raise ValueError("llama-swap not found. Run 'llamate init' to install")

    # Ensure the config file is up-to-date
    llama_swap.save_llama_swap_config()

    # Build the command
    cmd_list = [str(swap_path), "--config", str(config.constants.LLAMA_SWAP_CONFIG_FILE)]

    # Use port from command-line, config, or default
    port = args.port if args.port else global_config.get(
        "llama_swap_listen_port",
        config.constants.LLAMA_SWAP_DEFAULT_PORT
    )

    # Determine listen address based on public flag
    if args.public:
        address = f"0.0.0.0:{port}"
    else:
        address = f"127.0.0.1:{port}"

    cmd_list.extend(["--listen", address])

    # Add any additional arguments after 'serve', excluding --port and --public
    additional_args = []
    i = 0
    args_to_process = sys.argv[2:]
    while i < len(args_to_process):
        if args_to_process[i] == '--port':
            i += 2  # Skip --port and its value
        elif args_to_process[i] == '--public':
            i += 1  # Skip --public (boolean flag, no value)
        else:
            additional_args.append(args_to_process[i])
            i += 1
    cmd_list.extend(additional_args)

    config_file = config.constants.LLAMA_SWAP_CONFIG_FILE
    models_dir = config.constants.MODELS_DIR

    # Always monitor config files for changes
    print("Starting llama-swap...")
    while True:
        try:
            # Ensure the config file exists before starting
            if not config_file.exists():
                print(f"Config file {config_file} does not exist. Creating default configuration...")
                llama_swap.save_llama_swap_config()

            # Try to validate the config file
            try:
                with open(config_file, 'r') as f:
                    yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Config file appears to be invalid: {e}")
                print("Attempting to recreate a valid configuration...")
                llama_swap.save_llama_swap_config()

            # Run the process in the background so we can monitor the config files
            process = subprocess.Popen(cmd_list)

            # Setup monitoring for both main config and model config files
            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=monitor_config_files,
                args=(config_file, models_dir, process, stop_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            # Wait for process to exit
            process.wait()

            # Stop monitoring
            stop_event.set()
            monitor_thread.join(timeout=1)

            # If process exited normally (not due to config change), we should exit too
            if process.returncode != 0 and process.returncode != 143:  # 143 is SIGTERM
                print(f"llama-swap exited with code {process.returncode}")
                break

            # Otherwise, continue the loop to restart
            print("Restarting llama-swap...")
            # Ensure the config file is up-to-date before restart
            try:
                llama_swap.save_llama_swap_config()
            except Exception as e:
                print(f"Warning: Failed to update config file: {e}")

        except KeyboardInterrupt:
            print("\nStopping llama-swap...")
            try:
                if process.poll() is None:
                    terminate_process(process)
            except:
                pass  # Process might already be gone
            break
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            try:
                if process.poll() is None:
                    terminate_process(process)
            except:
                pass  # Process might already be gone
            break


def print_config_command(args) -> None:
    """Print the current llama-swap configuration."""
    models = {}
    models_dir = config.constants.MODELS_DIR
    if models_dir is not None and models_dir.exists():
        for path in models_dir.glob("*.yaml"):
            try:
                models[path.stem] = config.load_model_config(path.stem)
            except (ValueError, KeyError):
                continue

    swap_config = llama_swap.generate_config(models)
    if swap_config:
        yaml.dump(swap_config, sys.stdout, indent=2)
    else:
        print("No configuration found")
