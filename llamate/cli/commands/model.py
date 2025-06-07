"""Model management command implementations."""
from pathlib import Path
import sys

from ...core import config, model
from ...core import download
from ...data.model_aliases import MODEL_ALIASES

def model_add_command(args) -> None:
    """Add a new model.
    
    Args:
        args: Command line arguments containing hf_spec, alias, set args, and auto_gpu flag
    """
    if not config.constants.LLAMATE_HOME.exists():
        print("llamate is not initialized. Run 'llamate init' first.")
        raise SystemExit(1)

    # Check for pre-configured model
    model_data = MODEL_ALIASES.get(args.hf_spec, {}).copy() if args.hf_spec in MODEL_ALIASES else None
    
    if not model_data:
        # Parse as HF spec
        try:
            hf_repo, hf_file = model.parse_hf_spec(args.hf_spec)
            model_data = {
                "hf_repo": hf_repo,
                "hf_file": hf_file,
                "args": {}
            }
        except ValueError as e:
            raise ValueError(str(e)) from None

    # Use alias as model name if provided, otherwise use hf_spec for aliased models
    if args.hf_spec in MODEL_ALIASES:
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
        except ValueError as e:
            raise ValueError(f"Invalid argument: {e}")

    # Set proxy based on port
    port = model_data["args"].get("port", "9999")
    model_data["proxy"] = f"http://127.0.0.1:{port}"

    config.save_model_config(model_name, model_data)
    
    # Register custom alias if provided and different from model name
    if args.alias and args.alias != model_name:
        config.register_alias(args.alias, model_name)
    
    print(f"Model '{model_name}' added successfully.")

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
    if model_name_or_spec in MODEL_ALIASES:
        config_dict = MODEL_ALIASES[model_name_or_spec].copy()
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
        sys.exit(1)