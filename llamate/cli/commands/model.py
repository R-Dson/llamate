"""Model management command implementations."""
import sys
from pathlib import Path

from ...core import config, download, model
from ...services.aliases import get_model_aliases


def model_add_command(args) -> None:
    """Add a new model.

    Args:
        args: Command line arguments containing hf_spec, alias, set args, and auto_gpu flag
    """
    if not config.constants.LLAMATE_HOME.exists():
        print("llamate is not initialized. Run 'llamate init' first.")
        raise SystemExit(1)

    # Check for pre-configured model with alias validation
    try:
        model_data = model.parse_model_alias(args.hf_spec)
    except model.InvalidInputError as e:
        raise model.InvalidInputError(str(e)) from e

    if not model_data:
        # Parse as HF spec
        try:
            hf_repo, hf_file = model.parse_hf_spec(args.hf_spec)
            model_data = {
                "hf_repo": hf_repo,
                "hf_file": hf_file,
                "args": {}
            }
        except model.InvalidInputError as e:
            raise model.InvalidInputError(str(e)) from e

    # Use alias as model name if provided, otherwise use hf_spec for aliased models
    if args.hf_spec in get_model_aliases():
        model_name = model.validate_model_name(args.alias or args.hf_spec)
    else:
        model_name = model.validate_model_name(args.alias or Path(model_data["hf_file"]).stem)

    # Auto GPU configuration if requested
    if args.auto_gpu:
        model_data = model.configure_gpu(model_data, model_name, auto_detect=True)

    # Update with provided arguments
    if args.set:
        try:
            model_data["args"].update(model.validate_args_list(args.set))
        except model.InvalidInputError as e:
            raise model.InvalidInputError(f"Invalid argument: {e}")

    # Set proxy based on port
    port = model_data["args"].get("port", "9999")
    model_data["proxy"] = f"http://127.0.0.1:{port}"

    config.save_model_config(model_name, model_data)

    # Register custom alias if provided and different from model name
    if args.alias and args.alias != model_name:
        config.register_alias(args.alias, model_name)

    print(f"Model '{model_name}' added successfully.")

    # Download GGUF file unless --no-pull is specified
    if not args.no_pull:
        try:
            global_config = config.load_global_config()
            gguf_dir = global_config["ggufs_storage_path"]
            Path(gguf_dir).mkdir(parents=True, exist_ok=True)
            gguf_path = Path(gguf_dir) / model_data["hf_file"]

            if gguf_path.exists():
                print(f"GGUF already exists at {gguf_path}")
            else:
                url = f"https://huggingface.co/{model_data['hf_repo']}/resolve/main/{model_data['hf_file']}"
                download.download_file(url, gguf_path)
                print(f"Successfully downloaded {model_data['hf_file']} to {gguf_path}")
        except Exception as e:
            print(f"Download failed: {e}", file=sys.stderr)

def model_list_command(args) -> None:
    """List configured models."""
    if not config.constants.MODELS_DIR.exists():
        print("No models defined")
        return

    global_config = config.load_global_config()
    aliases = global_config.get("aliases", {})
    reverse_aliases = {}
    for alias, model in aliases.items():
        reverse_aliases.setdefault(model, []).append(alias)

    print("Defined models:")
    for path in config.constants.MODELS_DIR.glob("*.yaml"):
        model_name = path.stem
        try:
            model_config = config.load_model_config(model_name)
            alias_list = reverse_aliases.get(model_name, [])
            alias_str = ", ".join(alias_list) if alias_list else "(no aliases)"
            print(f"  {model_name} [aliases: {alias_str}]: {model_config['hf_repo']} ({model_config['hf_file']})")
        except (ValueError, KeyError):
            continue

def model_remove_command(args) -> None:
    """Remove a model configuration.

    Args:
        args: Command line arguments containing model_name and delete_gguf flag
    """
    try:
        model_config = config.load_model_config(args.model_name)
        model_file = config.constants.MODELS_DIR / f"{args.model_name}.yaml"
        model_file.unlink(missing_ok=True)
        print(f"Model '{args.model_name}' definition removed.")

        # Remove any aliases pointing to this model
        global_config = config.load_global_config()
        aliases = global_config.get("aliases", {})
        updated_aliases = {a: m for a, m in aliases.items() if m != args.model_name}
        if len(updated_aliases) != len(aliases):
            global_config["aliases"] = updated_aliases
            config.save_global_config(global_config)
            print(f"Removed aliases for model '{args.model_name}'")

        # Update llama-swap config file
        from ...services import llama_swap
        llama_swap.save_llama_swap_config()
        print(f"Updated llama-swap configuration after removing model '{args.model_name}'")

        # Handle GGUF removal
        if args.delete_gguf:
            # Force delete without prompt when flag is provided
            gguf_path = Path(global_config["ggufs_storage_path"]) / model_config["hf_file"]
            gguf_path.unlink(missing_ok=True)
            print(f"GGUF file '{model_config['hf_file']}' removed.")
        else:
            # Prompt user when flag is not provided
            print(f"Do you want to remove the GGUF file '{model_config['hf_file']}'? [y/N]: ", end='', flush=True)
            response = input().strip().lower()
            if response in ('y', 'yes'):
                gguf_path = Path(global_config["ggufs_storage_path"]) / model_config["hf_file"]
                gguf_path.unlink(missing_ok=True)
                print(f"GGUF file '{model_config['hf_file']}' removed.")
    except ValueError as e:
        print(f"Error: {e}")

