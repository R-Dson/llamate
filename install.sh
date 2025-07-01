#!/bin/bash

# --- Configuration ---
REPO="R-Dson/llamate"
TARGET_INSTALL_NAME="llamate" # The name of the command after installation
USER_INSTALL_DIR="$HOME/.local/bin" # Standard user-specific bin directory
SYSTEM_INSTALL_DIR="/usr/local/bin"  # Standard system-wide location

# --- Helper Functions ---
log() { echo "$@" >&2; }
err() { log "Error: $@"; exit 1; }

check_prerequisites() {
    command -v curl >/dev/null || err "curl is not installed. Please install it."
    command -v jq >/dev/null || err "jq is not installed. Please install it."
    command -v uname >/dev/null || err "uname is not installed. This script needs it to determine OS/Arch."
    command -v ps >/dev/null || err "ps command not found. This is highly unusual and required for setup."
    log "Dependencies check passed."
}

# --- Main Script ---
set -euo pipefail

echo "------------------------------------------"
echo "  $TARGET_INSTALL_NAME Installation Script  "
echo "------------------------------------------"

# --- 1. Check Prerequisites ---
check_prerequisites

# --- 2. Detect OS and Architecture ---
OS_KERNEL=$(uname -s)
OS_ARCH=$(uname -m)
OS_SPECIFIC_NAME=""
ASSET_SUFFIX="" # For .exe on Windows

log "Detected OS Kernel: $OS_KERNEL"
log "Detected Architecture: $OS_ARCH"

case "$OS_KERNEL" in
    Linux)
        OS_SPECIFIC_NAME="linux"
        if [ "$OS_ARCH" == "arm64" ]; then OS_ARCH="aarch64"; fi
        ;;
    Darwin) # macOS
        OS_SPECIFIC_NAME="macos"
        ;;
    CYGWIN*|MINGW*|MSYS*|Windows_NT)
        OS_SPECIFIC_NAME="windows"
        ASSET_SUFFIX=".exe"
        if [ "$OS_ARCH" == "x86_64" ] || [ "$OS_ARCH" == "AMD64" ]; then
             OS_ARCH="x86_64"
        elif [ "$OS_ARCH" == "ARM64" ]; then
             OS_ARCH="arm64"
        else
            log "Warning: Detected Windows architecture '$OS_ARCH' may not have a pre-built binary. Falling back to x86_64."
            OS_ARCH="x86_64"
        fi
        log "Detected Windows-like environment. Will look for .exe"
        ;;
    *)
        err "Unsupported operating system: $OS_KERNEL. Please download the binary manually."
        ;;
esac

EXPECTED_ASSET_BASENAME="${TARGET_INSTALL_NAME}-${OS_SPECIFIC_NAME}-${OS_ARCH}"
EXPECTED_ASSET_NAME="${EXPECTED_ASSET_BASENAME}${ASSET_SUFFIX}"
log "Expecting release asset named: $EXPECTED_ASSET_NAME"


# --- 3. Prompt for Installation Location ---
INSTALL_DIR="$USER_INSTALL_DIR"
SYSTEM_INSTALL=false
if [ -t 0 ]; then # Interactive
    echo ""
    read -p "Install '$TARGET_INSTALL_NAME' system-wide ($SYSTEM_INSTALL_DIR)? [y/N]: " choice
    lower_choice=$(echo "${choice:-}" | tr '[:upper:]' '[:lower:]')
    if [ "$lower_choice" == "yes" ] || [ "$lower_choice" == "y" ]; then
        INSTALL_DIR="$SYSTEM_INSTALL_DIR"
        SYSTEM_INSTALL=true
        log "Installing system-wide to '$INSTALL_DIR'."
    else
        log "Installing for user in '$INSTALL_DIR'."
    fi
else # Non-interactive
    log "Running non-interactively, defaulting to user installation in '$USER_INSTALL_DIR'."
fi


# --- 4. Find Latest Release Asset ---
log "Finding latest release for '$EXPECTED_ASSET_NAME'..."
api_url="https://api.github.com/repos/$REPO/releases/latest"
release_info=$(curl -sS --fail "$api_url")
if [ $? -ne 0 ] || [ -z "$release_info" ] || echo "$release_info" | jq -e '.message' > /dev/null 2>&1; then
    err "Failed to fetch release info from GitHub API for $REPO. Check repo name, internet, or API rate limits."
fi
tag_name=$(echo "$release_info" | jq -r '.tag_name')
log "Latest release tag: $tag_name"
asset=$(echo "$release_info" | jq -c ".assets[] | select(.name == \"${EXPECTED_ASSET_NAME}\")" | head -n 1)
if [ -z "$asset" ]; then
    log "Could not find specific asset '$EXPECTED_ASSET_NAME'."
    log "Available assets in release $tag_name:"
    echo "$release_info" | jq -r '.assets[].name' >&2
    err "No suitable binary found for your system ($OS_SPECIFIC_NAME/$OS_ARCH). Please check the releases page on GitHub."
fi
ASSET_ACTUAL_NAME=$(echo "$asset" | jq -r '.name')
ASSET_URL=$(echo "$asset" | jq -r '.browser_download_url')
if [ -z "$ASSET_URL" ] || [ "$ASSET_URL" == "null" ]; then
     err "Found asset '$ASSET_ACTUAL_NAME' but could not get download URL."
fi
log "Found matching asset: $ASSET_ACTUAL_NAME"


