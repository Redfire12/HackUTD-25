#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with the following variables:"
    echo "  OPENAI_API_KEY=your_openai_api_key_here"
    echo "  SECRET_KEY=your-secret-key-change-in-production"
    echo "  DATABASE_URL=sqlite:///./feedback.db"
    echo ""
    echo "The server will start but AI features may not work without OPENAI_API_KEY."
    echo ""
fi

# Start the server
echo "🚀 Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

