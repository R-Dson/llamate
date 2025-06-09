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
        # Normalize arch for Linux if needed (e.g., arm64 to aarch64)
        if [ "$OS_ARCH" == "arm64" ]; then OS_ARCH="aarch64"; fi
        ;;
    Darwin) # macOS
        OS_SPECIFIC_NAME="macos"
        # uname -m on Apple Silicon is arm64, which matches our GitHub Actions build
        ;;
    CYGWIN*|MINGW*|MSYS*|Windows_NT) # Git Bash, Cygwin, MSYS2, or actual Windows from WSL uname -o
        OS_SPECIFIC_NAME="windows"
        ASSET_SUFFIX=".exe"
        # Normalize Windows arch (PROCESSOR_ARCHITECTURE is better but not always available in pure bash)
        if [ "$OS_ARCH" == "x86_64" ] || [ "$OS_ARCH" == "AMD64" ]; then
             OS_ARCH="x86_64" # Standardize to x86_64
        elif [ "$OS_ARCH" == "ARM64" ]; then
             OS_ARCH="arm64" # Standardize to arm64
        else
            log "Warning: Detected Windows architecture '$OS_ARCH' may not have a pre-built binary."
            log "Attempting to find a generic x86_64 Windows binary."
            OS_ARCH="x86_64" # Fallback, adjust if you build other Windows arches
        fi
        log "Detected Windows-like environment. Will look for .exe"
        ;;
    *)
        err "Unsupported operating system: $OS_KERNEL. Please download the binary manually."
        ;;
esac

# Construct the expected asset name based on GitHub Actions output
# Example: llamate-linux-x86_64, llamate-macos-arm64, llamate-windows-x86_64.exe
EXPECTED_ASSET_BASENAME="${TARGET_INSTALL_NAME}-${OS_SPECIFIC_NAME}-${OS_ARCH}"
EXPECTED_ASSET_NAME="${EXPECTED_ASSET_BASENAME}${ASSET_SUFFIX}"

log "Expecting release asset named: $EXPECTED_ASSET_NAME"


# --- 3. Prompt for Installation Location ---
INSTALL_DIR="$USER_INSTALL_DIR"
SYSTEM_INSTALL=false

if [ -t 0 ]; then # Interactive
    echo ""
    echo -n "Install '$TARGET_INSTALL_NAME' system-wide ($SYSTEM_INSTALL_DIR)? [y/N]: "
    choice=""
    read choice
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
    # lower_choice is not strictly needed here if not used, but set for completeness
    lower_choice="no" 
fi


# --- 4. Find Latest Release Asset ---
log "Finding latest release for '$EXPECTED_ASSET_NAME'..."
api_url="https://api.github.com/repos/$REPO/releases/latest"
release_info=$(curl -sS --fail "$api_url") # --fail makes curl exit non-zero on HTTP errors

if [ $? -ne 0 ] || [ -z "$release_info" ] || echo "$release_info" | jq -e '.message' > /dev/null 2>&1; then
    err "Failed to fetch release info from GitHub API for $REPO. Check repo name, internet, or API rate limits."
fi

tag_name=$(echo "$release_info" | jq -r '.tag_name')
if [ -z "$tag_name" ] || [ "$tag_name" == "null" ]; then
    err "Could not determine latest release tag name from GitHub API."
fi
log "Latest release tag: $tag_name"

# Find the asset matching our constructed name (case-sensitive as GitHub asset names are)
asset=$(echo "$release_info" | jq -c ".assets[] | select(.name == \"${EXPECTED_ASSET_NAME}\")" | head -n 1)

if [ -z "$asset" ]; then
    log "Could not find specific asset '$EXPECTED_ASSET_NAME'."
    log "Available assets in release $tag_name:"
    echo "$release_info" | jq -r '.assets[].name' >&2
    err "No suitable binary found for your system ($OS_SPECIFIC_NAME/$OS_ARCH). Please check the releases page on GitHub."
fi

ASSET_ACTUAL_NAME=$(echo "$asset" | jq -r '.name') # The name of the asset we found
ASSET_URL=$(echo "$asset" | jq -r '.browser_download_url')

if [ -z "$ASSET_URL" ] || [ "$ASSET_URL" == "null" ]; then
     err "Found asset '$ASSET_ACTUAL_NAME' but could not get download URL."
fi
log "Found matching asset: $ASSET_ACTUAL_NAME"


# --- 5. Download Binary ---
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"
trap "log 'Cleaning up temporary directory $TEMP_DIR'; rm -rf '$TEMP_DIR'" EXIT

# Download the asset directly
DOWNLOADED_FILE_PATH="$TEMP_DIR/$ASSET_ACTUAL_NAME" # Use the actual asset name for temp file
log "Downloading $ASSET_ACTUAL_NAME..."
curl -L -S -o "$DOWNLOADED_FILE_PATH" "$ASSET_URL" || err "Failed to download asset: $ASSET_URL"


# --- 6. Install Binary ---
log "Installing binary to $INSTALL_DIR..."

