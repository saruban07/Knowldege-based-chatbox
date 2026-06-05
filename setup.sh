#!/usr/bin/env bash
# Discord KB Support Bot — macOS/Linux setup script
# Usage: chmod +x setup.sh && ./setup.sh

set -euo pipefail

echo ""
echo "Discord KB Support Bot — Setup"
echo "==============================="
echo ""

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python not found. Install Python 3.10+"
    exit 1
fi

echo "[OK] $($PYTHON --version)"

# Create venv if missing
if [ ! -f "venv/bin/python" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment exists"
fi

# Install dependencies
echo "Installing dependencies..."
venv/bin/pip install -r requirements.txt
echo "[OK] Dependencies installed"

# Create .env from example if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[ACTION] Created .env from .env.example"
    echo "         Edit .env and add your DISCORD_TOKEN and GROQ_API_KEY"
else
    echo "[OK] .env already exists"
fi

# Create required directories
mkdir -p kb tickets chroma_db

echo ""
echo "Running setup checks..."
venv/bin/python check_setup.py
check_exit=$?

echo ""
if [ "$check_exit" -eq 0 ]; then
    echo "Setup complete! Start the bot with:"
    echo "  source venv/bin/activate"
    echo "  python bot.py"
else
    echo "Setup checks failed. Fix .env and run again:"
    echo "  nano .env"
    echo "  ./setup.sh"
fi

exit "$check_exit"
