#!/bin/bash

# Exit on first failure
set -e

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Determine or create virtual environment
if [ -d ".venv" ]; then
  VENV_DIR=".venv"
elif [ -d "venv" ]; then
  VENV_DIR="venv"
else
  VENV_DIR=".venv"
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Installing backend dependencies..."
pip install --disable-pip-version-check -r requirements.txt >/dev/null

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with the following variables:"
<<<<<<< HEAD
    echo "  OPENAI_API_KEY=your_openai_api_key_here"
    echo "  SECRET_KEY=your-secret-key-change-in-production"
    echo "  DATABASE_URL=sqlite:///./feedback.db"
    echo ""
    echo "The server will start but AI features may not work without OPENAI_API_KEY."
=======
    echo "  HUGGINGFACE_API_KEY=your_huggingface_api_key_here  # Optional"
    echo "  SECRET_KEY=your-secret-key-change-in-production"
    echo "  DATABASE_URL=sqlite:///./feedback.db"
    echo ""
    echo "The server will start and AI features will use the public Hugging Face API (may have rate limits)."
>>>>>>> frontend-ui
    echo ""
fi

# Start the server
echo "🚀 Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