# Ensure the installation directory exists
if $SYSTEM_INSTALL; then
    sudo mkdir -p "$INSTALL_DIR" || err "Failed to create system directory '$INSTALL_DIR'. Check permissions or run with sudo."
else
    mkdir -p "$HOME/.local" 2>/dev/null || true # Ensure $HOME/.local exists
    mkdir -p "$INSTALL_DIR" || err "Failed to create user directory '$INSTALL_DIR'."
fi

# Make the downloaded binary executable
log "Making '$DOWNLOADED_FILE_PATH' executable..."
chmod +x "$DOWNLOADED_FILE_PATH" || err "Failed to make binary executable."

# Final destination path (using the generic TARGET_INSTALL_NAME)
# If it's a Windows .exe, we might want to keep the .exe or install it as 'llamate'
# For simplicity and cross-platform command consistency, let's aim for 'llamate'
# but handle if the downloaded file itself needs to be 'llamate.exe' for Windows environments.
FINAL_INSTALL_PATH="$INSTALL_DIR/$TARGET_INSTALL_NAME"
if [ "$OS_SPECIFIC_NAME" == "windows" ] && [[ "$INSTALL_DIR" != "/usr/local/bin" ]] && [[ "$INSTALL_DIR" != "$HOME/.local/bin" ]]; then
    # If installing to a typical Windows path (not handled here, but for future thought)
    # one might want to keep the .exe. For WSL/Git Bash common paths, 'llamate' is fine.
    # For now, we always install as TARGET_INSTALL_NAME
    log "Note: For Windows, the installed command will be '$TARGET_INSTALL_NAME' (not necessarily with .exe)."
fi


# Move the binary to the installation directory
if $SYSTEM_INSTALL; then
    log "Moving '$DOWNLOADED_FILE_PATH' to '$FINAL_INSTALL_PATH' with sudo..."
    sudo mv -f "$DOWNLOADED_FILE_PATH" "$FINAL_INSTALL_PATH" || err "Failed to move binary to system directory. Check permissions."
    sudo chown root:root "$FINAL_INSTALL_PATH" 2>/dev/null || true # Optional ownership fix
else
    log "Moving '$DOWNLOADED_FILE_PATH' to '$FINAL_INSTALL_PATH'..."
    mv -f "$DOWNLOADED_FILE_PATH" "$FINAL_INSTALL_PATH" || err "Failed to move binary to user directory."
fi


# --- 7. Final Messages ---
echo ""
echo "Successfully installed '$TARGET_INSTALL_NAME' to '$FINAL_INSTALL_PATH'."
if [ "$OS_SPECIFIC_NAME" == "windows" ] && [[ "$ASSET_ACTUAL_NAME" == *".exe" ]]; then
    echo "The downloaded executable was '$ASSET_ACTUAL_NAME'."
fi

# Provide PATH hint
path_command_check="$TARGET_INSTALL_NAME"
# On Windows (in Git Bash/WSL), if the target is llamate.exe, we check for that in path if appropriate
# However, we installed it as 'llamate', so 'llamate' should be what's checked.

if ! command -v "$path_command_check" &>/dev/null; then
    if ! $SYSTEM_INSTALL && [[ ":$PATH:" != *":$USER_INSTALL_DIR:"* ]]; then
        echo ""
        echo "Note: '$USER_INSTALL_DIR' might not be in your \$PATH."
        echo "To run '$TARGET_INSTALL_NAME' from any terminal, add this to your shell profile (e.g., ~/.bashrc, ~/.zshrc, ~/.profile):"
        echo "  export PATH=\"\$PATH:$USER_INSTALL_DIR\""
        echo "Then restart your terminal or run 'source ~/.your_profile_file'."
    elif $SYSTEM_INSTALL; then
        log "Warning: '$TARGET_INSTALL_NAME' may not be immediately found in your \$PATH. You might need to open a new terminal or re-login."
    else
        log "Warning: '$TARGET_INSTALL_NAME' not found in PATH, but '$USER_INSTALL_DIR' seems to be. A new terminal session might be needed."
    fi
fi

echo ""
echo "Installation complete."
echo "You can try running: $TARGET_INSTALL_NAME --version"
echo "------------------------------------------"

# --- 8. Optional Initialization ---
if ! $SYSTEM_INSTALL; then
    if [ -t 0 ]; then  # Interactive
        echo ""
        echo -n "Run '$TARGET_INSTALL_NAME init' for first-time setup? [Y/n]: "
        read choice
        choice_lower=$(echo "${choice:-y}" | tr '[:upper:]' '[:lower:]')
        if [ "$choice_lower" = "y" ] || [ "$choice_lower" = "yes" ]; then
            echo "Running initialization..."
            $FINAL_INSTALL_PATH init || echo "Initialization failed - run manually later"
        fi
    else  # Non-interactive
        echo "Running automatic initialization..."
        $FINAL_INSTALL_PATH init || echo "Initialization failed - run manually later"
    fi
else  # System-wide install
    echo ""
    echo "Note: Run '$TARGET_INSTALL_NAME init' per user for first-time setup"
fi

exit 0