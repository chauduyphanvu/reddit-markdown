#!/bin/bash

# Obsidian Reddit Import Plugin Integration Script
# Handles installation, updates, and management across multiple vaults

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_ID="reddit-import"
PLUGIN_NAME="Reddit Import"
GITHUB_REPO="chauduyphanvu/reddit-markdown"
PLUGIN_PATH="obsidian-reddit-import"

# Print colored output
print_status() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}🚀 Obsidian Reddit Import Plugin Manager${NC}\n"
}

# Show help
show_help() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
  install [VAULT_PATH]     Install plugin to vault (auto-detects if no path)
  update [VAULT_PATH]      Update plugin in vault
  build                    Build plugin from source
  list                     List all Obsidian vaults with plugin status
  uninstall [VAULT_PATH]   Remove plugin from vault
  dev [VAULT_PATH]         Install in development mode with file watching
  help                     Show this help message

Options:
  --force                  Force reinstall even if already installed
  --no-build              Skip building (use existing files)
  --verbose               Show detailed output

Examples:
  $0 install                              # Auto-detect and install
  $0 install ~/Documents/MyVault          # Install to specific vault
  $0 update                               # Update all vaults
  $0 dev ~/Documents/TestVault            # Development mode
  $0 list                                 # Show vault status

EOF
}

# Find Obsidian vaults
find_vaults() {
    local vaults=()
    
    # Common Obsidian vault locations
    local search_paths=(
        "$HOME/Documents"
        "$HOME/Desktop" 
        "$HOME/Dropbox"
        "$HOME/OneDrive"
        "$HOME/iCloud*"
        "$HOME/Library/Mobile Documents/iCloud~md~obsidian"
    )
    
    print_status "Searching for Obsidian vaults..."
    
    for path in "${search_paths[@]}"; do
        if [[ -d "$path" ]]; then
            while IFS= read -r -d '' vault; do
                if [[ -d "$vault/.obsidian" ]]; then
                    vaults+=("$vault")
                fi
            done < <(find "$path" -name ".obsidian" -type d -print0 2>/dev/null | head -10)
        fi
    done
    
    printf '%s\n' "${vaults[@]}"
}

# Get plugin status in vault
get_plugin_status() {
    local vault_path="$1"
    local plugin_dir="$vault_path/.obsidian/plugins/$PLUGIN_ID"
    
    if [[ -d "$plugin_dir" ]]; then
        if [[ -f "$plugin_dir/manifest.json" ]]; then
            local version=$(jq -r '.version' "$plugin_dir/manifest.json" 2>/dev/null || echo "unknown")
            echo "installed:$version"
        else
            echo "broken"
        fi
    else
        echo "not_installed"
    fi
}

# Build plugin
build_plugin() {
    local skip_build="$1"
    
    if [[ "$skip_build" == "true" ]]; then
        print_warning "Skipping build (using existing files)"
        return 0
    fi
    
    print_status "Building plugin..."
    
    if [[ ! -f "package.json" ]]; then
        print_error "package.json not found. Are you in the plugin directory?"
        exit 1
    fi
    
    # Install dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing dependencies..."
        npm install --silent
    fi
    
    # Build
    npm run build --silent
    
    if [[ ! -f "main.js" ]]; then
        print_error "Build failed - main.js not found"
        exit 1
    fi
    
    print_success "Plugin built successfully"
}

