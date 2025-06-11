# llamate 🌟

llamate (llama + mate) is a simple, "Ollama-like" tool for managing and running GGUF language models from your terminal.

`llamate` streamlines your local LLM workflow by automating downloads, configuration, and execution. It's designed for users who want a straightforward way to handle models with GPU acceleration.

## Key Features ✨
- **Easy Model Management:** Add models from Huggingface or use simple aliases (`llama3:8b`).
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
You can use a pre-configured alias or a full Huggingface repository link.

```bash
# Add and automatically download using an alias
llamate add llama3:8b

# To add without downloading, use --no-pull
llamate add llama3:8b --no-pull

# Or, add a specific model from Huggingface with a custom alias
# llamate add <hf_repo>:<hf_file> --alias <your-alias>
llamate add bartowski/Qwen_Qwen3-0.6B-GGUF:Qwen_Qwen3-0.6B-Q8_0.gguf --alias my-model

```

#### 2. Run a Model

**API Server (Ollama-compatible):**
```bash
# Start the server
llamate serve
```

#### 3. (Optional) Chat with your LLM
**Interactive Chat:**
```bash
# Basic chat function.
llamate run llama3:8b

# Connect to a specific host (default: localhost) or a specific port (default: 11434)
llamate run llama3:8b --host <IP> --port <PORT>
```

#### Other Commands

```bash
# Run initiation again
llamate init

# List all configured models
llamate list

# Set custom parameters for a model (context size, temp, etc., https://github.com/ggml-org/llama.cpp/tree/master/tools/server for more settings)
llamate set llama3:8b ctx-size=8192 n-gpu-layers=99
# or
# llamate set my-model ctx-size=32768 temp=0.6 top-p=0.95 min-p=0.05 top-k=40 n-gpu-layers=99

# Remove a model and its GGUF file
llamate remove llama3:8b

# For existing aliases, you can still download manually with
llamate pull my-model

# Use a custom port (default: 11434)
llamate serve --port 9090
```

## Platform Support & Troubleshooting

- **Default Support:** The default `llama-server` binary is built for CUDA, Metal, ROCm and Vulkan (Non-CUDA builds are still testing).
- **Requirements:** You must have your GPU drivers (e.g., CUDA) installed.

<details>
<summary><b>Running on other hardware (AMD, Mac, etc.)</b></summary>

If tne `llama-server` binary still doesn't work for you, you can compile your own:

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
    cp ./server ~/.config/llamate/bin/llama-server
    ```
</details>

## Configuration

`llamate` stores all its files in `~/.config/llamate/`:
- `bin/`: Server binaries (`llama-server`, `llama-swap`).
- `models/`: YAML configuration for each model.
- `ggufs/`: Downloaded GGUF model files.

## TODO
- Add pre-configured optimal parameters for pre-configured alias models.
- Add support for importing model yaml files.

# Acknowledgement

This tool is built on the following projects:
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)**: For its incredible, high-performance C++ inference engine.
- **[llama-swap](https://github.com/mostlygeek/llama-swap)**: For its elegant server wrapper that enables on-the-fly model swapping and multi-model configuration.

Thank you to [Ollama](https://github.com/ollama/ollama) For popularizing a simple and powerful local LLM workflow.

---
*This tool uses binaries compiled from [llama-server-compile](https://github.com/R-Dson/llama-server-compile) and [llama-swap](https://github.com/R-Dson/llama-swap).*
