#!/bin/bash

# Function to clean up processes
cleanup() {
    echo "🛑 Stopping services..."
    # Kill all child processes of this script
    pkill -P $$
    # Kill frontend and backend by port, just in case
    lsof -ti:8001 | xargs kill -9
    lsof -ti:5173 | xargs kill -9
    echo "✅ All services stopped."
    exit 0
}

# Trap SIGINT and SIGTERM to run cleanup
trap cleanup SIGINT SIGTERM

# Activate conda environment
# NOTE: You might need to source your shell's rc file if conda command is not found
# e.g., source ~/.bashrc or source ~/.zshrc
# This script assumes 'conda' is in the PATH

echo "🧹 Cleaning up previous runs..."
lsof -ti:8001 | xargs kill -9 >/dev/null 2>&1
lsof -ti:5173 | xargs kill -9 >/dev/null 2>&1

echo "🐍 Activating Conda environment 'scholar'..."
eval "$(conda shell.bash hook)"
conda activate scholar

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate conda environment 'scholar'. Please ensure it exists and conda is initialized."
    exit 1
fi

# Start the backend server in the background
echo "🚀 Starting backend server..."
cd backend
/Users/wangguanghui/miniconda3/envs/scholar/bin/python run.py &
BACKEND_PID=$!
cd ..

# Wait a moment for the backend to initialize
sleep 5

# Health check for the backend
echo "🩺 Performing health check on backend..."
if curl -s http://127.0.0.1:8001/api/health | grep -q '"status":"healthy"'; then
    echo "✅ Backend is healthy."
else
    echo "❌ Backend failed to start or is not healthy. Check backend logs."
    kill $BACKEND_PID
    exit 1
fi

# Start the frontend server
echo "🎨 Starting frontend server..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Frontend dependencies not found, installing..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n\n============================================================"
echo "✅ Application started successfully!"
echo "Backend is running on http://127.0.0.1:8001"
echo "Frontend is running on http://127.0.0.1:5173"
echo "============================================================"
echo "Press Ctrl+C to stop all services."

# Wait for all background jobs to complete.
# This will keep the script alive until Ctrl+C is pressed.
wait