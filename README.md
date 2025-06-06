# llamate 🌟

Simple Ollama-like tool for managing and running GGUF format language models.

llamate streamlines language model management with automated workflows and GPU optimization. It's designed for users who need easy and efficient model handling.

The tool use and downloads the follwing binaries, stored in `~/.config/llamate/bin/`:
  - [R-Dson/llama-server-compile](https://github.com/R-Dson/llama-server-compile). This repo is used to compile `llama-server`
  - [R-Dson/llama-swap](https://github.com/R-Dson/llama-swap). This repo is used to compile `llama-swap` with Ollama endpoints

## Platform
The tool only supports Nvidia och Linux currently by default. You can replace the `llama-server` with your own to support your hardware. 

## Key Features ✨
  - Add models from Huggingface or use pre-configured aliases or popular models (llama3:8b, qwen3:7b, etc.)
  - Track model configurations and versions
  - Download and store GGUF files
  - Auto-detect and configure GPU settings (Still testing)
  - Set default inference parameters per model
  - Run models using llama-swap server
  - Downloads `llama-swap` and `llama-server` automatically


## Quick Start 🚀

<details>

<summary> ### Requirements (Optional if the default llama-server binary does not work) </summary>

1. **Download `llama.cpp`**
   Get the latest version from:
   https://github.com/ggerganov/llama.cpp

2. **Build `llama-server`**
   Follow the build instructions for your platform to create the `llama-server` binary

</details>

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash
```

### Setup
```bash
# Initialize `llama-swap` and `llama-server`
llamate init

# Add a model using pre-configured alias
llamate add llama3:8b --alias my-llama
# Or add a specific model
# llamate add bartowski/Qwen_Qwen3-0.6B-GGUF:Qwen_Qwen3-0.6B-Q8_0.gguf --alias my-model


# Download the GGUF file
llamate pull my-llama

# Serve the model
llamate serve
```

## Basic Usage
### Managing Models
```bash
# List configured models
llamate list

# Configure model parameters
llamate set my-model max-tokens=2048 temperature=0.7 n-gpu-layers=24

# Remove a model
llamate remove old-model
```

### Running the Server
```bash
# Start server with default settings
llamate serve

# Custom port (defaults to 11434)
llamate serve --port 9090
```

> **Note**: The server will serve models based on your configuration. Use `llamate config --set-default` to specify which model to serve by default.

## TODO
Add the `ollamate run <model name>` command.
Add the `ollamate update` command.

## Configuration Overview ⚙️
llamate uses YAML configuration files:
- **Global config**: `~/.config/llamate/llamate.yaml`
- **Model configs**: `~/.config/llamate/models/*.yaml`
- **Model GGUF files**: `~/.config/llamate/ggufs/*.yaml`

Example model configuration:
```yaml
hf_repo: bartowski/Qwen_Qwen3-0.6B-GGUF
hf_file: Qwen_Qwen3-0.6B-Q8_0.gguf
args:
  max_tokens: 2048
  temperature: 0.8
```

## Project Structure 🏗️
```
llamate/
├── cli/          # Command-line interface
├── core/         # Core functionality
├── data/         # Data resources
├── services/     # Integration services
├── utils/        # Utility functions
├── __init__.py   # Package initialization
├── __main__.py   # Main entry point
└── constants.py  # Global constants
```

