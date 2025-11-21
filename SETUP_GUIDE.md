# Quick Setup Guide - Make It Work NOW

## Critical Tools Installation

### 1. Install Docker Desktop (5 minutes)

**Mac Installation:**
```bash
# Option 1: Using Homebrew (recommended)
brew install --cash docker

# Option 2: Download directly
# Go to: https://www.docker.com/products/docker-desktop
# Download and install Docker Desktop for Mac
```

**After Installation:**
1. Open Docker Desktop app
2. Wait for it to start (whale icon in menu bar)
3. Verify: `docker --version`

### 2. Install Ollama (2 minutes)

```bash
# One command installation
curl -fsSL https://ollama.com/install.sh | sh

# Or via Homebrew
brew install ollama

# Verify installation
ollama --version

# Pull a model (we'll use llama3.2 - 2GB, fast)
ollama pull llama3.2

# Test it
ollama run llama3.2 "Hello"
```

## Fallback: No Docker? No Problem!

I'm also building a subprocess-based executor that works WITHOUT Docker:
- Uses Python's subprocess module
- Still isolated (separate processes)
- Works on any system
- Not as secure as Docker but functional for demos

## Timeline

- **Docker Install**: 5 min
- **Ollama Install**: 2 min  
- **Pull Model**: 2 min
- **Test Both**: 1 min
- **Total**: 10 minutes

Then we code.

## Commands to Run

```bash
# 1. Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Docker Desktop
brew install --cask docker

# 3. Open Docker Desktop (GUI app)
open /Applications/Docker.app

# 4. Install Ollama
brew install ollama

# 5. Start Ollama service
ollama serve &

# 6. Pull model
ollama pull llama3.2

# 7. Test
ollama run llama3.2 "What is 2+2?"
```

**Do these installations now. I'll build the subprocess fallback in parallel so system works either way.**
