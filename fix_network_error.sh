#!/bin/bash

echo "=========================================="
echo "Network Error Fix Script"
echo "=========================================="
echo ""

# Step 1: Kill all processes on ports 8000 and 3000
echo "Step 1: Cleaning up ports 8000 and 3000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 2
echo "✅ Ports cleaned"
echo ""

# Step 2: Check if backend can start
echo "Step 2: Testing backend connection..."
cd server
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start backend in background
echo "Starting backend server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Test backend
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend failed to start. Check /tmp/backend.log"
    cat /tmp/backend.log | tail -10
    exit 1
fi

echo ""
echo "Step 3: Backend is ready!"
echo ""
echo "Next steps:"
echo "1. In a NEW terminal, start the frontend:"
echo "   cd client && npm start"
echo ""
echo "2. Open http://localhost:3000 in your browser"
echo ""
echo "3. Check browser console (F12) for any errors"
echo ""
echo "Backend logs: tail -f /tmp/backend.log"
echo "Backend PID: $BACKEND_PID (to kill: kill $BACKEND_PID)"

