# llamate 🌟

llamate (llama + mate) is a simple, "Ollama-like" tool for managing and running GGUF language models from your terminal.

`llamate` streamlines your local LLM workflow by automating downloads, configuration, and execution. It's designed for users who want a straightforward way to handle models with GPU acceleration.

## Key Features ✨
- **Easy Model Management:** Add models from Huggingface or use simple aliases (`llama3:8b`). All available can be found [here](https://github.com/R-Dson/llamate-alias/blob/main/README.md).
- **Automated Setup:** Downloads and manages GGUF files and required server binaries for you.
- **GPU Accelerated:** Runs models using a `llama.cpp`-based server, optimized for GPUs.
- **Persistent Configuration:** Set default inference parameters (context size, temp, etc.) for each model.

## Native Installation 🚀
##### `llama-server` is having issues currently with ROCm and will not work by default.

```bash
curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash
```
> You may need to restart your terminal or run `source ~/.bashrc` for the command to be available.

## Running with Docker 🐳

You can run `llamate` in a Docker container.

### Run the Container

Ensure you have Docker and your GPU drivers installed.

#### For NVIDIA GPUs:

```bash
docker run --gpus all -p 11434:11434 -v ~/.config:/app rdson/llamate <command>
```

#### For AMD ROCm GPUs:
##### `llama-server` is having issues currently with ROCm and will not work by default.
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=video -p 11434:11434 -v ~/.config/llamate:/app rdson/llamate <command>
```
> **Note:** The `--gpus all` flag is generally sufficient for NVIDIA GPUs. For AMD ROCm, you might need to specify `--device=/dev/kfd --device=/dev/dri --group-add=video` to ensure proper access to the GPU. The `llamate` tool will automatically detect your GPU and download the appropriate `llama-server` binary.

## Usage ⚡

#### 1. Add and Download a Model
You can use a pre-configured alias or a full Huggingface repository link.  All available aliases can be found on [R-Dson/llamate-alias](https://github.com/R-Dson/llamate-alias/blob/main/README.md).

```bash
# Add and automatically download using an alias
llamate add llama3:8b

# Or, add a specific model from Huggingface with a custom alias
# llamate add <hf_repo>:<hf_file> --alias <your-alias>
llamate add bartowski/Qwen_Qwen3-0.6B-GGUF:Qwen_Qwen3-0.6B-Q8_0.gguf --alias my-model
```

#### 2. Run a Model

**API Server (Ollama-compatible):**
```bash
# Start the server (listens on localhost:11434 by default)
llamate serve
```

#### 3. (Optional) Chat with your LLM
**Interactive Chat:**
```bash
# Basic chat function
llamate run llama3:8b

```

## Available Commands ⚡

- `set`: Set global config or model arguments
- `add`: Add a new model
- `list`: List configured models
- `remove`: Remove a model
- `pull`: Download GGUF file for a model
- `show`: Show model information
- `copy`: Copy a model configuration
- `list-aliases`: List all available model aliases
- `config`: Model configuration commands
- `serve`: Run the llama-swap server
- `update`: Update llamate CLI components
- `run`: Run a model in interactive chat mode
- `print`: Print the llama-swap config
- `init`: Initialize llamate (runs automatically during the installation)

#### Model Management Commands

```bash

# List configured models
llamate list

# Show detailed information about a model
llamate show llama3:8b

# Remove a model and optionally its GGUF file
llamate remove llama3:8b --delete-gguf


# To add without downloading, use --no-pull
llamate add llama3:8b --no-pull

# To disable automatic GPU configuration, use --no-gpu
llamate add llama3:8b --no-gpu

# Set model arguments during creation
llamate add llama3:8b --set "ctx-size=8192" "n-gpu-layers=99"

# To listen on all interfaces (public) use --public
llamate serve --public

# Use a custom port
llamate serve --port 9090

# Connect to a specific host or port
llamate run llama3:8b --host <IP> --port <PORT>

# Download GGUF file for a model
llamate pull my-model

# Copy a model configuration
llamate copy source-model new-model-name
```

#### Configuration Commands

```bash
# List all available model aliases
llamate list-aliases

# Set global config value
llamate set ggufs_storage_path=/new/path

# Set model argument
llamate config set llama3:8b ctx-size 16384

# Get model argument
llamate config get llama3:8b ctx-size

# List all model arguments
llamate config list llama3:8b

# Remove model argument
llamate config remove llama3:8b ctx-size
```

#### Utility Commands

```bash
# Re-initialize llamate
llamate init

# Update llamate components
llamate update

# Print llama-swap config
llamate print
```

## Configuration

`llamate` stores all its files in `~/.config/llamate/`:
- `bin/`: Server binaries (`llama-server`, `llama-swap`).
- `models/`: YAML configuration for each model.
- `ggufs/`: Downloaded GGUF model files.

## TODO
- Add pre-configured optimal parameters for pre-configured alias models.
- Add support for importing model yaml files.

## Platform Support & Troubleshooting

- **Default Support:** The default `llama-server` binary is built for CUDA, Metal, ROCm and Vulkan (Non-CUDA builds are still testing).
- **Requirements:** You must have your GPU drivers (e.g., CUDA) installed.

<details>
<summary><b>Running on other hardware (AMD, Mac, etc.)</b></summary>

If the `llama-server` binary still does not work for you, you can compile your own:

1.  **Download `llama.cpp`**:
    ```bash
    git clone https://github.com/ggerganov/llama.cpp.git
    cd llama.cpp
    ```
2.  **Build `llama-server`**:
    Follow the `llama.cpp` build instructions for your platform (e.g., `make LLAMA_METAL=1` for Mac).

3.  **Replace the Binary**:
    Copy your compiled `server` binary to the `llamate` config directory:
    ```bash
    cp ./llama-server ~/.config/llamate/bin/llama-server
    ```
</details>

# Acknowledgement

This tool is built on the following projects:
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)**: For its incredible, high-performance C++ inference engine.
- **[llama-swap](https://github.com/mostlygeek/llama-swap)**: For its elegant server wrapper that enables on-the-fly model swapping and multi-model configuration.

Thank you to [Ollama](https://github.com/ollama/ollama) For popularizing a simple and powerful local LLM workflow.

---
*This tool uses binaries compiled from [llama-server-compile](https://github.com/R-Dson/llama-server-compile) and [llama-swap](https://github.com/R-Dson/llama-swap).*