# Install plugin to vault
install_plugin() {
    local vault_path="$1"
    local force="$2"
    local is_dev_mode="$3"
    
    if [[ ! -d "$vault_path" ]]; then
        print_error "Vault path does not exist: $vault_path"
        exit 1
    fi
    
    if [[ ! -d "$vault_path/.obsidian" ]]; then
        print_error "Not an Obsidian vault: $vault_path"
        exit 1
    fi
    
    local plugin_dir="$vault_path/.obsidian/plugins/$PLUGIN_ID"
    local status=$(get_plugin_status "$vault_path")
    
    if [[ "$status" =~ ^installed: && "$force" != "true" ]]; then
        local version=${status#installed:}
        print_warning "Plugin already installed (version: $version)"
        print_status "Use --force to reinstall or run 'update' command"
        return 0
    fi
    
    # Create plugin directory
    mkdir -p "$plugin_dir"
    
    # Copy files
    print_status "Installing plugin files to: $plugin_dir"
    
    local files=("manifest.json" "main.js" "styles.css")
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            cp "$file" "$plugin_dir/"
            print_status "  ✓ $file"
        else
            print_error "Missing file: $file"
            exit 1
        fi
    done
    
    # Development mode - create symlinks for auto-reload
    if [[ "$is_dev_mode" == "true" ]]; then
        print_status "Setting up development mode..."
        local abs_source_dir="$(pwd)"
        
        for file in "${files[@]}"; do
            rm -f "$plugin_dir/$file"
            ln -s "$abs_source_dir/$file" "$plugin_dir/$file"
        done
        
        print_success "Development mode enabled (files symlinked)"
        print_warning "Remember to run 'npm run dev' for auto-building"
    fi
    
    print_success "Plugin installed to: $(basename "$vault_path")"
    print_status "Next steps:"
    print_status "  1. Reload Obsidian (Cmd/Ctrl + R)"
    print_status "  2. Enable '$PLUGIN_NAME' in Settings → Community Plugins"
    
    if [[ "$is_dev_mode" != "true" ]]; then
        print_status "  3. Optional: Configure Reddit API credentials in plugin settings"
    fi
}

# List vaults with plugin status
list_vaults() {
    local vaults
    readarray -t vaults < <(find_vaults)
    
    if [[ ${#vaults[@]} -eq 0 ]]; then
        print_warning "No Obsidian vaults found"
        return 0
    fi
    
    print_success "Found ${#vaults[@]} Obsidian vault(s):\n"
    
    printf "%-50s %-20s\n" "Vault Path" "Plugin Status"
    printf "%-50s %-20s\n" "$(printf '%.50s' "$(printf '%.0s-' {1..50})")" "$(printf '%.20s' "$(printf '%.0s-' {1..20})")"
    
    for vault in "${vaults[@]}"; do
        local status=$(get_plugin_status "$vault")
        local vault_name=$(basename "$vault")
        
        case "$status" in
            "not_installed")
                printf "%-50s ${RED}%-20s${NC}\n" "$vault_name" "Not installed"
                ;;
            "broken")
                printf "%-50s ${YELLOW}%-20s${NC}\n" "$vault_name" "Broken"
                ;;
            installed:*)
                local version=${status#installed:}
                printf "%-50s ${GREEN}%-20s${NC}\n" "$vault_name" "v$version"
                ;;
        esac
    done
    
    echo ""
}

# Uninstall plugin
uninstall_plugin() {
    local vault_path="$1"
    
    if [[ ! -d "$vault_path" ]]; then
        print_error "Vault path does not exist: $vault_path"
        exit 1
    fi
    
    local plugin_dir="$vault_path/.obsidian/plugins/$PLUGIN_ID"
    
    if [[ ! -d "$plugin_dir" ]]; then
        print_warning "Plugin not installed in: $(basename "$vault_path")"
        return 0
    fi
    
    print_status "Removing plugin from: $(basename "$vault_path")"
    rm -rf "$plugin_dir"
    print_success "Plugin removed"
}

# Update plugin in vault
update_plugin() {
    local vault_path="$1"
    local status=$(get_plugin_status "$vault_path")
    
    if [[ "$status" == "not_installed" ]]; then
        print_warning "Plugin not installed in: $(basename "$vault_path")"
        print_status "Run 'install' command first"
        return 0
    fi
    
    print_status "Updating plugin in: $(basename "$vault_path")"
    install_plugin "$vault_path" "true" "false"
}

# Auto-detect vault if none provided
auto_detect_vault() {
    local vaults
    readarray -t vaults < <(find_vaults)
    
    case ${#vaults[@]} in
        0)
            print_error "No Obsidian vaults found"
            print_status "Please specify vault path manually"
            exit 1
            ;;
        1)
            echo "${vaults[0]}"
            ;;
        *)
            print_status "Multiple vaults found:"
            for i in "${!vaults[@]}"; do
                echo "  $((i+1)). $(basename "${vaults[$i]}")"
            done
            
            echo -n "Select vault (1-${#vaults[@]}): "
            read -r choice
            
            if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 1 && "$choice" -le ${#vaults[@]} ]]; then
                echo "${vaults[$((choice-1))]}"
            else
                print_error "Invalid selection"
                exit 1
            fi
            ;;
    esac
}

# Start development server
start_dev_server() {
    local vault_path="$1"
    
    print_status "Starting development mode..."
    print_status "Vault: $(basename "$vault_path")"
    print_status "Plugin will auto-rebuild on file changes"
    print_warning "Keep this terminal open"
    
    # Install in dev mode first
    install_plugin "$vault_path" "true" "true"
    
    # Start file watcher
    print_status "Starting file watcher..."
    npm run dev
}

# Main script logic
main() {
    local command="$1"
    local vault_path="$2"
    local force="false"
    local skip_build="false"
    local verbose="false"
    
    # Parse flags
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force="true"
                shift
                ;;
            --no-build)
                skip_build="true"
                shift
                ;;
            --verbose)
                verbose="true"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                if [[ -z "$vault_path" ]]; then
                    vault_path="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Show header
    print_header
    
    case "$command" in
        "install")
            if [[ -z "$vault_path" ]]; then
                vault_path=$(auto_detect_vault)
            fi
            build_plugin "$skip_build"
            install_plugin "$vault_path" "$force" "false"
            ;;
        "update")
            if [[ -z "$vault_path" ]]; then
                # Update all vaults
                local vaults
                readarray -t vaults < <(find_vaults)
                build_plugin "$skip_build"
                for vault in "${vaults[@]}"; do
                    local status=$(get_plugin_status "$vault")
                    if [[ "$status" =~ ^installed: ]]; then
                        update_plugin "$vault"
                    fi
                done
            else
                build_plugin "$skip_build"
                update_plugin "$vault_path"
            fi
            ;;
        "build")
            build_plugin "$skip_build"
            ;;
        "list")
            list_vaults
            ;;
        "uninstall")
            if [[ -z "$vault_path" ]]; then
                vault_path=$(auto_detect_vault)
            fi
            uninstall_plugin "$vault_path"
            ;;
        "dev")
            if [[ -z "$vault_path" ]]; then
                vault_path=$(auto_detect_vault)
            fi
            start_dev_server "$vault_path"
            ;;
        "help"|"--help"|"")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Check dependencies
check_deps() {
    local deps=("node" "npm" "jq")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing[*]}"
        print_status "Please install:"
        for dep in "${missing[@]}"; do
            case "$dep" in
                "node"|"npm")
                    print_status "  - Node.js: https://nodejs.org/"
                    ;;
                "jq")
                    print_status "  - jq: brew install jq (or apt-get install jq)"
                    ;;
            esac
        done
        exit 1
    fi
}

# Run dependency check and main function
check_deps
main "$@"