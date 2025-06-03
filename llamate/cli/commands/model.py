"""Model management command implementations."""
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...core import config, model
from ...data.model_aliases import MODEL_ALIASES

def model_add_command(args) -> None:
    """Add a new model.
    
    Args:
        args: Command line arguments containing hf_spec, alias, set args, and auto_gpu flag
    """
    if not config.constants.LLAMATE_HOME.exists():
        print("Llamate is not initialized. Run 'llamate init' first.")
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
    print(f"Model '{model_name}' added successfully.")

def model_list_command(args) -> None:
    """List configured models."""
    if not config.constants.MODELS_DIR.exists():
        print("No models defined")
        return
    
    print("Defined models:")
    for path in config.constants.MODELS_DIR.glob("*.yaml"):
        try:
            model_config = config.load_model_config(path.stem)
            print(f"  {path.stem}: {model_config['hf_repo']} ({model_config['hf_file']})")
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

        if args.delete_gguf:
            global_config = config.load_global_config()
            gguf_path = Path(global_config["ggufs_storage_path"]) / model_config["hf_file"]
            gguf_path.unlink(missing_ok=True)
            print(f"GGUF file '{model_config['hf_file']}' removed.")
    except ValueError as e:
        print(f"Error: {e}")