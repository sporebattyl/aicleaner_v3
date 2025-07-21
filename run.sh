#!/bin/bash
# AICleaner v3 - Simple Startup Script

echo "Starting AICleaner v3 Core Service..."

# Check if Python dependencies are installed
if ! python3 -c "import fastapi, uvicorn, aiohttp, yaml" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the core service
echo "Core service starting on http://localhost:8000"
python3 -m core.service

