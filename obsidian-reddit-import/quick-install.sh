#!/bin/bash

# Quick one-liner installer for Obsidian Reddit Import Plugin
# Usage: curl -sSL https://raw.githubusercontent.com/user/repo/main/quick-install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✅${NC} $1"; }
print_error() { echo -e "${RED}❌${NC} $1"; }

echo -e "\n${BLUE}🚀 Quick Install: Obsidian Reddit Import Plugin${NC}\n"

# Check dependencies
for cmd in node npm jq; do
    if ! command -v $cmd &> /dev/null; then
        print_error "Missing dependency: $cmd"
        exit 1
    fi
done

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

print_status "Downloading plugin..."

# Download latest release or clone repo
if command -v gh &> /dev/null; then
    gh repo clone chauduyphanvu/reddit-markdown
    cd reddit-markdown/obsidian-reddit-import
else
    git clone https://github.com/chauduyphanvu/reddit-markdown.git
    cd reddit-markdown/obsidian-reddit-import
fi

# Build
print_status "Building plugin..."
npm install --silent
npm run build --silent

# Auto-detect vaults
print_status "Searching for Obsidian vaults..."
VAULTS=($(find "$HOME" -name ".obsidian" -type d 2>/dev/null | head -5 | xargs -I {} dirname {}))

if [ ${#VAULTS[@]} -eq 0 ]; then
    print_error "No Obsidian vaults found"
    exit 1
elif [ ${#VAULTS[@]} -eq 1 ]; then
    VAULT="${VAULTS[0]}"
else
    print_status "Found multiple vaults:"
    for i in "${!VAULTS[@]}"; do
        echo "  $((i+1)). $(basename "${VAULTS[$i]}")"
    done
    echo -n "Select vault (1-${#VAULTS[@]}): "
    read choice
    VAULT="${VAULTS[$((choice-1))]}"
fi

# Install
PLUGIN_DIR="$VAULT/.obsidian/plugins/reddit-import"
mkdir -p "$PLUGIN_DIR"

cp manifest.json main.js styles.css "$PLUGIN_DIR/"

print_success "Plugin installed to: $(basename "$VAULT")"
print_status "Next steps:"
print_status "  1. Reload Obsidian (Cmd/Ctrl + R)"
print_status "  2. Enable 'Reddit Import' in Settings → Community Plugins"

# Cleanup
cd /
rm -rf "$TEMP_DIR"