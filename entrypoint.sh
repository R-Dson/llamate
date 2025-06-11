#!/bin/sh
chmod 777 ${LLAMATE_HOME}

echo "Detecting GPU and architecture using bash commands:"
echo "--- GPU Detection ---"
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv
elif command -v rocm-smi &> /dev/null; then
    echo "AMD ROCm GPU detected:"
    rocm-smi --showmeminfo
else
    echo "No NVIDIA or AMD ROCm GPU detected using nvidia-smi or rocm-smi."
    echo "Checking for other GPUs with lspci:"
    lspci -k | grep -EA3 'VGA|3D|Display'
fi
echo "--- Architecture Detection ---"
echo "System architecture: $(uname -m)"

#cp /usr/local/bin/llamate ${LLAMATE_HOME}

mkdir -p ${LLAMATE_HOME}/models ${LLAMATE_HOME}/bin
if [ -f "${LLAMATE_HOME}/bin/llama-server" ] && [ -f "${LLAMATE_HOME}/bin/llama-swap" ]; then
    echo "llama-server and llama-swap binaries already exist. Skipping llamate init."
else
    echo "llama-server or llama-swap binaries not found. Running llamate init."
    /usr/local/bin/llamate init
fi

echo "Running /usr/local/bin/llamate with arguments: $@"
exec /usr/local/bin/llamate "$@"