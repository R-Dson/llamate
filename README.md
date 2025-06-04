# llamate 🌟

Simple command-line tool for managing and running GGUF format language models.
*Version: 0.1.0*

llamate streamlines language model management with automated workflows and GPU optimization. It's designed for users who need easy and efficient model handling.

## Key Features ✨
- **Model management**:
  - Add models from Hugging Face Hub or use pre-configured aliases
  - Track model configurations and versions
  - Download and store GGUF files
  - Auto-detect and configure GPU settings

- **Configuration**:
  - Set default inference parameters per model
  - Configure storage locations
  - Manage runtime arguments
  - Pre-configured aliases for popular models (llama2:7b, mistral:7b, etc.)

- **Execution**:
  - Run models using llama-swap server
  - Pass custom arguments at runtime
  - Automatic GPU layer optimization
  - Resume interrupted downloads


## Quick Start 🚀

### Requirements
1. **Download `llama.cpp`**
   Get the latest version from:
   https://github.com/ggerganov/llama.cpp

2. **Build `llama-server`**
   Follow the build instructions for your platform to create the `llama-server` binary

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash
```

### Setup
```bash
# Initialize environment
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

# Set default model
llamate config --set-default my-model

# Configure model parameters
llamate config my-model --max-tokens 2048 --temperature 0.7

# Remove a model
llamate remove old-model
```

### Running the Server
```bash
# Start server with default settings
llamate serve

# Custom port and GPU layers
llamate serve --port 9090 --n-gpu-layers 24
```

> **Note**: The server will serve models based on your configuration. Use `llamate config --set-default` to specify which model to serve by default.

## Configuration Overview ⚙️
llamate uses YAML configuration files:
- **Global config**: `~/.config/llamate/config.yaml`
- **Model configs**: `~/.config/llamate/models/*.yaml`
- **Model GGUF files**: `~/.config/llamate/GGUFs/*.yaml`

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

