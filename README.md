# llamate 🌟

llamate (llama + mate) is a simple, "Ollama-like" tool for managing and running GGUF language models from your terminal.

`llamate` streamlines your local LLM workflow by automating downloads, configuration, and execution. It's designed for users who want a straightforward way to handle models with GPU acceleration.

## Key Features ✨
- **Easy Model Management:** Add models from Huggingface or use simple aliases (`llama3:8b`).
- **Automated Setup:** Downloads and manages GGUF files and required server binaries for you.
- **GPU Accelerated:** Runs models using a `llama.cpp`-based server, optimized for GPUs.
- **Persistent Configuration:** Set default inference parameters (context size, temp, etc.) for each model.

## Installation 🚀

```bash
curl -fsSL https://raw.githubusercontent.com/R-Dson/llamate/main/install.sh | bash
```
> You may need to restart your terminal or run `source ~/.bashrc` for the command to be available.

## Usage ⚡

#### 1. Initialize `llamate`
This downloads the necessary server binaries. 
```bash
llamate init
```

#### 2. Add and Download a Model
You can use a pre-configured alias or a full Huggingface repository link.

```bash
# Add and download using an alias
llamate add llama3:8b
llamate pull llama3:8b

# Or, add a specific model from Huggingface with a custom alias
# llamate add <hf_repo>:<hf_file> --alias <your-alias>
llamate add bartowski/Qwen_Qwen3-0.6B-GGUF:Qwen_Qwen3-0.6B-Q8_0.gguf --alias my-model
llamate pull my-model
```

#### 3. Run a Model

**API Server (Ollama-compatible):**
```bash
# Start the server with a model
llamate serve

# Use a custom port (default: 11434)
llamate serve --port 9090
```

**Interactive Chat:**
```bash
llamate run llama3:8b
```

#### Other Commands

```bash
# List all configured models
llamate list

# Set custom parameters for a model (context size, temp, etc., https://github.com/ggml-org/llama.cpp/tree/master/tools/server for more settings)
llamate set llama3:8b ctx-size=8192 n-gpu-layers=99
# or
# llamate set my-model ctx-size=32768 temp=0.6 top-p=0.95 min-p=0.05 top-k=40 n-gpu-layers=99

# Remove a model and its GGUF file
llamate remove llama3:8b
```

## Platform Support & Troubleshooting

- **Default Support:** Linux with an NVIDIA GPU.
- **Requirements:** You must have your GPU drivers (e.g., CUDA) installed.

<details>
<summary><b>Running on other hardware (AMD, Mac, etc.)</b></summary>

The default `llama-server` binary is built for Linux/NVIDIA. If it doesn't work for you, you can compile your own:

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
- Add `llamate run --host <IP>` to set the host ip.
- Add `llamate serve --public` option to set localhost or public connections only.
- Add pre-configured optimal parameters for pre-configured alias models.
- Implement `llamate show <model>` to display model information (parameters, license, etc.).
- Implement `llamate copy <source> <destination>` to duplicate model configurations/aliases.

# Acknowledgement

This tool is built on the following projects:
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)**: For its incredible, high-performance C++ inference engine.
- **[llama-swap](https://github.com/mostlygeek/llama-swap)**: For its elegant server wrapper that enables on-the-fly model swapping and multi-model configuration.

Thank you to [Ollama](https://github.com/ollama/ollama) For popularizing a simple and powerful local LLM workflow.

---
*This tool uses binaries compiled from [llama-server-compile](https://github.com/R-Dson/llama-server-compile) and [llama-swap](https://github.com/R-Dson/llama-swap).*
