"""Configuration command implementations."""
from typing import List

from ...core import config
from ...services import llama_swap


def model_set_command(model_name: str, args_list: List[str]) -> None:
    """Set multiple model arguments at once.

    Args:
        model_name: Name of the model to configure
        args_list: List of KEY=VALUE strings
    """
    try:
        model_config = config.load_model_config(model_name)
    except ValueError as e:
        raise ValueError(f"Error: {e}")

    updates = {}
    for arg in args_list:
        if '=' not in arg:
            raise ValueError(f"Argument '{arg}' should be in the form KEY=VALUE")
        key, value = arg.split('=', 1)
        updates[key] = value

    model_config["args"].update(updates)
    config.save_model_config(model_name, model_config)

    # Update llama-swap config file whenever a model is changed
    llama_swap.save_llama_swap_config()

    print(f"Updated {len(updates)} arguments for model '{model_name}'")

def handle_set_command(args) -> None:
    """Handle the set command for both global and model config.

    Args:
        args: Command line arguments which may contain model_name
    """
    if not hasattr(args, 'model_name') and not getattr(args, 'model_args', []):
        # Interactive global config setting
        print("Setting global config...", flush=True)
        current_path = config.load_global_config().get('llama_server_path', 'not set')
        new_path = input(f"Enter new llama_server_path (current: {current_path}): ")
        if new_path:
            set_global_command("llama_server_path", new_path)
        else:
            print("No path entered, global config not changed.", flush=True)
    elif hasattr(args, 'model_name') and getattr(args, 'model_args', []):
        # Model config setting
        model_set_command(args.model_name, args.model_args)
    elif hasattr(args, 'model_name') and '=' in args.model_name:
        # Global config setting with KEY=VALUE
        key, value = args.model_name.split('=', 1)
        global_config = config.load_global_config()
        if key not in config.constants.DEFAULT_CONFIG:
            print(f"Warning: Key '{key}' is not a standard global config key")
        global_config[key] = value
        config.save_global_config(global_config)
        print("Updated 1 global config keys.")
    else:
        raise ValueError("Invalid usage. Use one of:\n" +
                      "  llamate set                     # Set global config interactively\n" +
                      "  llamate set KEY=VALUE          # Set global config key\n" +
                      "  llamate set <model> KEY=VALUE  # Set model config")

def set_global_command(key: str, value: str) -> None:
    """Set a global configuration value.

    Args:
        key: Config key to set
        value: Value to set
    """
    global_config = config.load_global_config()
    if key not in config.constants.DEFAULT_CONFIG:
        print(f"Warning: Key '{key}' is not a standard global config key")
    global_config[key] = value
    config.save_global_config(global_config)
    print("Updated 1 global config keys.")

def config_set_command(args) -> None:
    """Set a model configuration value.

    Args:
        args: Command line arguments containing model_name, key, and value
    """
    try:
        model_config = config.load_model_config(args.model_name)
    except ValueError as e:
        raise ValueError(f"Error: {e}")

    model_config["args"][args.key] = args.value
    config.save_model_config(args.model_name, model_config)

    # Update llama-swap config file whenever a model is changed
    llama_swap.save_llama_swap_config()

    print(f"Argument '{args.key}' set to '{args.value}' for model '{args.model_name}'")

def config_get_command(args) -> None:
    """Get a model configuration value.

    Args:
        args: Command line arguments containing model_name and key
    """
    try:
        model_config = config.load_model_config(args.model_name)
    except ValueError as e:
        raise ValueError(f"Error: {e}")

    if args.key not in model_config["args"]:
        raise ValueError(f"Argument '{args.key}' not found for model '{args.model_name}'")

    print(model_config["args"][args.key])

def config_list_args_command(args) -> None:
    """List all arguments for a model.

    Args:
        args: Command line arguments containing model_name
    """
    try:
        model_config = config.load_model_config(args.model_name)
    except ValueError as e:
        raise ValueError(f"Error: {e}")

    if not model_config["args"]:
        print(f"No arguments set for model '{args.model_name}'")
        return

    print(f"Arguments for model '{args.model_name}':")
    for key, value in model_config["args"].items():
        print(f"  {key}: {value}")

def config_remove_arg_command(args) -> None:
    """Remove an argument from a model's configuration.

    Args:
        args: Command line arguments containing model_name and key
    """
    try:
        model_config = config.load_model_config(args.model_name)
    except ValueError as e:
        raise ValueError(f"Error: {e}")

    if args.key not in model_config["args"]:
        raise ValueError(f"Argument '{args.key}' not found for model '{args.model_name}'")

    del model_config["args"][args.key]
    config.save_model_config(args.model_name, model_config)

    # Update llama-swap config file whenever a model is changed
    llama_swap.save_llama_swap_config()

    print(f"Argument '{args.key}' removed from model '{args.model_name}'")

def print_config_command(args) -> None:
    """Print the current configuration.

    Args:
        args: Command line arguments (unused)
    """
    global_config = config.load_global_config()
    print("Global config:")
    for key, value in global_config.items():
        print(f"  {key}: {value}")
