# Obsidian Reddit Import Plugin Makefile
# Convenient commands for development and distribution

.PHONY: help install build dev clean test lint format release

# Default target
help:
	@echo "Obsidian Reddit Import Plugin"
	@echo ""
	@echo "Available commands:"
	@echo "  make install         Install plugin to auto-detected vault"
	@echo "  make build          Build plugin for production"
	@echo "  make dev            Start development mode with file watching"
	@echo "  make clean          Clean build artifacts"
	@echo "  make lint           Run TypeScript linter"
	@echo "  make format         Format code with Prettier"
	@echo "  make test           Run tests"
	@echo "  make release        Create release bundle"
	@echo "  make install-deps   Install dependencies"
	@echo ""
	@echo "Variables:"
	@echo "  VAULT=/path/to/vault  Specify vault path"
	@echo "  VERSION=1.0.0         Specify version for release"
	@echo ""
	@echo "Examples:"
	@echo "  make install VAULT=~/Documents/MyVault"
	@echo "  make release VERSION=1.2.3"

# Install dependencies
install-deps:
	@echo "📦 Installing dependencies..."
	@npm install

# Build plugin
build: install-deps
	@echo "🔨 Building plugin..."
	@npm run build
	@echo "✅ Build complete"

# Install plugin to vault
install: build
ifdef VAULT
	@echo "📁 Installing to vault: $(VAULT)"
	@./install-plugin.sh install "$(VAULT)" --no-build
else
	@echo "📁 Auto-detecting vault..."
	@./install-plugin.sh install --no-build
endif

# Development mode
dev: install-deps
ifdef VAULT
	@echo "🛠️ Starting development mode for: $(VAULT)"
	@./install-plugin.sh dev "$(VAULT)" --no-build
else
	@echo "🛠️ Starting development mode (auto-detect vault)"
	@./install-plugin.sh dev --no-build
endif

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -f main.js main.js.map
	@rm -rf node_modules/.cache
	@echo "✅ Clean complete"

# Run linter
lint: install-deps
	@echo "🔍 Running TypeScript linter..."
	@npx tsc --noEmit
	@echo "✅ Lint complete"

# Format code
format: install-deps
	@echo "✨ Formatting code..."
	@npx prettier --write "**/*.{ts,js,json,md}"
	@echo "✅ Format complete"

# Run tests (placeholder - add when tests are implemented)
test:
	@echo "🧪 Running tests..."
	@echo "⚠️  Tests not implemented yet"

# Create release bundle
release: clean build
ifdef VERSION
	@echo "📦 Creating release bundle v$(VERSION)..."
	@sed -i.bak 's/"version": ".*"/"version": "$(VERSION)"/' manifest.json
	@rm -f manifest.json.bak
else
	@echo "📦 Creating release bundle..."
endif
	@mkdir -p dist
	@zip -j dist/reddit-import-$(shell jq -r .version manifest.json).zip manifest.json main.js styles.css README.md
	@echo "✅ Release bundle created: dist/reddit-import-$(shell jq -r .version manifest.json).zip"

# List all vaults
list-vaults:
	@echo "📋 Listing Obsidian vaults..."
	@./install-plugin.sh list

# Update plugin in all vaults
update-all: build
	@echo "🔄 Updating plugin in all vaults..."
	@./install-plugin.sh update --no-build

# Uninstall from vault
uninstall:
ifdef VAULT
	@echo "🗑️ Uninstalling from vault: $(VAULT)"
	@./install-plugin.sh uninstall "$(VAULT)"
else
	@echo "🗑️ Uninstalling from auto-detected vault..."
	@./install-plugin.sh uninstall
endif

# Quick development setup
setup: install-deps build
	@echo "🚀 Development setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  make install         # Install to vault"
	@echo "  make dev            # Start development mode"
	@echo "  make list-vaults    # See available vaults"

# Check plugin status
status:
	@echo "📊 Plugin Status:"
	@echo "Version: $(shell jq -r .version manifest.json)"
	@echo "Build exists: $(shell [ -f main.js ] && echo "✅" || echo "❌")"
	@echo "Dependencies: $(shell [ -d node_modules ] && echo "✅" || echo "❌")"
	@./install-plugin.sh list

# Development server with live reload
serve: dev

# All-in-one: setup and install
quick-start: setup install
	@echo ""
	@echo "🎉 Quick start complete!"
	@echo "Plugin is installed and ready to use."
	@echo ""
	@echo "In Obsidian:"
	@echo "  1. Reload (Cmd/Ctrl + R)"
	@echo "  2. Enable plugin in Settings → Community Plugins"
	@echo "  3. Use Cmd/Ctrl + P → 'Import Reddit post'"