# --- 5. Download Binary ---
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"
trap "log 'Cleaning up temporary directory $TEMP_DIR'; rm -rf '$TEMP_DIR'" EXIT
DOWNLOADED_FILE_PATH="$TEMP_DIR/$ASSET_ACTUAL_NAME"
log "Downloading $ASSET_ACTUAL_NAME..."
curl -L -S -o "$DOWNLOADED_FILE_PATH" "$ASSET_URL" || err "Failed to download asset: $ASSET_URL"


# --- 6. Install Binary ---
log "Installing binary to $INSTALL_DIR..."
if $SYSTEM_INSTALL; then
    sudo mkdir -p "$INSTALL_DIR" || err "Failed to create system directory '$INSTALL_DIR'. Check permissions or run with sudo."
else
    mkdir -p "$USER_INSTALL_DIR" || err "Failed to create user directory '$USER_INSTALL_DIR'."
fi
chmod +x "$DOWNLOADED_FILE_PATH" || err "Failed to make binary executable."
FINAL_INSTALL_PATH="$INSTALL_DIR/$TARGET_INSTALL_NAME"
if $SYSTEM_INSTALL; then
    log "Moving '$DOWNLOADED_FILE_PATH' to '$FINAL_INSTALL_PATH' with sudo..."
    sudo mv -f "$DOWNLOADED_FILE_PATH" "$FINAL_INSTALL_PATH" || err "Failed to move binary to system directory."
    sudo chown root:root "$FINAL_INSTALL_PATH" 2>/dev/null || true
else
    log "Moving '$DOWNLOADED_FILE_PATH' to '$FINAL_INSTALL_PATH'..."
    mv -f "$DOWNLOADED_FILE_PATH" "$FINAL_INSTALL_PATH" || err "Failed to move binary to user directory."
fi


# --- 7. Perform Robust Initialization ---

run_robust_initialization() {
    local llamate_exe="$1"
    
    echo ""
    echo "------------------------------------------"
    echo "   Starting First-Time Setup"
    echo "------------------------------------------"
    log "This script will now work around a 'Text file busy' error in 'llamate init'."

    # Define paths
    local config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
    local swap_binary_path="$config_home/llamate/bin/llama-swap"
    local swap_binary_name="llama-swap"
    local old_swap_path="${swap_binary_path}.old"

    # Step 1: Stop any running llama-swap process to prevent it from being restarted
    log "Step 1: Checking for and stopping any running '$swap_binary_name' process..."
    local pids
    pids=$(ps -e -o pid,comm | grep "$swap_binary_name" | grep -v grep | awk '{print $1}') || true
    if [ -n "$pids" ]; then
        log "Found running process(es) with PIDs: $pids. Terminating..."
        kill $pids >/dev/null 2>&1
        sleep 1 # Give a moment for the process to die
    else
        log "No running '$swap_binary_name' process found. Good."
    fi

    # Step 2: If the problematic file exists, rename it.
    if [ -f "$swap_binary_path" ]; then
        log "Step 2: Renaming existing '$swap_binary_path' to '$old_swap_path'."
        mv -f "$swap_binary_path" "$old_swap_path"
    else
        log "Step 2: No existing '$swap_binary_path' found to rename."
    fi

    # Step 3: Run the actual init command using the full path to the executable
    log "Step 3: Running '$llamate_exe init'. This may take a while to download files..."
    if "$llamate_exe" init; then
        # Step 4: Cleanup the old file on success
        if [ -f "$old_swap_path" ]; then
            log "Step 4: Cleaning up by removing '$old_swap_path'."
            rm -f "$old_swap_path"
        fi
        return 0 # Success
    else
        log "Error: '$llamate_exe init' command failed."
        log "The old binary was left at '$old_swap_path' for inspection."
        return 1 # Failure
    fi
}

# --- 8. Final Messages ---
echo ""
echo "✅ Successfully installed '$TARGET_INSTALL_NAME' to '$FINAL_INSTALL_PATH'."

if ! $SYSTEM_INSTALL; then
    # Run the robust initialization function directly
    if ! run_robust_initialization "$FINAL_INSTALL_PATH"; then
        echo ""
        echo "❗️ Installation of '$TARGET_INSTALL_NAME' complete, but the automatic setup failed."
        echo "   Please check the error messages above."
        exit 1
    fi
else
    echo ""
    echo "❗️ Note: System-wide install complete. Run '$TARGET_INSTALL_NAME init' as a regular user to perform first-time setup."
    echo "   If the init command fails, kill the 'llama-swap' process and run it again."
fi

# Final PATH hint if needed
if ! command -v "$TARGET_INSTALL_NAME" &>/dev/null; then
    if ! $SYSTEM_INSTALL && [[ ":$PATH:" != *":$USER_INSTALL_DIR:"* ]]; then
        echo ""
        echo "❗️ Note: Your shell may not find the '$TARGET_INSTALL_NAME' command yet."
        echo "   To fix this, add the following line to your shell profile file (e.g., ~/.bashrc or ~/.zshrc):"
        echo ""
        echo "   export PATH=\"\$PATH:$USER_INSTALL_DIR\""
        echo ""
        echo "   Then, restart your terminal or run 'source <your_profile_file>'."
    fi
fi

echo ""
echo "------------------------------------------"
echo "✅ Installation and setup complete!"
echo "------------------------------------------"
exit 0
