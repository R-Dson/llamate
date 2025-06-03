#!/bin/bash

# --- Configuration ---
REPO="R-Dson/llamate"
TARGET_BINARY_NAME="llamate"
USER_INSTALL_DIR="$HOME/.local/bin" # Standard user-specific bin directory
SYSTEM_INSTALL_DIR="/usr/local/bin"  # Standard system-wide location

# --- Helper Functions ---

# Prints a message to stderr (less intrusive for progress)
log() {
    echo "$@" >&2
}

# Prints an error message to stderr and exits
err() {
    log "Error: $@"
    exit 1
}

# Checks for required commands (silent unless missing)
check_prerequisites() {
    command -v curl >/dev/null || err "curl is not installed. Please install it."
    command -v jq >/dev/null || err "jq is not installed. Please install it."
    # Removed tar check as it's not needed for direct binary download
    log "Dependencies check passed."
}

# --- Main Script ---

# Set strict mode:
# -e: Exit immediately if a command exits with a non-zero status.
# -u: Treat unset variables as an error.
# -o pipefail: The return value of a pipeline is the status of the last command
#             to exit with a non-zero status, or zero if all commands exit
#             successfully.
set -euo pipefail

echo "------------------------------------------"
echo "  $TARGET_BINARY_NAME Installation Script  "
echo "------------------------------------------"

# --- 1. Check Prerequisites ---
check_prerequisites

# --- 2. Prompt for Installation Location ---
INSTALL_DIR="$USER_INSTALL_DIR" # Default to user
SYSTEM_INSTALL=false

# Check if running interactively (stdin is a terminal)
if [ -t 0 ]; then
    echo "" # Newline for clarity
    echo "Install '$TARGET_BINARY_NAME' system-wide ($SYSTEM_INSTALL_DIR)? (Requires sudo)"
    echo -n "Enter yes or no (default is no): "

    # Variables for the prompt, not in a function so no 'local'
    choice=""
    read choice
    lower_choice=$(echo "${choice:-}" | tr '[:upper:]' '[:lower:]')

    if [ "$lower_choice" == "yes" ] || [ "$lower_choice" == "y" ]; then
        INSTALL_DIR="$SYSTEM_INSTALL_DIR"
        SYSTEM_INSTALL=true
        log "Installing system-wide to '$INSTALL_DIR'."
    else
        INSTALL_DIR="$USER_INSTALL_DIR"
        SYSTEM_INSTALL=false
        log "Installing for user in '$INSTALL_DIR'."
    fi
else
    # Not running interactively, default to user install
    log "Running non-interactively, defaulting to user installation in '$USER_INSTALL_DIR'."
    INSTALL_DIR="$USER_INSTALL_DIR"
    SYSTEM_INSTALL=false
    # Set lower_choice to a default value to avoid unbound variable error with set -u
    lower_choice=""
fi


# --- 3. Find Latest Release Asset (direct binary) ---
log "Finding latest release asset named '$TARGET_BINARY_NAME'..."
api_url="https://api.github.com/repos/$REPO/releases/latest"
release_info=$(curl -sS "$api_url") # Use -sS for silent but show errors

# Check for API errors or empty response
if [ $? -ne 0 ] || [ -z "$release_info" ] || echo "$release_info" | jq -e '.message' > /dev/null; then
    err "Failed to fetch release info from GitHub. Check repo name, internet, or try again later."
fi

tag_name=$(echo "$release_info" | jq -r '.tag_name')
if [ -z "$tag_name" ] || [ "$tag_name" == "null" ]; then
    err "Could not determine latest release tag name from GitHub API."
fi
log "Latest release tag: $tag_name"

# Find the asset whose name is exactly TARGET_BINARY_NAME (case-insensitive)
asset=$(echo "$release_info" | jq -c ".assets[] | select(.name | ascii_downcase == \"${TARGET_BINARY_NAME}\")" | head -n 1)