def model_pull_command(args) -> None:
    """Download GGUF file for a model"""
    if not config.constants.LLAMATE_HOME.exists():
        print("llamate is not initialized. Run 'llamate init' first.")
        raise SystemExit(1)

    model_name_or_spec = args.model_name_or_spec

    # Check input type
    # Check for pre-configured model alias
    if model_name_or_spec in get_model_aliases():
        config_dict = get_model_aliases()[model_name_or_spec].copy()
        model_name = model_name_or_spec
    elif ':' in model_name_or_spec or model_name_or_spec.startswith("https://"):
        # Parse as HF spec
        try:
            hf_repo, hf_file = model.parse_hf_spec(model_name_or_spec)
            model_name = Path(hf_file).stem.replace(' ', '_').replace('.', '_')
            config_dict = {"hf_repo": hf_repo, "hf_file": hf_file}
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Treat as model name
        model_name = model_name_or_spec
        try:
            config_dict = config.load_model_config(model_name)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    global_config = config.load_global_config()
    gguf_dir = global_config["ggufs_storage_path"]
    Path(gguf_dir).mkdir(parents=True, exist_ok=True)
    gguf_path = Path(gguf_dir) / config_dict["hf_file"]

    if gguf_path.exists():
        print(f"GGUF already exists at {gguf_path}")
        return

    try:
        url = f"https://huggingface.co/{config_dict['hf_repo']}/resolve/main/{config_dict['hf_file']}"
        download.download_file(url, gguf_path)
        print(f"Successfully downloaded {config_dict['hf_file']} to {gguf_path}")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
def model_copy_command(args) -> None:
    """Copy a model configuration to a new model.

    Args:
        args: Command line arguments containing source_model and new_model_name.
    """
    if not config.constants.LLAMATE_HOME.exists():
        print("llamate is not initialized. Run 'llamate init' first.")
        raise SystemExit(1)

    try:
        source_name = resolve_model_name(args.source_model)
        new_name = model.validate_model_name(args.new_model_name)

        if source_name == new_name:
            print("Error: Source and new model names must be different.", file=sys.stderr)
            sys.exit(1)

        model_file = config.constants.MODELS_DIR / f"{new_name}.yaml"
        if model_file.exists():
            print(f"Error: Model '{new_name}' already exists.", file=sys.stderr)
            sys.exit(1)

        global_config = config.load_global_config()
        aliases = global_config.get("aliases", {})
        if new_name in aliases:
            print(f"Error: '{new_name}' is already used as an alias for model '{aliases[new_name]}'.", file=sys.stderr)
            sys.exit(1)

        model_config = config.load_model_config(source_name)
        config.save_model_config(new_name, model_config)

        # Update llama-swap config after copying a model
        from ...services import llama_swap
        llama_swap.save_llama_swap_config()

        print(f"Model '{source_name}' copied to '{new_name}'.")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
def resolve_model_name(name: str) -> str:
    """Resolves a model name or alias to the actual model name."""
    # Check if there's a model file for this name
    model_file = config.constants.MODELS_DIR / f"{name}.yaml"
    if model_file.exists():
        return name

    # Check global config aliases
    global_config = config.load_global_config()
    aliases = global_config.get("aliases", {})
    if name in aliases:
        return aliases[name]

    raise ValueError(f"Model '{name}' not found. Please add the model first.")

def model_show_command(args) -> None:
    """Display model information."""
    try:
        model_name = resolve_model_name(args.model_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        model_config = config.load_model_config(model_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Model: {model_name}")
    print(f"Repository: {model_config.get('hf_repo', 'N/A')}")
    print(f"GGUF file: {model_config.get('hf_file', 'N/A')}")

    # Check if GGUF file exists
    global_config = config.load_global_config()
    gguf_dir = global_config.get("ggufs_storage_path", "")
    gguf_path = Path(gguf_dir) / model_config.get("hf_file", "")
    if gguf_path.exists():
        print(f"GGUF Status: Downloaded at {gguf_path}")
    else:
        print("GGUF Status: Not downloaded")

    print("Arguments:")
    model_args = model_config.get('args', {})
    if model_args:
        for key, value in model_args.items():
            print(f"  {key}: {value}")
    else:
        print("  No custom arguments set.")

    print("License: Not available") # Placeholder as per plan

def model_list_aliases_command(args) -> None:
    """List all model aliases."""
    aliases = get_model_aliases()
    if not aliases:
        print("No aliases defined")
        return

    print("Available aliases:")
    for alias in aliases.keys():
        print(f"  • {alias}")
