"""Command-line interface for llamate."""
import argparse
import sys
from typing import List, Optional

from .. import constants
from ..core import config
from ..core.version import get_version
from .commands import config as config_commands
from .commands import init as init_commands
from .commands import model as model_commands
from .commands import run as run_commands
from .commands import serve as serve_commands
from .commands import update as update_commands
from ..data.model_aliases import MODEL_ALIASES

def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(prog="llamate", description="Simple model management for llama-swap")
    parser.add_argument('-V', '--version', action='version', version=f'llamate {get_version()}')
    subparsers = parser.add_subparsers(dest='command', required=False)

    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize llamate')
    init_parser.add_argument('--arch', help='Override system architecture (amd64, arm64, etc)')
    init_parser.set_defaults(func=init_commands.init_command)

    # Set command
    set_parser = subparsers.add_parser('set', help='Set global config or model arguments',
                                      description="Set global config or model arguments.\n\n" +
                                      "Global keys: " + ", ".join(constants.DEFAULT_CONFIG.keys()))
    set_parser.add_argument('model_name', nargs='?', help='Model name or KEY=VALUE for global config')
    set_parser.add_argument('model_args', nargs='*', help='Additional KEY=VALUE pairs for model config')
    set_parser.set_defaults(func=config_commands.handle_set_command)

    # Model management commands
    alias_list = "\n".join([f"  • {alias}" for alias in MODEL_ALIASES.keys()])
    add_parser = subparsers.add_parser(
        'add',
        help='Add a new model',
        description=f"Add a new model using a Huggingface repo or pre-configured alias.\n\nAvailable aliases:\n{alias_list} \n\n Or use a Huggingface repo directly as 'Qwen/Qwen3-32B-GGUF:Qwen3-32B-Q4_K_M.gguf'.\n\n",
        formatter_class=argparse.RawTextHelpFormatter
    )
    add_parser.add_argument(
        'hf_spec',
        help='Model spec (e.g. "repo_id:file" or model alias)'
    )
    add_parser.add_argument('--alias', help='Custom name for the model')
    add_parser.add_argument('--set', nargs='+', help='Set model arguments (KEY=VALUE)')
    add_parser.add_argument('--no-gpu', action='store_false', dest='auto_gpu',
                          help='Disable automatic GPU configuration')
    add_parser.set_defaults(func=model_commands.model_add_command)

    list_parser = subparsers.add_parser('list', help='List configured models')
    list_parser.set_defaults(func=model_commands.model_list_command)

    remove_parser = subparsers.add_parser('remove', help='Remove a model')
    remove_parser.add_argument('model_name', help='Name of the model to remove')
    remove_parser.add_argument('--delete-gguf', action='store_true',
                             help='Also delete the GGUF file')
    remove_parser.set_defaults(func=model_commands.model_remove_command)

    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Download GGUF file')
    pull_parser.add_argument('model_name_or_spec', help='Model to download (name, repo:file, or URL)')
    pull_parser.set_defaults(func=model_commands.model_pull_command)

    # Show command
    show_parser = subparsers.add_parser('show', help='Show model information')
    show_parser.add_argument('model_name', help='Name of the model to show')
    show_parser.set_defaults(func=model_commands.model_show_command)

    copy_parser = subparsers.add_parser('copy', help='Copy a model configuration')
    copy_parser.add_argument('source_model', help='Name or alias of the source model')
    copy_parser.add_argument('new_model_name', help='New name for the copied model')
    copy_parser.set_defaults(func=model_commands.model_copy_command)

    # Config commands
    config_parser = subparsers.add_parser('config', help='Model configuration commands')
    config_subparsers = config_parser.add_subparsers(dest='config_command')

    config_set = config_subparsers.add_parser('set', help='Set model argument')
    config_set.add_argument('model_name', help='Model name')
    config_set.add_argument('key', help='Argument name')
    config_set.add_argument('value', help='Argument value')
    config_set.set_defaults(func=config_commands.config_set_command)

    config_get = config_subparsers.add_parser('get', help='Get model argument')
    config_get.add_argument('model_name', help='Model name')
    config_get.add_argument('key', help='Argument name')
    config_get.set_defaults(func=config_commands.config_get_command)

    config_list = config_subparsers.add_parser('list', help='List model arguments')
    config_list.add_argument('model_name', help='Model name')
    config_list.set_defaults(func=config_commands.config_list_args_command)

    config_remove = config_subparsers.add_parser('remove', help='Remove model argument')
    config_remove.add_argument('model_name', help='Model name')
    config_remove.add_argument('key', help='Argument name')
    config_remove.set_defaults(func=config_commands.config_remove_arg_command)

    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Run the llama-swap server')
    serve_parser.add_argument('--port', type=int, help='Port to run llama-swap on')
    serve_parser.add_argument('--public', action='store_true',
                              help='Listen on all interfaces (public) instead of localhost')
    serve_parser.set_defaults(func=serve_commands.serve_command)

    # Update command
    update_parser = subparsers.add_parser('update', help='Update llamate CLI, llama-server, and llama-swap')
    update_parser.add_argument('--arch', help='Override system architecture (amd64, arm64, etc)')
    update_parser.set_defaults(func=update_commands.update_command)

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a model in interactive chat mode')
    run_parser.add_argument('model_name', help='Name of the model to run')
    run_parser.add_argument('--host', default='localhost', help='Host for the llama-swap API')
    run_parser.add_argument('--port', type=int, help='Port of the llama-swap server')
    run_parser.set_defaults(func=run_commands.run_command)

    # Print command
    print_parser = subparsers.add_parser('print', help='Print the llama-swap config')
    print_parser.set_defaults(func=config_commands.print_config_command)

    return parser

def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        args: Command line arguments, if None uses sys.argv[1:]
        
    Returns:
        int: Exit code
    """
    if args is None:
        args = sys.argv[1:]

    parser = create_parser()
    parsed_args = parser.parse_args(args)

    try:
        if parsed_args.command == None:
            # Check if llamate needs initialization
            if config.constants.LLAMATE_HOME.exists():
                reinitialize = input("llamate is already initialized. Do you want to re-initialize? (y)es/(N)o: ").lower()
                print("llamate needs to be initialized.")
                if reinitialize == 'y' or reinitialize == 'yes':
                    print("Initializing llamate...")
                    init_commands.init_command(argparse.Namespace(arch=None))
                    return 0
                else:
                    print("Initialization skipped.")
                    parser.print_help()
                    return 1
            
            print("Re-initializing llamate...")
            init_commands.init_command(argparse.Namespace(arch=None))

        if hasattr(parsed_args, 'func'):
            parsed_args.func(parsed_args)
            return 0
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())