"""Pre-configured model aliases."""

MODEL_ALIASES = {
    "gemma3:4b": {
        "hf_repo": "unsloth/gemma-3-4b-it-GGUF",
        "hf_file": "gemma-3-4b-it-UD-Q4_K_XL.gguf",
        "args": {
            "ctx-size": "8192"
        }
    },
    "gemma3:27b": {
        "hf_repo": "unsloth/gemma-3-27b-it-GGUF",
        "hf_file": "gemma-3-27b-it-UD-Q4_K_XL.gguf",
        "args": {
            "ctx-size": "8192"
        }
    },
    "qwen3:32b": {
        "hf_repo": "unsloth/Qwen3-32B-GGUF",
        "hf_file": "Qwen3-32B-UD-Q4_K_XL.gguf",
        "args": {
            "ctx-size": "8192"
        }
    },
    "phi4:reasoning-plus": {
        "hf_repo": "unsloth/Phi-4-reasoning-plus-GGUF",
        "hf_file": "Phi-4-reasoning-plus-UD-Q4_K_XL.gguf",
        "args": {
            "ctx-size": "8192",
            "jinja": ""
        }
    },
    "llama3:8b": {
        "hf_repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "hf_file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "args": {
            "ctx-size": "8192"
        }
    },
    "r1-distill:8b": {
        "hf_repo": "unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF",
        "hf_file": "DeepSeek-R1-0528-Qwen3-8B-UD-Q4_K_XL.gguf",
        "args": {
            "ctx-size": "8192"
        }
    }
}