if [ -z "$asset" ]; then
    log "Available assets:"
    echo "$release_info" | jq -r '.assets[].name' >&2 # List available assets on stderr
    err "Could not find a release asset named '$TARGET_BINARY_NAME'."
fi

ASSET_NAME=$(echo "$asset" | jq -r '.name')
ASSET_URL=$(echo "$asset" | jq -r '.browser_download_url')

if [ -z "$ASSET_URL" ] || [ "$ASSET_URL" == "null" ]; then
     err "Found asset '$ASSET_NAME' but could not get download URL."
fi
log "Found matching asset: $ASSET_NAME"


# --- 4. Download Binary ---
# Create a temporary directory
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"

# Register a trap to clean up on exit
trap "log 'Cleaning up temporary directory $TEMP_DIR'; rm -rf $TEMP_DIR" EXIT

# Download the asset directly (it's the binary itself)
DOWNLOADED_FILE="$TEMP_DIR/$ASSET_NAME"
log "Downloading $ASSET_NAME binary..."
curl -L -S -o "$DOWNLOADED_FILE" "$ASSET_URL" || err "Failed to download asset."


# --- 5. Install Binary ---
log "Installing binary to $INSTALL_DIR..."

# Ensure the installation directory exists
if "$SYSTEM_INSTALL"; then
    sudo mkdir -p "$INSTALL_DIR" || err "Failed to create system directory '$INSTALL_DIR'. Check permissions or run with sudo."
else
    # Ensure $HOME/.local exists first for ~/.local/bin
    mkdir -p "$HOME/.local" || err "Failed to create $HOME/.local directory."
    mkdir -p "$INSTALL_DIR" || err "Failed to create user directory '$INSTALL_DIR'."
fi

# The downloaded file IS the binary. Make it executable.
log "Making downloaded binary '$DOWNLOADED_FILE' executable..."
chmod +x "$DOWNLOADED_FILE" || err "Failed to make binary executable."

# Determine the final destination path
INSTALL_PATH="$INSTALL_DIR/$TARGET_BINARY_NAME"

# Move the binary to the installation directory
if "$SYSTEM_INSTALL"; then
    sudo mv -f "$DOWNLOADED_FILE" "$INSTALL_PATH" || err "Failed to move binary to system directory '$INSTALL_DIR'. Check permissions."
    # Optional: Fix ownership
    sudo chown root:root "$INSTALL_PATH" 2>/dev/null || true
else
    mv -f "$DOWNLOADED_FILE" "$INSTALL_PATH" || err "Failed to move binary to user directory '$INSTALL_DIR'."
fi


# --- 6. Final Messages ---
echo "" # Newline
echo "Successfully installed '$TARGET_BINARY_NAME' to '$INSTALL_PATH'."

# Provide PATH hint for user install if needed
if ! "$SYSTEM_INSTALL"; then
    if [[ ":$PATH:" != *":$USER_INSTALL_DIR:"* ]]; then
        echo "" # Newline
        echo "Note: '$USER_INSTALL_DIR' is not in your \$PATH."
        echo "To run '$TARGET_BINARY_NAME' from any terminal, add this to your shell profile (e.g., ~/.bashrc, ~/.zshrc):"
        echo ""
        echo "  export PATH=\"\$PATH:$USER_INSTALL_DIR\""
        echo ""
        echo "Then restart your terminal or run 'source ~/.your_profile'."
    # Else: It is in PATH, no message needed.
    fi
else
    # For system install, verify the path (usually /usr/local/bin is in system PATH)
     if ! command -v "$TARGET_BINARY_NAME" &>/dev/null; then
          log "Warning: '$TARGET_BINARY_NAME' may not be immediately found in your \$PATH. You might need to open a new terminal."
     # Else: It is in PATH, no message needed.
     fi
fi

echo "" # Newline
echo "Installation complete."
echo "------------------------------------------"

exit 0